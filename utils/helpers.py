"""Helper utility functions."""

from datetime import datetime, time as Time
from typing import Optional
import pytz
import re


# Indian timezone
IST = pytz.timezone("Asia/Kolkata")


def normalize_ticker(ticker: str) -> str:
    """
    Normalize ticker symbol to NSE/BSE format.
    
    Examples:
        'reliance' -> 'RELIANCE.NS'
        'TCS' -> 'TCS.NS'
        'INFY.NS' -> 'INFY.NS'
        'HDFC.BO' -> 'HDFC.BO'
    """
    ticker = ticker.strip().upper()
    
    # Remove common prefixes/suffixes
    ticker = re.sub(r'^(NSE:|BSE:)', '', ticker)
    
    # If already has exchange suffix, return as is
    if ticker.endswith('.NS') or ticker.endswith('.BO'):
        return ticker
    
    # Default to NSE
    return f"{ticker}.NS"


def format_currency(amount: float, symbol: str = "₹") -> str:
    """Format amount as Indian currency."""
    if amount >= 10000000:  # Crore
        return f"{symbol}{amount/10000000:.2f} Cr"
    elif amount >= 100000:  # Lakh
        return f"{symbol}{amount/100000:.2f} L"
    elif amount >= 1000:  # Thousand
        return f"{symbol}{amount/1000:.2f} K"
    else:
        return f"{symbol}{amount:.2f}"


def format_percentage(value: float, decimals: int = 2) -> str:
    """Format value as percentage with sign."""
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.{decimals}f}%"


def format_large_number(num: float) -> str:
    """Format large numbers in Indian notation (Cr, L)."""
    if num >= 1e12:  # Lakh Crore
        return f"{num/1e12:.2f} L Cr"
    elif num >= 1e7:  # Crore
        return f"{num/1e7:.2f} Cr"
    elif num >= 1e5:  # Lakh
        return f"{num/1e5:.2f} L"
    elif num >= 1e3:  # Thousand
        return f"{num/1e3:.2f} K"
    else:
        return f"{num:.2f}"


def get_indian_time() -> datetime:
    """Get current time in IST."""
    return datetime.now(IST)


def is_market_open() -> tuple[bool, str]:
    now = get_indian_time()
    current_time = now.time()
    
    # Market hours: 9:15 AM - 3:30 PM IST
    market_open = Time(9, 15)
    market_close = Time(15, 30)
    
    # Check if weekend
    if now.weekday() >= 5:
        return False, "🔴 Market Closed (Weekend)"
    
    # Check time
    if current_time < market_open:
        return False, "🔴 Pre-market (Opens at 9:15 AM IST)"
    elif current_time > market_close:
        return False, "🔴 Market Closed (Closed at 3:30 PM IST)"
    else:
        return True, "🟢 Market Open"


def calculate_percentage_change(old_value: float, new_value: float) -> float:
    """Calculate percentage change between two values."""
    if old_value == 0:
        return 0.0
    return ((new_value - old_value) / old_value) * 100


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text to max length with ellipsis."""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def parse_timeframe(timeframe: str) -> Optional[int]:
    """
    Parse timeframe string to days.
    
    Examples:
        '1d' -> 1
        '1w' -> 7
        '1m' -> 30
        '3m' -> 90
        '1y' -> 365
    """
    timeframe = timeframe.lower().strip()
    
    patterns = {
        r'(\d+)d': lambda m: int(m.group(1)),
        r'(\d+)w': lambda m: int(m.group(1)) * 7,
        r'(\d+)m': lambda m: int(m.group(1)) * 30,
        r'(\d+)y': lambda m: int(m.group(1)) * 365,
    }
    
    for pattern, converter in patterns.items():
        match = re.match(pattern, timeframe)
        if match:
            return converter(match)
    
    return None
