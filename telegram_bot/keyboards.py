"""Telegram inline keyboards."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def get_price_keyboard(ticker: str) -> InlineKeyboardMarkup:
    """Get keyboard for price check response."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Full Analysis", callback_data=f"analyze_{ticker}"),
            InlineKeyboardButton("📈 Technical", callback_data=f"technical_{ticker}"),
        ],
        [
            InlineKeyboardButton("💼 Fundamentals", callback_data=f"fundamental_{ticker}"),
            InlineKeyboardButton("📰 News", callback_data=f"news_{ticker}"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh", callback_data=f"price_{ticker}"),
        ],
    ])


def get_analysis_keyboard(ticker: str) -> InlineKeyboardMarkup:
    """Get keyboard for analysis response."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔍 Deep Dive", callback_data=f"deepdive_{ticker}"),
            InlineKeyboardButton("📰 Latest News", callback_data=f"news_{ticker}"),
        ],
        [
            InlineKeyboardButton("📈 Technical", callback_data=f"technical_{ticker}"),
            InlineKeyboardButton("💼 Fundamentals", callback_data=f"fundamental_{ticker}"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Analysis", callback_data=f"analyze_{ticker}"),
        ],
    ])


def get_comparison_keyboard(ticker1: str, ticker2: str) -> InlineKeyboardMarkup:
    """Get keyboard for comparison response."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"📊 {ticker1} Full", callback_data=f"analyze_{ticker1}"),
            InlineKeyboardButton(f"📊 {ticker2} Full", callback_data=f"analyze_{ticker2}"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Comparison", callback_data=f"compare_{ticker1}_{ticker2}"),
        ],
    ])


def get_single_analysis_keyboard(ticker: str, analysis_type: str) -> InlineKeyboardMarkup:
    """Get keyboard for single aspect analysis."""
    buttons = [
        [InlineKeyboardButton("📊 Full Analysis", callback_data=f"analyze_{ticker}")],
    ]
    
    if analysis_type != "technical":
        buttons.append([InlineKeyboardButton("📈 Technical", callback_data=f"technical_{ticker}")])
    if analysis_type != "fundamental":
        buttons.append([InlineKeyboardButton("💼 Fundamentals", callback_data=f"fundamental_{ticker}")])
    if analysis_type != "news":
        buttons.append([InlineKeyboardButton("📰 News", callback_data=f"news_{ticker}")])
    
    return InlineKeyboardMarkup(buttons)


def get_error_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for error messages."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📚 Help", callback_data="help")],
    ])


def get_help_keyboard() -> InlineKeyboardMarkup:
    """Get keyboard for help message."""
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("💹 Price Example", callback_data="example_price"),
            InlineKeyboardButton("📊 Analysis Example", callback_data="example_analysis"),
        ],
        [
            InlineKeyboardButton("📈 Compare Example", callback_data="example_compare"),
        ],
    ])
