import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from src.services.asset_service import build_asset_with_metadata

def test_build_asset_with_metadata():
    data = {
        'symbol': 'AAPL',
        'latest_price': 100.0,
        'change_percent_24h': 1.5,
        'average_price_7d': 98.0
    }
    asset = build_asset_with_metadata(data)
    assert asset.symbol == 'AAPL'
    assert asset.latest_price == 100.0
    assert asset.change_percent_24h == 1.5
    assert asset.average_price_7d == 98.0
    assert asset.last_updated is not None
