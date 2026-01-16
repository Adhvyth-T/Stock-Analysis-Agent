"""SQLAlchemy database models."""

from datetime import datetime
from typing import Optional
from sqlalchemy import (
    Column, Integer, BigInteger, String, Float, DateTime, 
    Boolean, Text, JSON, ForeignKey, Index, Enum as SQLEnum
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import enum

Base = declarative_base()


class RiskAppetite(enum.Enum):
    """User risk appetite levels."""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class AlertStatus(enum.Enum):
    """Price alert status."""
    ACTIVE = "active"
    TRIGGERED = "triggered"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class User(Base):
    """User model - stores Telegram user information and preferences."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    telegram_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    
    # User preferences
    risk_appetite = Column(
        SQLEnum(RiskAppetite), 
        default=RiskAppetite.MODERATE,
        nullable=False
    )
    default_investment_horizon = Column(String(50), default="medium")  # short, medium, long
    portfolio_value = Column(Float, default=1000000.0)  # Assumed portfolio value for position sizing
    preferred_sectors = Column(JSON, nullable=True)  # List of preferred sectors
    
    # Feature flags
    detailed_responses = Column(Boolean, default=False)  # Enable verbose responses
    include_technicals = Column(Boolean, default=True)
    include_fundamentals = Column(Boolean, default=True)
    include_news = Column(Boolean, default=True)
    
    # Conversation memory (for /rememberconv feature)
    conversation_memory = Column(JSON, nullable=True)  # Stores context if enabled
    memory_enabled = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    last_active = Column(DateTime, default=func.now())
    
    # Relationships
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")
    analysis_history = relationship("AnalysisHistory", back_populates="user", cascade="all, delete-orphan")
    price_alerts = relationship("PriceAlert", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(telegram_id={self.telegram_id}, username={self.username})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "telegram_id": self.telegram_id,
            "username": self.username,
            "risk_appetite": self.risk_appetite.value if self.risk_appetite else "moderate",
            "portfolio_value": self.portfolio_value,
            "memory_enabled": self.memory_enabled,
        }


class Portfolio(Base):
    """Portfolio holdings for a user."""
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    ticker = Column(String(20), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    avg_price = Column(Float, nullable=False)
    buy_date = Column(DateTime, nullable=True)
    
    # Current values (updated periodically)
    current_price = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    pnl = Column(Float, nullable=True)  # Profit/Loss
    pnl_percent = Column(Float, nullable=True)
    
    # Optional notes
    notes = Column(Text, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    
    # Relationship
    user = relationship("User", back_populates="portfolios")
    
    # Composite index for user + ticker
    __table_args__ = (
        Index('idx_user_ticker', 'user_id', 'ticker'),
    )
    
    def __repr__(self):
        return f"<Portfolio(ticker={self.ticker}, qty={self.quantity}, avg={self.avg_price})>"
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "quantity": self.quantity,
            "avg_price": self.avg_price,
            "current_price": self.current_price,
            "current_value": self.current_value,
            "pnl": self.pnl,
            "pnl_percent": self.pnl_percent,
        }


class AnalysisHistory(Base):
    """Stores history of stock analyses performed."""
    __tablename__ = "analysis_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Analysis details
    ticker = Column(String(20), nullable=False, index=True)
    intent = Column(String(50), nullable=False)  # price_check, full_analysis, technical, etc.
    
    # Results
    recommendation = Column(String(20), nullable=True)  # BUY, HOLD, SELL, AVOID
    confidence = Column(Float, nullable=True)
    
    # Scores from agents
    fundamental_score = Column(Float, nullable=True)
    technical_score = Column(Float, nullable=True)
    market_intel_score = Column(Float, nullable=True)
    risk_score = Column(Float, nullable=True)
    
    # Price at time of analysis
    price_at_analysis = Column(Float, nullable=True)
    target_price = Column(Float, nullable=True)
    stop_loss = Column(Float, nullable=True)
    
    # Full output stored as JSON
    full_output = Column(JSON, nullable=True)
    
    # Execution metrics
    execution_time_seconds = Column(Float, nullable=True)
    agents_used = Column(JSON, nullable=True)  # List of agent names used
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False, index=True)
    
    # Relationship
    user = relationship("User", back_populates="analysis_history")
    
    def __repr__(self):
        return f"<AnalysisHistory(ticker={self.ticker}, rec={self.recommendation})>"
    
    def to_dict(self) -> dict:
        return {
            "ticker": self.ticker,
            "intent": self.intent,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "price_at_analysis": self.price_at_analysis,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class PriceAlert(Base):
    """Price alerts set by users."""
    __tablename__ = "price_alerts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    ticker = Column(String(20), nullable=False, index=True)
    target_price = Column(Float, nullable=False)
    alert_type = Column(String(20), nullable=False)  # "above" or "below"
    
    # Status tracking
    status = Column(
        SQLEnum(AlertStatus),
        default=AlertStatus.ACTIVE,
        nullable=False
    )
    
    # Price when alert was set
    price_when_set = Column(Float, nullable=True)
    
    # When triggered
    triggered_at = Column(DateTime, nullable=True)
    triggered_price = Column(Float, nullable=True)
    
    # Optional expiry
    expires_at = Column(DateTime, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    
    # Relationship
    user = relationship("User", back_populates="price_alerts")
    
    # Index for active alerts lookup
    __table_args__ = (
        Index('idx_active_alerts', 'status', 'ticker'),
    )
    
    def __repr__(self):
        return f"<PriceAlert(ticker={self.ticker}, target={self.target_price}, type={self.alert_type})>"
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "ticker": self.ticker,
            "target_price": self.target_price,
            "alert_type": self.alert_type,
            "status": self.status.value if self.status else "active",
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class ConversationContext(Base):
    """Stores conversation context for stateful conversations."""
    __tablename__ = "conversation_contexts"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Context data
    context_data = Column(JSON, nullable=False, default=dict)
    
    # Recent tickers discussed
    recent_tickers = Column(JSON, nullable=True)  # List of recently discussed tickers
    
    # Last analysis results (for follow-up questions)
    last_analysis_ticker = Column(String(20), nullable=True)
    last_analysis_result = Column(JSON, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime, default=func.now(), nullable=False)
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    expires_at = Column(DateTime, nullable=True)  # Auto-expire old contexts
    
    def __repr__(self):
        return f"<ConversationContext(user_id={self.user_id})>"
