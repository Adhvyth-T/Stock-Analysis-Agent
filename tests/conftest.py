"""Test configuration and fixtures."""

import pytest
import asyncio
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.queries import DatabaseManager
from database.models import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test."""
    db = DatabaseManager("sqlite:///:memory:")
    db.create_tables()
    yield db
    db.drop_tables()


@pytest.fixture
def sample_stock_data():
    """Sample stock data for testing."""
    return {
        "ticker": "RELIANCE.NS",
        "price_data": {
            "current_price": 2456.80,
            "change_percent": 1.2,
            "volume": 8200000,
            "previous_close": 2427.50,
            "day_high": 2470.00,
            "day_low": 2445.00,
            "52_week_high": 2900.00,
            "52_week_low": 2150.00,
        },
        "fundamental_data": {
            "market_cap": 16500000000000,
            "pe_ratio": 24.5,
            "pb_ratio": 2.8,
            "eps": 100.28,
            "dividend_yield": 0.35,
            "roe": 18.5,
            "roce": 16.2,
            "debt_to_equity": 0.45,
        },
        "ownership_data": {
            "promoter_holding": 50.39,
            "fii_holding": 22.15,
            "dii_holding": 13.87,
            "public_holding": 13.59,
        },
    }


@pytest.fixture
def sample_historical_data():
    """Sample OHLCV historical data."""
    return [
        {"date": "2026-01-10", "open": 2430.0, "high": 2455.0, "low": 2420.0, "close": 2427.5, "volume": 7800000},
        {"date": "2026-01-09", "open": 2420.0, "high": 2445.0, "low": 2410.0, "close": 2430.0, "volume": 7500000},
        {"date": "2026-01-08", "open": 2410.0, "high": 2435.0, "low": 2400.0, "close": 2420.0, "volume": 8000000},
        {"date": "2026-01-07", "open": 2400.0, "high": 2420.0, "low": 2390.0, "close": 2410.0, "volume": 7200000},
        {"date": "2026-01-06", "open": 2395.0, "high": 2410.0, "low": 2385.0, "close": 2400.0, "volume": 6900000},
    ]


@pytest.fixture
def sample_news_data():
    """Sample news articles."""
    return [
        {
            "title": "Reliance Industries wins ₹5,000 Cr government contract",
            "source": "Economic Times",
            "url": "https://example.com/news/1",
            "published_at": "2026-01-10T10:30:00Z",
            "sentiment": "positive",
        },
        {
            "title": "RIL announces expansion plans in retail segment",
            "source": "Mint",
            "url": "https://example.com/news/2",
            "published_at": "2026-01-08T14:20:00Z",
            "sentiment": "positive",
        },
    ]


@pytest.fixture
def mock_telegram_user():
    """Mock Telegram user for testing."""
    class MockUser:
        id = 123456789
        username = "test_user"
        first_name = "Test"
        last_name = "User"
        is_bot = False
    
    return MockUser()


@pytest.fixture
def mock_telegram_update(mock_telegram_user):
    """Mock Telegram update for testing."""
    class MockChat:
        id = 123456789
        type = "private"
    
    class MockMessage:
        message_id = 1
        from_user = mock_telegram_user
        chat = MockChat()
        text = "/start"
        date = None
        
        async def reply_text(self, text, **kwargs):
            return text
    
    class MockUpdate:
        update_id = 1
        message = MockMessage()
        effective_user = mock_telegram_user
        effective_chat = MockChat()
    
    return MockUpdate()
