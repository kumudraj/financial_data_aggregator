import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

import pytest
from unittest.mock import patch, MagicMock
from src.utils.chain_utils import FinancialChain

@pytest.fixture
def mock_openai():
    with patch('src.utils.chain_utils.ChatOpenAI') as mock:
        mock_instance = MagicMock()
        async def async_ainvoke(*args, **kwargs):
            return "Test summary"
        mock_instance.ainvoke.side_effect = async_ainvoke
        mock.return_value = mock_instance
        yield mock_instance

@pytest.fixture
def mock_fetch_data():
    with patch('src.utils.chain_utils.fetch_financial_data') as mock:
        mock.return_value = {"symbol": "TEST", "latest_price": 100.0}
        yield mock

@pytest.mark.asyncio
async def test_financial_chain_initialization(mock_openai):
    """Test FinancialChain initialization with different parameters"""
    # Test default initialization
    chain = FinancialChain()
    assert isinstance(chain.symbols, list)
    
    # Test custom initialization with symbols
    custom_chain = FinancialChain(
        symbols=["CUSTOM-1", "CUSTOM-2"],
        temperature=0.5
    )
    assert custom_chain.symbols == ["CUSTOM-1", "CUSTOM-2"]
    assert isinstance(custom_chain.llm, MagicMock)

@pytest.mark.asyncio
async def test_generate_summary_with_valid_data(mock_openai):
    """Test summary generation with valid data"""
    chain = FinancialChain(symbols=["TEST"])
    
    test_data = [{
        "symbol": "TEST",
        "latest_price": 100.0,
        "change_percent_24h": 5.0
    }]
    
    result = await chain.generate_summary(test_data)
    assert result == "Test summary"
    assert mock_openai.ainvoke.called

@pytest.mark.asyncio
async def test_generate_summary_with_empty_data(mock_openai):
    """Test summary generation with empty data"""
    chain = FinancialChain(symbols=["TEST"])
    result = await chain.generate_summary([])
    assert result == "No valid financial data to summarize."

@pytest.mark.asyncio
async def test_generate_summary_with_error(mock_openai):
    """Test summary generation with error"""
    chain = FinancialChain(symbols=["TEST"])
    mock_openai.ainvoke.side_effect = Exception("Test error")
    
    result = await chain.generate_summary([{"symbol": "TEST"}])
    assert result == "Summary generation failed due to an error."

@pytest.mark.asyncio
async def test_run_with_valid_data(mock_openai, mock_fetch_data):
    """Test run method with valid data"""
    chain = FinancialChain(symbols=["TEST"])
    
    result = await chain.run()
    assert isinstance(result, str)
    assert result == "Test summary"
    assert mock_fetch_data.called
    assert mock_openai.ainvoke.called

@pytest.mark.asyncio
async def test_run_with_no_valid_data(mock_openai, mock_fetch_data):
    """Test run method when no valid data is fetched"""
    chain = FinancialChain(symbols=["TEST"])
    mock_fetch_data.return_value = {}
    
    result = await chain.run()
    assert result is None

@pytest.mark.asyncio
async def test_run_with_fetch_error(mock_openai, mock_fetch_data):
    """Test run method with fetch error"""
    chain = FinancialChain(symbols=["TEST"])
    mock_fetch_data.side_effect = Exception("Fetch error")
    
    result = await chain.run()
    assert result is None