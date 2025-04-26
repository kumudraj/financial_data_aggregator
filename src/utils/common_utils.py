import numpy as np
import yfinance as yf

from src.utils.logger import structlog

log = structlog.get_logger()

default_symbols = ["BTC-USD", "ETH-USD", "TSLA"]
default_instructions = "Generate a concise summary for the following financial data."


def convert_numpy_types(obj):
    """Convert numpy types to native Python types for serialization."""
    if isinstance(obj, dict):
        return {k: convert_numpy_types(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_numpy_types(i) for i in obj]
    elif isinstance(obj, np.generic):
        return obj.item()
    return obj


async def fetch_financial_data(symbol: str, period: str = "7d"):
    """Fetch financial data for a given symbol."""
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period=period)
        if data.empty:
            log.warning(f"No data found symbol: {symbol}")
            return {}
        latest_price = data['Close'].iloc[-1]
        change_percent_24h = ((latest_price - data['Close'].iloc[-2]) / data['Close'].iloc[-2]) * 100
        average_price_7d = data['Close'].mean()

        log.info(f"Fetched data: symbol: {symbol}, latest_price: {latest_price}, "
                 f"change_percent_24h: {change_percent_24h}, average_price_7d: {average_price_7d}")

        return {
            "symbol": symbol,
            "latest_price": latest_price,
            "change_percent_24h": change_percent_24h,
            "average_price_7d": average_price_7d
        }
    except Exception as e:
        log.error(f"Error fetching financial data {symbol} {str(e)}", exc_info=True)
        return {}
