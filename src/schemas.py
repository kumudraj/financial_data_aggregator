from typing import List, Optional, Dict

from pydantic import BaseModel, Field


class AssetMetrics(BaseModel):
    symbol: str
    latest_price: float
    change_percent_24h: float
    average_price_7d: float


class AssetWithMetadata(BaseModel):
    symbol: str
    latest_price: Optional[float] = None
    change_percent_24h: Optional[float] = None
    average_price_7d: Optional[float] = None
    last_updated: Optional[str] = None


class AssetComparison(BaseModel):
    asset1: AssetMetrics
    asset2: AssetMetrics
    price_difference: float
    performance_difference_24h: float


class Summary(BaseModel):
    summary: str


class SummaryRequest(BaseModel):
    symbol: Optional[str] = Field(
        default=None,
        description="Optional symbol to get summary for. If not provided, summary will be generated for all tracked assets."
    )


class Assets(BaseModel):
    assets: List[AssetWithMetadata] = Field(description="List of assets with their metadata")


class AddAssetsRequest(BaseModel):
    symbols: List[str] = Field(description="List of symbols to add", min_length=1)


class IngestRequest(BaseModel):
    assets: Optional[List[str]] = Field(
        default=None,
        description="Optional list of asset symbols to update. If not provided, all assets will be updated."
    )


class AssetHistoryEntry(BaseModel):
    symbol: str
    timestamp: str
    metadata: Dict[str, float]


class AssetHistory(BaseModel):
    history: List[AssetHistoryEntry]


class ErrorResponse(BaseModel):
    error: str
