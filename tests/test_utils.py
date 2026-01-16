"""Tests for utility functions."""

import pytest
from datetime import datetime, time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.helpers import (
    normalize_ticker,
    format_currency,
    format_percentage,
    format_large_number,
    is_market_open,
)
from utils.validators import (
    validate_ticker,
    validate_price,
    extract_tickers_from_text,
)
from utils.math_tools import (
    calculate_cagr,
    calculate_pe_ratio,
    calculate_rsi,
    calculate_position_size,
)


class TestHelpers:
    """Test helper functions."""
    
    def test_normalize_ticker_simple(self):
        """Test simple ticker normalization."""
        assert normalize_ticker("reliance") == "RELIANCE.NS"
        assert normalize_ticker("TCS") == "TCS.NS"
        assert normalize_ticker("infy") == "INFY.NS"
    
    def test_normalize_ticker_with_suffix(self):
        """Test ticker already has suffix."""
        assert normalize_ticker("RELIANCE.NS") == "RELIANCE.NS"
        assert normalize_ticker("SBIN.BO") == "SBIN.BO"
    
    def test_normalize_ticker_bse(self):
        """Test BSE ticker normalization."""
        assert normalize_ticker("reliance", exchange="bse") == "RELIANCE.BO"
    
    def test_format_currency(self):
        """Test currency formatting."""
        assert format_currency(1234.56) == "₹1,234.56"
        assert format_currency(1234567.89) == "₹12,34,567.89"
        assert format_currency(-500) == "-₹500.00"
    
    def test_format_percentage(self):
        """Test percentage formatting."""
        assert format_percentage(5.5) == "+5.50%"
        assert format_percentage(-3.2) == "-3.20%"
        assert format_percentage(0) == "0.00%"
    
    def test_format_large_number(self):
        """Test large number formatting."""
        assert format_large_number(10000000) == "1.00 Cr"
        assert format_large_number(100000) == "1.00 L"
        assert format_large_number(1000) == "1,000"
        assert format_large_number(16500000000000) == "16,50,000.00 Cr"


class TestValidators:
    """Test validation functions."""
    
    def test_validate_ticker_valid(self):
        """Test valid ticker validation."""
        assert validate_ticker("TCS") == True
        assert validate_ticker("RELIANCE.NS") == True
        assert validate_ticker("INFY") == True
    
    def test_validate_ticker_invalid(self):
        """Test invalid ticker validation."""
        assert validate_ticker("") == False
        assert validate_ticker("A" * 25) == False
        assert validate_ticker("123") == False
        assert validate_ticker("@INVALID") == False
    
    def test_validate_price(self):
        """Test price validation."""
        assert validate_price(100.5) == True
        assert validate_price(0) == False
        assert validate_price(-50) == False
        assert validate_price("invalid") == False
    
    def test_extract_tickers_from_text(self):
        """Test ticker extraction from text."""
        text = "What do you think about TCS and INFY?"
        tickers = extract_tickers_from_text(text)
        assert "TCS" in tickers
        assert "INFY" in tickers
        
        text2 = "Compare RELIANCE vs HDFC"
        tickers2 = extract_tickers_from_text(text2)
        assert "RELIANCE" in tickers2
        assert "HDFC" in tickers2


