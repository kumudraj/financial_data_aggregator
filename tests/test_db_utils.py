import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
import asyncio
from src.utils import db_utils
from src.services.asset_service import trim_asset_history

def test_validate_symbol_format():
    assert db_utils.validate_symbol_format("BTC-USD")
    assert db_utils.validate_symbol_format("TSLA")
    assert not db_utils.validate_symbol_format("btc-usd")
    assert not db_utils.validate_symbol_format("1234")

@pytest.mark.asyncio
async def test_save_symbols_and_is_valid_symbol(mock_yfinance):
    """Test symbol validation and saving"""
    # Should only save valid symbols
    valid = await db_utils.save_symbols(["BTC-USD", "INVALID", "TSLA"])
    assert "BTC-USD" in valid
    assert "TSLA" in valid
    # Should not save invalid symbol
    assert "INVALID" not in valid
    
    # Test symbol validation
    assert await db_utils.is_valid_symbol("BTC-USD")
    assert not await db_utils.is_valid_symbol("INVALID")
    assert not await db_utils.is_valid_symbol("btc-usd")  # lowercase not valid
    assert not await db_utils.is_valid_symbol("")
    assert not await db_utils.is_valid_symbol(None)

# For history trimming, we mock the table
class DummyEntry:
    def __init__(self, symbol, timestamp, doc_id):
        self.symbol = symbol
        self.timestamp = timestamp
        self.doc_id = doc_id

class DummyHistoryTable:
    def __init__(self):
        self.entries = []

    def all(self):
        return self.entries

    def remove(self, doc_ids):
        doc_id_set = set(doc_ids)
        self.entries = [e for e in self.entries if e['doc_id'] not in doc_id_set]

    def insert(self, entry):
        entry = entry.copy()
        entry['doc_id'] = len(self.entries)
        self.entries.append(entry)

    def truncate(self):
        self.entries = []

@pytest.fixture
def mock_history_table(monkeypatch):
    table = DummyHistoryTable()
    monkeypatch.setattr(db_utils, "history_table", table)
    return table

def test_trim_asset_history(mock_history_table):
    """Test that trim_asset_history keeps only the most recent entries."""
    symbol = "TSLA"

    # Insert mock entries with ascending timestamps
    entries = []
    for i in range(12):
        entry = {
            "symbol": symbol,
            "timestamp": f"2024-01-01T00:00:{i:02d}",
            "doc_id": i
        }
        entries.append(entry)

    # Set entries directly
    mock_history_table.entries = entries.copy()

    # Trim and verify
    trim_asset_history(symbol, keep_last=10, history_table=mock_history_table)
    assert len(mock_history_table.entries) == 10, f"Expected 10 entries but got {len(mock_history_table.entries)}"

    # Verify we kept the most recent timestamps
    timestamps = sorted(e['timestamp'] for e in mock_history_table.entries)
    assert len(timestamps) == 10, "Should have exactly 10 timestamps"
    assert timestamps[0] >= "2024-01-01T00:00:02", "Should have removed oldest timestamps"

@pytest.fixture
def mock_symbols_table(monkeypatch):
    class MockSymbolsTable:
        def __init__(self):
            self.data = {"symbols": []}
            
        def upsert(self, document, cond=None):
            if "symbols" in document:
                self.data["symbols"] = sorted(document.get("symbols", []))
            
        def all(self):
            return [{"symbol": s, "last_updated": None} for s in self.data.get("symbols", [])]
            
        def truncate(self):
            self.data["symbols"] = []

        def search(self, query):
            # Always return the symbols in the expected structure for get_symbols
            if self.data.get("symbols"):
                return [{"symbols": self.data["symbols"]}]
            return []
            
        def insert(self, document):
            if "symbols" in document:
                self.data["symbols"] = sorted(document["symbols"])
            elif "symbol" in document:
                if document["symbol"] not in self.data["symbols"]:
                    self.data["symbols"].append(document["symbol"])
                    self.data["symbols"].sort()
            
    table = MockSymbolsTable()
    monkeypatch.setattr(db_utils, "symbols_table", table)
    return table

# Mock yfinance for symbol validation
@pytest.fixture
def mock_yfinance(monkeypatch):
    import types
    import pandas as pd
    class DummyTicker:
        def __init__(self, symbol):
            self.symbol = symbol
        def history(self, period="1d"):
            valid_symbols = ["BTC-USD", "ETH-USD", "TSLA", "AAPL", "GOOG"]
            # Only uppercase and in valid_symbols are valid
            if self.symbol and self.symbol.upper() == self.symbol and self.symbol in valid_symbols:
                # Return a non-empty DataFrame
                return pd.DataFrame({"price": [1]})
            # Return an empty DataFrame for invalid
            return pd.DataFrame()
    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", DummyTicker)
    return DummyTicker

def test_get_symbols(mock_symbols_table):
    """Test getting symbols from the database"""
    # Empty database should return default symbols
    initial_symbols = db_utils.get_symbols()
    assert len(initial_symbols) == 3  # Default symbols should be present
    assert all(s in initial_symbols for s in ["BTC-USD", "ETH-USD", "TSLA"])
    
    # Replace with new symbols
    new_symbols = ["AAPL", "GOOG"]
    mock_symbols_table.upsert({"symbols": new_symbols})
    symbols = db_utils.get_symbols()
    assert len(symbols) == 2  # Should have only new symbols
    assert all(s in symbols for s in new_symbols)

def test_truncate_db(mock_symbols_table, mock_history_table):
    """Test database truncation"""
    # Add some data
    mock_symbols_table.upsert({"symbols": ["BTC-USD", "TSLA", "AAPL"]})
    mock_history_table.insert({"symbol": "BTC-USD", "price": 100})

    # Verify data was added
    assert len(mock_symbols_table.data["symbols"]) == 3
    assert len(mock_history_table.entries) == 1
    
    # Truncate
    db_utils.truncate_db()
    
    # Verify empty
    assert mock_symbols_table.data["symbols"] == []
    assert len(mock_history_table.entries) == 0
    
    # After truncate, new get_symbols call should return default symbols
    symbols = db_utils.get_symbols()
    assert len(symbols) == 3
    assert all(s in symbols for s in ["BTC-USD", "ETH-USD", "TSLA"])

@pytest.mark.asyncio
async def test_save_asset_metadata():
    """Test saving asset metadata"""
    symbol = "BTC-USD"
    metadata = {
        "latest_price": 50000.0,
        "change_percent_24h": 2.5,
        "average_price_7d": 49000.0
    }
    
    # Test saving valid metadata
    db_utils.save_asset_metadata(symbol, metadata)
    
    # Test saving with missing fields (should not raise error)
    partial_metadata = {"latest_price": 51000.0}
    db_utils.save_asset_metadata(symbol, partial_metadata)

@pytest.mark.asyncio
async def test_is_valid_symbol_error_handling(mock_yfinance):
    """Test error handling in is_valid_symbol"""
    # Test with None
    assert not await db_utils.is_valid_symbol(None)
    
    # Test with empty string
    assert not await db_utils.is_valid_symbol("")
    
    # Test with invalid format (lowercase)
    assert not await db_utils.is_valid_symbol("btc-usd")
    
    # Test with valid format (uppercase)
    assert await db_utils.is_valid_symbol("BTC-USD")
