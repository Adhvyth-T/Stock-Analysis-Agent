"""Database package - SQLAlchemy models and database operations."""

from database.models import (
    Base, 
    User, 
    Portfolio, 
    AnalysisHistory, 
    PriceAlert,
    ConversationContext,
    RiskAppetite,
    AlertStatus
)

__all__ = [
    "Base",
    "User", 
    "Portfolio",
    "AnalysisHistory",
    "PriceAlert",
    "ConversationContext",
    "RiskAppetite",
    "AlertStatus",
]

# Import DatabaseManager lazily to avoid circular imports
def get_db_manager():
    from database.queries import db_manager
    return db_manager
