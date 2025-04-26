import asyncio
from typing import List, Dict, Any, Tuple
from datetime import datetime
from src.schemas import AssetWithMetadata
from src.utils.common_utils import fetch_financial_data
from src.utils.db_utils import (
    save_asset_metadata, history_table, add_symbol_with_metadata, get_symbols
)
import logging

log = logging.getLogger(__name__)

def trim_asset_history(symbol: str, keep_last: int = 10, history_table=history_table) -> None:
    """
    Trim the history table for a symbol to keep only the most recent `keep_last` entries.
    """
    entries = [e for e in history_table.all() if e.get('symbol') == symbol]
    log.info(f"Found entries symbol: {symbol}, count {len(entries)}")

    if len(entries) > keep_last:
        entries_sorted = sorted(entries, key=lambda x: x.get('timestamp', ''))  # Sort ascending, oldest first
        to_remove = entries_sorted[:len(entries) - keep_last]  # Remove oldest entries
        doc_ids = [e.get('doc_id') for e in to_remove if e.get('doc_id') is not None]
        log.info(f"Removing old entries symbol: {symbol}, count: {len(doc_ids)}, doc_ids: {doc_ids}")

        if doc_ids:
            history_table.remove(doc_ids=doc_ids)
            remaining = [e for e in history_table.all() if e.get('symbol') == symbol]
            log.info(f"History trimmed symbol: {symbol}, remaining_count: {len(remaining)}")

def trim_all_histories(symbols: list[str], keep_last: int = 10) -> None:
    """
    Trim history for all given symbols to keep only the most recent `keep_last` entries.
    """
    for symbol in symbols:
        trim_asset_history(symbol, keep_last=keep_last)

def build_asset_with_metadata(data: dict) -> AssetWithMetadata:
    """
    Build an AssetWithMetadata object from a data dict.
    """
    return AssetWithMetadata(
        symbol=data['symbol'],
        latest_price=data['latest_price'],
        change_percent_24h=data['change_percent_24h'],
        average_price_7d=data['average_price_7d'],
        last_updated=datetime.now().isoformat()
    )

async def fetch_and_save_asset(symbol: str) -> AssetWithMetadata | None:
    """
    Fetch latest data for a symbol, save to DB, trim history, and return AssetWithMetadata or None if fetch fails.
    """
    data = await fetch_financial_data(symbol)
    if data and 'symbol' in data:
        save_asset_metadata(data['symbol'], {
            'latest_price': data['latest_price'],
            'change_percent_24h': data['change_percent_24h'],
            'average_price_7d': data['average_price_7d']
        })
        trim_asset_history(data['symbol'])
        return build_asset_with_metadata(data)
    return None

async def update_assets_and_trim_history(symbols: List[str]) -> None:
    """
    Fetch latest data for each symbol, update DB, and trim history to last 10 entries.
    """
    tasks = [fetch_and_save_asset(s) for s in symbols]
    await asyncio.gather(*tasks)

async def add_assets_service(symbols: List[str]) -> List[AssetWithMetadata]:
    """
    Add new assets, fetch their metadata, update DB/history, and return AssetWithMetadata list.
    """
    tasks = [fetch_and_save_asset(symbol) for symbol in symbols]
    results = await asyncio.gather(*tasks)
    assets_with_metadata = []
    for symbol, asset in zip(symbols, results):
        if asset:
            assets_with_metadata.append(asset)
        else:
            assets_with_metadata.append(AssetWithMetadata(symbol=symbol))
    return assets_with_metadata

async def ingest_assets_service(update_symbols: List[str]) -> Dict[str, Any]:
    """
    Ingest/update market data for given symbols, update DB/history, and return status dict.
    """
    all_symbols = get_symbols()
    results = []
    success_messages = []
    error_messages = []
    for symbol in update_symbols:
        try:
            asset = await fetch_and_save_asset(symbol)
            if asset:
                if symbol not in all_symbols:
                    success, message = await add_symbol_with_metadata(symbol, {
                        'latest_price': asset.latest_price,
                        'change_percent_24h': asset.change_percent_24h,
                        'average_price_7d': asset.average_price_7d
                    })
                    if success:
                        success_messages.append(message)
                    else:
                        error_messages.append(message)
                else:
                    success_messages.append(f"Updated {symbol}")
                results.append(asset)
            else:
                error_messages.append(f"Could not fetch data for {symbol}")
        except Exception as e:
            error_messages.append(f"Error processing {symbol}: {str(e)}")
    return {
        "message": f"Processed {len(update_symbols)} symbols",
        "updated_count": len(results),
        "success_messages": success_messages,
        "error_messages": error_messages,
        "updated_assets": [r.symbol for r in results]
    }
