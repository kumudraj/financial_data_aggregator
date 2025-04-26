import pytest
from httpx import AsyncClient, ASGITransport
from src.main import app

@pytest.mark.asyncio
async def test_get_assets():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/assets")
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert isinstance(data["assets"], list)

def test_get_assets_internal_error(monkeypatch):
    from src.main import app
    from httpx import AsyncClient, ASGITransport
    # Simulate get_assets_with_metadata raising an exception
    monkeypatch.setattr("src.main.get_assets_with_metadata", lambda: (_ for _ in ()).throw(Exception("DB error")))
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/assets")
            assert response.status_code == 500
            assert "detail" in response.json()
    import asyncio; asyncio.run(run())

@pytest.mark.asyncio
async def test_post_assets_valid_and_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test valid symbols
        response = await client.post("/assets", json={"symbols": ["BTC-USD"]})
        assert response.status_code == 200
        data = response.json()
        assert "assets" in data
        assert len(data["assets"]) > 0
        
        # Test invalid symbols
        response = await client.post("/assets", json={"symbols": ["INVALID"]})
        assert response.status_code == 400

def test_add_assets_internal_error(monkeypatch):
    from src.main import app
    from httpx import AsyncClient, ASGITransport
    # Simulate save_symbols raising an exception
    monkeypatch.setattr("src.main.save_symbols", lambda symbols: (_ for _ in ()).throw(Exception("DB error")))
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/assets", json={"symbols": ["BTC-USD"]})
            assert response.status_code == 500
            assert "detail" in response.json()
    import asyncio; asyncio.run(run())

@pytest.mark.asyncio
async def test_get_metrics_valid_and_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/metrics/BTC-USD")
        assert response.status_code in (200, 404)
        response = await client.get("/metrics/INVALID")
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_get_asset_history_valid_and_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/assets/BTC-USD/history")
        assert response.status_code in (200, 404)
        response = await client.get("/assets/INVALID/history")
        assert response.status_code == 404

def test_get_asset_history_internal_error(monkeypatch):
    from src.main import app
    from httpx import AsyncClient, ASGITransport
    # Simulate get_asset_history raising an exception
    monkeypatch.setattr("src.main.get_asset_history", lambda symbol, limit=10: (_ for _ in ()).throw(Exception("DB error")))
    async def run():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/assets/BTC-USD/history")
            assert response.status_code == 500
            assert "detail" in response.json()
    import asyncio; asyncio.run(run())

@pytest.mark.asyncio
async def test_compare_assets_valid_and_invalid():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/compare", params={"asset1": "BTC-USD", "asset2": "TSLA"})
        assert response.status_code in (200, 404)
        response = await client.get("/compare", params={"asset1": "BTC-USD", "asset2": "INVALID"})
        assert response.status_code == 404

@pytest.mark.asyncio
async def test_summary_all_and_single():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test summary for all assets
        response = await client.get("/summary")
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data
        
        # Test summary for single asset
        response = await client.get("/summary", params={"symbol": "BTC-USD"})
        assert response.status_code == 200
        data = response.json()
        assert "summary" in data

@pytest.mark.asyncio
async def test_ingest_all_and_some():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/ingest")
        assert response.status_code in (200, 400)
        response = await client.post("/ingest", json={"assets": ["BTC-USD"]})
        assert response.status_code in (200, 400)