class TestMathTools:
    """Test mathematical calculation functions."""
    
    def test_calculate_cagr(self):
        """Test CAGR calculation."""
        result = calculate_cagr(100, 200, 3)
        assert result.value is not None
        assert 25 < result.value < 27  # ~26% CAGR
        assert result.formula is not None
    
    def test_calculate_cagr_negative(self):
        """Test CAGR with decline."""
        result = calculate_cagr(200, 100, 3)
        assert result.value is not None
        assert result.value < 0
    
    def test_calculate_pe_ratio(self):
        """Test PE ratio calculation."""
        result = calculate_pe_ratio(100, 5)
        assert result.value == 20.0
        
        # Zero EPS
        result2 = calculate_pe_ratio(100, 0)
        assert result2.value is None
    
    def test_calculate_rsi(self):
        """Test RSI calculation."""
        # Uptrending prices
        prices = [100, 102, 104, 103, 105, 107, 106, 108, 110, 109, 111, 113, 112, 114, 116]
        result = calculate_rsi(prices)
        assert result.value is not None
        assert 0 <= result.value <= 100
        
        # Not enough data
        result2 = calculate_rsi([100, 102, 104])
        assert result2.value is None
    
    def test_calculate_position_size(self):
        """Test position sizing calculation."""
        result = calculate_position_size(
            portfolio_value=1000000,
            risk_percent=2.0,
            entry_price=100,
            stop_loss=95
        )
        assert result.value is not None
        # Risk = 2% of 1M = 20,000
        # Risk per share = 100 - 95 = 5
        # Shares = 20,000 / 5 = 4,000
        assert result.value == 4000


class TestDatabaseOperations:
    """Test database operations."""
    
    def test_create_user(self, test_db):
        """Test user creation."""
        user = test_db.get_or_create_user(
            telegram_id=111222333,
            username="test_user",
            first_name="Test"
        )
        assert user is not None
        assert user.telegram_id == 111222333
        assert user.username == "test_user"
    
    def test_get_existing_user(self, test_db):
        """Test getting existing user."""
        # Create first
        test_db.get_or_create_user(telegram_id=111222333)
        
        # Get again
        user = test_db.get_or_create_user(telegram_id=111222333)
        assert user is not None
        assert user.telegram_id == 111222333
    
    def test_add_to_portfolio(self, test_db):
        """Test adding to portfolio."""
        test_db.get_or_create_user(telegram_id=111222333)
        
        portfolio = test_db.add_to_portfolio(
            telegram_id=111222333,
            ticker="TCS.NS",
            quantity=10,
            avg_price=3500.0
        )
        
        assert portfolio is not None
        assert portfolio.ticker == "TCS.NS"
        assert portfolio.quantity == 10
    
    def test_get_portfolio(self, test_db):
        """Test getting portfolio."""
        test_db.get_or_create_user(telegram_id=111222333)
        test_db.add_to_portfolio(111222333, "TCS.NS", 10, 3500.0)
        test_db.add_to_portfolio(111222333, "INFY.NS", 20, 1500.0)
        
        portfolio = test_db.get_portfolio(111222333)
        assert len(portfolio) == 2
    
    def test_create_alert(self, test_db):
        """Test creating price alert."""
        test_db.get_or_create_user(telegram_id=111222333)
        
        alert = test_db.create_alert(
            telegram_id=111222333,
            ticker="RELIANCE.NS",
            target_price=2500.0,
            alert_type="above"
        )
        
        assert alert is not None
        assert alert.ticker == "RELIANCE.NS"
        assert alert.target_price == 2500.0
    
    def test_save_analysis(self, test_db):
        """Test saving analysis history."""
        test_db.get_or_create_user(telegram_id=111222333)
        
        analysis = test_db.save_analysis(
            telegram_id=111222333,
            ticker="TCS.NS",
            intent="full_analysis",
            recommendation="BUY",
            confidence=75.0,
            scores={
                "fundamental": 80,
                "technical": 70,
                "market_intel": 75,
                "risk": 65,
            }
        )
        
        assert analysis is not None
        assert analysis.recommendation == "BUY"
        assert analysis.fundamental_score == 80
    
    def test_get_analysis_history(self, test_db):
        """Test getting analysis history."""
        test_db.get_or_create_user(telegram_id=111222333)
        test_db.save_analysis(111222333, "TCS.NS", "full_analysis", "BUY", 75.0)
        test_db.save_analysis(111222333, "INFY.NS", "full_analysis", "HOLD", 60.0)
        
        history = test_db.get_analysis_history(111222333)
        assert len(history) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
