# Financial Data Aggregator & GenAI Insight Engine

A robust financial data aggregation system that fetches real-time market data and provides AI-generated insights through a RESTful API interface. The system supports both cryptocurrency and stock market data tracking with automated data ingestion and analysis capabilities.

## Features

- Real-time financial data fetching using yfinance
- Support for both cryptocurrency (e.g., BTC-USD) and stock symbols (e.g., TSLA)
- Automated data ingestion and historical tracking
- GenAI-powered market trend summaries
- RESTful API endpoints for data access
- Asynchronous data processing
- Comprehensive error handling and logging

## Prerequisites

- Python 3.12+
- FastAPI
- yfinance
- OpenAI API key (for GenAI summaries)
- Other dependencies listed in requirements.txt

## Installation

1. Clone the repository
2. Create and activate a virtual environment:
```bash
python3.12 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
Create a `.env` file in the root directory and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```


## Running the Application

Start the FastAPI server:
```bash
python run.py
```

The server will start on `http://0.0.0.0:5001` with auto-reload enabled.

## API Endpoints & Functionality

### GET /assets
**Description:**
Returns a list of all tracked assets and their latest metadata (price, 24h change, 7d average, last update time).

**Response:**
- 200 OK: JSON object with a list of assets and their metadata.

---

### POST /assets
**Description:**
Add new assets to track. Accepts a list of symbols (e.g., ["BTC-USD", "TSLA"]). Only valid, real symbols are accepted. Fetches and stores their latest metadata.

**Request Body:**
```json
{
  "symbols": ["BTC-USD", "TSLA"]
}
```
**Response:**
- 200 OK: JSON object with the updated list of tracked assets and their metadata.
- 400 Bad Request: If no valid symbols are provided.

---

### GET /metrics/{symbol}
**Description:**
Returns the latest metrics for a specific asset symbol. Also updates the database with the latest data and returns the last update time.

**Path Parameter:**
- `symbol` (string): The asset symbol (e.g., "BTC-USD", "TSLA").

**Response:**
- 200 OK: JSON object with symbol, latest price, 24h change, 7d average, and last_updated.
- 404 Not Found: If the symbol is not tracked or not valid.

---

### GET /assets/{symbol}/history
**Description:**
Returns the last 10 historical entries for a specific asset symbol (timestamped price, 24h change, 7d average).

**Path Parameter:**
- `symbol` (string): The asset symbol.
- `limit` (query, optional): Number of history entries to return (default 10).

**Response:**
- 200 OK: JSON object with a list of historical entries.
- 404 Not Found: If no history is found for the symbol.

---

### GET /compare
**Description:**
Compares two assets on their latest metrics (price, 24h change, 7d average). Returns the difference in price and 24h performance.

**Query Parameters:**
- `asset1` (string): First asset symbol.
- `asset2` (string): Second asset symbol.

**Response:**
- 200 OK: JSON object with metrics for both assets and their differences.
- 404 Not Found: If either asset is not tracked or not valid.

---

### GET /summary
**Description:**
Returns a GenAI-generated summary of current market trends for up to 10 tracked assets (or a single symbol if provided). Also updates the database with the latest data and trims history to the last 10 entries per asset.

**Query Parameter (optional):**
- `symbol` (string): If provided, summary is for this symbol only. Otherwise, up to 10 tracked assets are summarized.

**Response:**
- 200 OK: JSON object with a summary string.
- 404/500: If no data is available or an error occurs.

---

### POST /ingest
**Description:**
Manually trigger ingestion/update of market data for all or selected assets. Updates DB and history for each asset.

**Request Body (optional):**
```json
{
  "assets": ["BTC-USD", "ETH-USD"]
}
```
If omitted, all tracked assets are ingested.

**Response:**
- 200 OK: JSON object with status, updated assets, and any errors.
- 400: If no valid data could be fetched for any symbol.

---

## Example API Responses

See `sample_summary_response.txt` for detailed example responses.

## API Notes
- All endpoints return structured JSON responses.
- All asset symbols are validated using yfinance before being accepted.
- History is automatically trimmed to the last 10 entries per asset.
- All endpoints implement error handling and logging.

## Project Structure

```
├── README.md
├── requirements.txt
├── run.py
├── src/
│   ├── main.py                # FastAPI application and endpoints
│   ├── schemas.py             # Pydantic models and schemas
│   ├── services/
│   │   └── asset_service.py   # Business logic/service layer for asset operations
│   └── utils/
│       ├── agent.py           # GenAI agent implementation
│       ├── chain_utils.py     # LangChain integration and summary chain
│       ├── common_utils.py    # Shared utility functions (data fetch, conversion)
│       ├── db_utils.py        # Database operations (TinyDB, validation)
│       ├── logger.py          # Logging configuration
│       └── symbols_db.json    # TinyDB JSON database (pretty-printed)
└── tests/
    ├── test_api_endpoints.py  # Integration tests for API endpoints
    ├── test_asset_service.py  # Unit tests for asset service functions
    ├── test_db_utils.py       # Unit tests for database utilities
    └── test_integration_api.py # Integration tests using TestClient
```

## Error Handling

The API implements comprehensive error handling with appropriate HTTP status codes:
- 404: Resource not found
- 400: Invalid request
- 500: Internal server error

All errors are logged with structured logging for easy debugging.

## Data Storage

The application uses TinyDB for data persistence, storing:
- List of tracked symbols
- Current asset metadata
- Historical price data
- Asset performance metrics

## Running Tests

This project uses **pytest** for unit and integration testing.

### How to Run All Tests

1. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run all tests (ensure PYTHONPATH is set correctly):
   ```bash
   PYTHONPATH=$(pwd) pytest
   ```

3. Generate a coverage report:
   ```bash
   pytest --cov=src tests/
   ```

### Test Coverage

The following API endpoints are covered:

- **GET /assets**: Fetch all tracked assets.
- **POST /assets**: Add new assets to track.
- **GET /metrics/{symbol}**: Fetch metrics for a specific symbol.
- **GET /assets/{symbol}/history**: Fetch historical data for a symbol.
- **GET /compare**: Compare two assets.
- **GET /summary**: Generate a summary for tracked assets.
- **POST /ingest**: Manually ingest/update asset data.

### Example Test Files

- `tests/test_api_endpoints.py`: Integration tests for all API endpoints.
- `tests/test_db_utils.py`: Unit tests for database utilities.
- `tests/test_asset_service.py`: Unit tests for service layer functions.
- `tests/test_integration_api.py`: Integration tests for API endpoints using `TestClient`.

### Additional Notes

- Ensure the `.env` file is properly configured with the `OPENAI_API_KEY` before running tests.
- Use the `--disable-warnings` flag with `pytest` to suppress warnings during test runs if needed.

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.