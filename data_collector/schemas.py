"""Data schemas for stock information using Pydantic."""

from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class HistoricalOHLCV(BaseModel):
    """Historical OHLCV data point."""
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class PriceData(BaseModel):
    """Real-time price data."""
    current_price: float
    change_percent: float
    change_absolute: float = 0.0
    volume: int
    previous_close: float
    day_high: float
    day_low: float
    week_52_high: float = Field(alias="52_week_high", default=0.0)
    week_52_low: float = Field(alias="52_week_low", default=0.0)
    avg_volume: int = 0
    historical_ohlcv: List[HistoricalOHLCV] = []
    
    class Config:
        populate_by_name = True


class QuarterlyResults(BaseModel):
    """Quarterly financial results."""
    revenue: float = 0.0
    revenue_growth_yoy: float = 0.0
    net_profit: float = 0.0
    profit_growth_yoy: float = 0.0
    operating_margin: float = 0.0
    net_margin: float = 0.0


class FundamentalData(BaseModel):
    """Fundamental financial data."""
    market_cap: float = 0.0
    pe_ratio: Optional[float] = None
    pb_ratio: Optional[float] = None
    eps: Optional[float] = None
    dividend_yield: Optional[float] = None
    roe: Optional[float] = None
    roce: Optional[float] = None
    debt_to_equity: Optional[float] = None
    current_ratio: Optional[float] = None
    book_value: Optional[float] = None
    face_value: Optional[float] = None
    industry: str = ""
    sector: str = ""
    quarterly_results: Optional[QuarterlyResults] = None


class OwnershipData(BaseModel):
    """Shareholding pattern data."""
    promoter_holding: float = 0.0
    fii_holding: float = 0.0
    dii_holding: float = 0.0
    public_holding: float = 0.0
    pledged_shares: float = 0.0


class CorporateAction(BaseModel):
    """Corporate action details."""
    type: str  # dividend, split, bonus
    amount: Optional[float] = None
    ratio: Optional[str] = None  # For splits/bonus
    ex_date: Optional[str] = None
    record_date: Optional[str] = None


class StockData(BaseModel):
    """Complete stock data aggregation."""
    ticker: str
    name: str = ""
    timestamp: datetime = Field(default_factory=datetime.now)
    price_data: PriceData
    fundamental_data: Optional[FundamentalData] = None
    ownership_data: Optional[OwnershipData] = None
    corporate_actions: List[CorporateAction] = []
    
    @property
    def is_valid(self) -> bool:
        """Check if data is valid for analysis."""
        return self.price_data.current_price > 0


class NewsArticle(BaseModel):
    """Single news article."""
    title: str
    source: str
    url: str
    published_at: Optional[datetime] = None
    description: Optional[str] = None
    sentiment: Optional[str] = None  # positive, negative, neutral
    relevance: str = "medium"  # high, medium, low


class NewsData(BaseModel):
    """Aggregated news data."""
    ticker: str
    articles: List[NewsArticle] = []
    total_count: int = 0
    positive_count: int = 0
    negative_count: int = 0
    neutral_count: int = 0
    overall_sentiment: str = "neutral"
    fetched_at: datetime = Field(default_factory=datetime.now)


class MarketData(BaseModel):
    """Broad market data."""
    nifty_50: float = 0.0
    nifty_change_percent: float = 0.0
    sensex: float = 0.0
    sensex_change_percent: float = 0.0
    india_vix: float = 0.0
    market_status: str = "closed"
    fii_net_buy: Optional[float] = None
    dii_net_buy: Optional[float] = None
