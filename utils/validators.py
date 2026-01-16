"""Input validation utilities."""

import re
from typing import Optional, Tuple


# Common Indian stock tickers for quick validation
COMMON_TICKERS = {
    "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "HINDUNILVR",
    "BHARTIARTL", "ITC", "SBIN", "KOTAKBANK", "LT", "AXISBANK",
    "BAJFINANCE", "ASIANPAINT", "MARUTI", "TITAN", "NESTLEIND",
    "WIPRO", "HCLTECH", "TECHM", "ADANIENT", "ADANIPORTS", "TATAMOTORS",
    "TATASTEEL", "JSWSTEEL", "POWERGRID", "NTPC", "ONGC", "COALINDIA",
    "SUNPHARMA", "DRREDDY", "CIPLA", "DIVISLAB", "APOLLOHOSP",
    "ULTRACEMCO", "GRASIM", "INDUSINDBK", "M&M", "BAJAJFINSV",
    "BRITANNIA", "EICHERMOT", "HEROMOTOCO", "BPCL", "TATACONSUM",
}


def validate_ticker(ticker: str) -> Tuple[bool, Optional[str], Optional[str]]:
    """
    Validate stock ticker symbol.
    
    Args:
        ticker: Raw ticker input from user
        
    Returns:
        Tuple of (is_valid, normalized_ticker, error_message)
    """
    if not ticker:
        return False, None, "Ticker symbol cannot be empty"
    
    # Clean input
    ticker = ticker.strip().upper()
    
    # Remove exchange prefix if present
    ticker = re.sub(r'^(NSE:|BSE:)', '', ticker)
    
    # Extract base ticker (remove .NS or .BO suffix)
    base_ticker = re.sub(r'\.(NS|BO)$', '', ticker)
    
    # Validate format: 1-20 alphanumeric characters, can include & and -
    if not re.match(r'^[A-Z0-9&\-]{1,20}$', base_ticker):
        return False, None, f"Invalid ticker format: {ticker}"
    
    # Determine exchange suffix
    if ticker.endswith('.BO'):
        normalized = ticker
    elif ticker.endswith('.NS'):
        normalized = ticker
    else:
        # Default to NSE
        normalized = f"{base_ticker}.NS"
    
    return True, normalized, None


def validate_price(price: str) -> Tuple[bool, Optional[float], Optional[str]]:
    """
    Validate price input.
    
    Args:
        price: Raw price input from user
        
    Returns:
        Tuple of (is_valid, parsed_price, error_message)
    """
    if not price:
        return False, None, "Price cannot be empty"
    
    # Remove currency symbols and commas
    price = re.sub(r'[₹$,\s]', '', price.strip())
    
    try:
        parsed = float(price)
        if parsed <= 0:
            return False, None, "Price must be positive"
        return True, parsed, None
    except ValueError:
        return False, None, f"Invalid price format: {price}"


def validate_quantity(quantity: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Validate quantity input.
    
    Args:
        quantity: Raw quantity input from user
        
    Returns:
        Tuple of (is_valid, parsed_quantity, error_message)
    """
    if not quantity:
        return False, None, "Quantity cannot be empty"
    
    try:
        parsed = int(quantity.strip())
        if parsed <= 0:
            return False, None, "Quantity must be positive"
        return True, parsed, None
    except ValueError:
        return False, None, f"Invalid quantity: {quantity}"


def extract_tickers_from_text(text: str) -> list[str]:
    """
    Extract potential stock tickers from text.
    
    Args:
        text: User input text
        
    Returns:
        List of potential ticker symbols
    """
    # Pattern to match ticker-like strings
    pattern = r'\b([A-Z]{2,20}(?:\.[NB][SO])?)\b'
    
    matches = re.findall(pattern, text.upper())
    
    # Filter to likely tickers
    tickers = []
    for match in matches:
        base = re.sub(r'\.[NB][SO]$', '', match)
        # Check if it's a known ticker or looks like one
        if base in COMMON_TICKERS or (len(base) >= 2 and len(base) <= 15):
            tickers.append(match)
    
    return list(set(tickers))
