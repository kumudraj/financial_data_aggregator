import os
from datetime import datetime
from tinydb import TinyDB, Query
from typing import List, Dict, Any, Tuple
from src.utils.logger import structlog
import yfinance as yf
import asyncio
from tinydb.storages import JSONStorage
import json

log = structlog.get_logger()

class PrettyJSONStorage(JSONStorage):
    def write(self, data):
        self._handle.seek(0)
        json.dump(data, self._handle, indent=4)
        self._handle.truncate()

# Initialize TinyDB with absolute path
DB_PATH = os.path.join(os.path.dirname(__file__), 'symbols_db.json')
log.info(f"Initializing database db_path:{DB_PATH}")

db = TinyDB(DB_PATH, storage=PrettyJSONStorage)
symbols_table = db.table('symbols')
history_table = db.table('history')

def validate_symbol_format(symbol: str) -> bool:
    """
    Check if the symbol string is in a valid format for a stock or crypto asset.
    Returns True if valid, False otherwise.
    """
    return isinstance(symbol, str) and (
        symbol.endswith("-USD") or  # For crypto
        symbol.isupper()  # For stocks
    )

async def is_valid_symbol(symbol: str) -> bool:
    """
    Check if the symbol exists and returns data from yfinance.
    Returns True if the symbol is valid and data is available, False otherwise.
    """
    try:
        ticker = yf.Ticker(symbol)
        data = ticker.history(period="1d")
        return not data.empty
    except Exception:
        return False

async def save_symbols(symbols: List[str]) -> List[str]:
    """
    Save new symbols to the database after validating their format and existence using yfinance.
    Returns the updated list of all tracked symbols.
    """
    try:
        # Validate format first
        format_valid = [s for s in symbols if validate_symbol_format(s)]
        if not format_valid:
            log.error("No valid symbols provided format check")
            return []
        # Validate existence using yfinance
        checks = await asyncio.gather(*(is_valid_symbol(s) for s in format_valid))
        valid_symbols = [s for s, ok in zip(format_valid, checks) if ok]
        if not valid_symbols:
            log.error(f"No valid symbols provided error: yfinance check")
            return []
        # Get existing and merge
        existing_symbols = get_symbols()
        updated_symbols = list(set(existing_symbols + valid_symbols))
        # Update symbols table
        symbols_table.truncate()
        symbols_table.insert({'symbols': updated_symbols})
        log.info(f"Symbols updated successfully new_symbols:{valid_symbols}, total_symbols: {len(updated_symbols)}")
        return updated_symbols
    except Exception as e:
        log.error(f"Error saving symbols error: {str(e)}", exc_info=True)
        return get_symbols()

def truncate_db() -> None:
    """
    Clear all records from the symbols and history tables in the database.
    Returns None.
    """
    try:
        symbols_table.truncate()
        history_table.truncate()
        log.info("Database truncated successfully")
    except Exception as e:
        log.error(f"Error truncating database error:{str(e)}", exc_info=True)

def get_symbols() -> List[str]:
    """
    Retrieve all tracked symbols from the database.
    If the database is empty, initializes with default symbols.
    Returns a list of symbol strings.
    """
    try:
        Symbol = Query()
        result = symbols_table.search(Symbol.symbols.exists())
        if not result:
            default_symbols = ["BTC-USD", "ETH-USD", "TSLA"]
            symbols_table.insert({'symbols': default_symbols})
            return default_symbols
        return result[0]['symbols']
    except Exception as e:
        log.error(f"Error fetching symbols error: {str(e)}", exc_info=True)
        return ["BTC-USD", "ETH-USD", "TSLA"]  # Return defaults on error

def save_asset_metadata(symbol: str, metadata: Dict[str, Any]) -> None:
    """
    Save asset metadata to the database, including historical and current data.
    Updates the 'history' and 'current' tables for the given symbol.
    Returns None.
    """
    try:
        timestamp = datetime.now().isoformat()
        history_entry = {
            'symbol': symbol,
            'timestamp': timestamp,
            'metadata': {
                'latest_price': metadata['latest_price'],
                'change_percent_24h': metadata['change_percent_24h'],
                'average_price_7d': metadata['average_price_7d']
            }
        }
        
        # Add new entry to history
        history_table.insert(history_entry)
        
        # Update current metadata
        Asset = Query()
        current_metadata = metadata.copy()
        current_metadata['last_updated'] = timestamp
        current_metadata['symbol'] = symbol
        
        # Update or insert current state
        current_table = db.table('current')
        if current_table.search(Asset.symbol == symbol):
            current_table.update(current_metadata, Asset.symbol == symbol)
        else:
            current_table.insert(current_metadata)
        log.info(f"Metadata updated symbol: {symbol}, has_history: True")
    except Exception as e:
        log.error(f"Error saving metadata symbol:{symbol}, error: {str(e)}", exc_info=True)

def get_assets_with_metadata() -> List[Dict[str, Any]]:
    """
    Retrieve all assets with their current metadata from the database.
    Returns a list of dictionaries, each containing asset metadata.
    """
    try:
        current_table = db.table('current')
        results = current_table.all()
        return results if results else []
    except Exception as e:
        log.error(f"Error fetching asset metadata error: {str(e)}", exc_info=True)
        return []

def get_asset_history(symbol: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Retrieve historical metadata for a specific asset symbol.
    Returns a list of dictionaries, each representing a historical entry, limited by 'limit'.
    """
    try:
        Asset = Query()
        results = history_table.search(Asset.symbol == symbol)
        # Sort by timestamp in descending order and limit results
        sorted_results = sorted(results, key=lambda x: x['timestamp'], reverse=True)
        return sorted_results[:limit]
    except Exception as e:
        log.error("Error fetching asset history", symbol=symbol, error=str(e), exc_info=True)
        return []

async def add_symbol_with_metadata(symbol: str, metadata: Dict[str, Any]) -> Tuple[bool, str]:
    """
    Add a new symbol and its metadata to the database after validating with yfinance.
    Returns a tuple (success: bool, message: str).
    """
    try:
        if not validate_symbol_format(symbol):
            return False, f"Invalid symbol format: {symbol}"
        if not await is_valid_symbol(symbol):
            return False, f"Symbol does not exist or is not valid: {symbol}"
        # Add to symbols list if not exists
        existing_symbols = get_symbols()
        if symbol not in existing_symbols:
            updated_symbols = existing_symbols + [symbol]
            symbols_table.truncate()
            symbols_table.insert({'symbols': updated_symbols})
        # Save metadata with history
        save_asset_metadata(symbol, metadata)
        log.info("Symbol added", symbol=symbol, has_metadata=True)
        return True, f"Successfully added {symbol} with metadata"
    except Exception as e:
        error = f"Error adding symbol {symbol}: {str(e)}"
        log.error(error, exc_info=True)
        return False, error