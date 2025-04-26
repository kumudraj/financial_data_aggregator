import asyncio
from datetime import datetime

from fastapi import FastAPI, HTTPException

from src.schemas import (
    AssetMetrics, AssetComparison, Summary, Assets,
    ErrorResponse, AddAssetsRequest, AssetWithMetadata,
    IngestRequest, AssetHistory
)
from src.services.asset_service import update_assets_and_trim_history, add_assets_service, ingest_assets_service
from src.utils.chain_utils import FinancialChain
from src.utils.common_utils import fetch_financial_data
from src.utils.db_utils import (
    get_symbols, save_symbols, save_asset_metadata,
    get_assets_with_metadata, get_asset_history
)
from src.utils.logger import structlog

app = FastAPI(title="Financial Data Aggregator & GenAI Insight Engine")
log = structlog.get_logger()


@app.get("/assets", response_model=Assets)
async def get_assets():
    """List all tracked assets with their metadata."""
    try:
        assets_with_metadata = get_assets_with_metadata()
        if not assets_with_metadata:
            # If no metadata exists, return just the symbols
            symbols = get_symbols()
            assets_with_metadata = [AssetWithMetadata(symbol=s) for s in symbols]

        log.info(f"Retrieved assets count: {len(assets_with_metadata)}")
        return Assets(assets=assets_with_metadata)
    except Exception as e:
        log.error(f"Error fetching assets error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/assets", response_model=Assets)
async def add_assets(request: AddAssetsRequest):
    """
    Add new assets to track and fetch their metadata.
    This endpoint keeps historical data for each asset.
    Request body must contain a list of symbols to add.
    """
    try:
        if not request.symbols:
            raise HTTPException(
                status_code=400,
                detail="No symbols provided. Please provide at least one symbol."
            )
        updated_symbols = await save_symbols(request.symbols)
        if not updated_symbols:
            raise HTTPException(
                status_code=400,
                detail="No valid symbols provided. Symbols should be in format 'BTC-USD' for crypto or 'TSLA' for stocks."
            )
        assets_with_metadata = await add_assets_service(request.symbols)
        log.info(
            f"Added new assets new_assets: {request.symbols} metadata:{assets_with_metadata}, history:{updated_symbols}")
        return Assets(assets=assets_with_metadata)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error adding assets error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/assets/{symbol}/history", response_model=AssetHistory)
async def get_asset_history_endpoint(symbol: str, limit: int = 10):
    """Get historical metadata for a specific asset."""
    try:
        history = get_asset_history(symbol, limit)
        if not history:
            raise HTTPException(status_code=404, detail=f"No history found for symbol {symbol}")
        return AssetHistory(history=history)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching history symbol: {symbol} error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/metrics/{symbol}", response_model=AssetWithMetadata,
         responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def get_metrics(symbol: str):
    """Get metrics for a specific symbol, update DB, and return last_updated."""
    try:
        data = await fetch_financial_data(symbol)
        if not data:
            raise HTTPException(status_code=404, detail=f"Symbol {symbol} not found")
        # Save/update in DB
        save_asset_metadata(symbol, {
            'latest_price': data['latest_price'],
            'change_percent_24h': data['change_percent_24h'],
            'average_price_7d': data['average_price_7d']
        })
        last_updated = datetime.now().isoformat()
        return AssetWithMetadata(
            symbol=symbol,
            latest_price=data['latest_price'],
            change_percent_24h=data['change_percent_24h'],
            average_price_7d=data['average_price_7d'],
            last_updated=last_updated
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error fetching metrics symbol: {symbol} error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/compare", response_model=AssetComparison,
         responses={404: {"model": ErrorResponse}, 500: {"model": ErrorResponse}})
async def compare_assets(asset1: str, asset2: str):
    """Compare two assets."""
    try:
        log.info(f"Comparing assets asset1: {asset1} asset2: {asset2}")
        # Fetch data for both assets in parallel
        data = await asyncio.gather(
            fetch_financial_data(asset1),
            fetch_financial_data(asset2)
        )

        if not data[0]:
            raise HTTPException(status_code=404, detail=f"Asset {asset1} not found")
        if not data[1]:
            raise HTTPException(status_code=404, detail=f"Asset {asset2} not found")

        asset1_metrics = AssetMetrics(**data[0])
        asset2_metrics = AssetMetrics(**data[1])

        price_difference = asset1_metrics.latest_price - asset2_metrics.latest_price
        performance_difference_24h = asset1_metrics.change_percent_24h - asset2_metrics.change_percent_24h

        return AssetComparison(
            asset1=asset1_metrics,
            asset2=asset2_metrics,
            price_difference=price_difference,
            performance_difference_24h=performance_difference_24h
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error comparing assets error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/summary", response_model=Summary, responses={500: {"model": ErrorResponse}})
async def get_summary(symbol: str = None):
    """
       Get a GenAI-generated summary of current trends. 
       Optionally filter by symbol. Also updates DB and trims history to last 10 entries.
       If no symbol is provided, only the first 10 tracked assets are summarized.
    """
    try:
        if symbol:
            symbols = [symbol]
        else:
            all_symbols = get_symbols()
            symbols = all_symbols[:10]  # Limit to max 10 assets
        # Use service layer for update and history management
        await update_assets_and_trim_history(symbols)
        # Generate summary
        chain = FinancialChain(symbols=symbols)
        summary = await chain.run()
        if not summary:
            summary = "Unable to generate summary at this time."
        return Summary(summary=summary)
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error generating summary error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/ingest")
async def ingest_data(request: IngestRequest = None):
    """
    Trigger manual ingestion/update of market data.
    If specific assets are provided, only those will be updated.
    Otherwise, all tracked assets will be updated.
    New assets will be automatically added if valid data can be fetched.
    """
    try:
        all_symbols = get_symbols()
        update_symbols = request.assets if request and request.assets else all_symbols
        result = await ingest_assets_service(update_symbols)
        if not result["updated_assets"]:
            raise HTTPException(status_code=400, detail="No valid data could be fetched for any symbol")
        return result
    except HTTPException:
        raise
    except Exception as e:
        log.error(f"Error during data ingestion error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
