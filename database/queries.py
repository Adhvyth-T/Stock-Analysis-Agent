"""Database query manager - handles all database operations."""

from datetime import datetime, timedelta
from typing import Optional, List
from contextlib import contextmanager

from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError

from database.models import (
    Base, User, Portfolio, AnalysisHistory, 
    PriceAlert, ConversationContext, RiskAppetite, AlertStatus
)
from config.settings import settings
from utils.logger import logger


class DatabaseManager:
    """Manages database connections and operations."""
    
    def __init__(self, db_url: Optional[str] = None):
        """Initialize database connection."""
        self.db_url = db_url or settings.DATABASE_URL

        connect_args = {}
        if "sqlite" in self.db_url:
    # SQLite needs check_same_thread=False for multi-threaded access
            connect_args = {"check_same_thread": False}
        self.db_url = db_url or settings.DATABASE_URL
        self.engine = create_engine(
            self.db_url,
            echo=settings.DEBUG,
            pool_pre_ping=True if "sqlite" not in self.db_url else False,
            connect_args=connect_args
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")
    
    def drop_tables(self):
        """Drop all database tables (use with caution!)."""
        Base.metadata.drop_all(bind=self.engine)
        logger.warning("All database tables dropped")
    
    @contextmanager
    def get_session(self):
        """Context manager for database sessions."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            session.close()
    
    # ==================== User Operations ====================
    
    def get_or_create_user(self, telegram_id: int, **kwargs) -> User:
        """Get existing user or create new one."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            
            if not user:
                user = User(
                    telegram_id=telegram_id,
                    username=kwargs.get("username"),
                    first_name=kwargs.get("first_name"),
                    last_name=kwargs.get("last_name"),
                )
                session.add(user)
                session.commit()
                session.refresh(user)
                logger.info(f"Created new user: {telegram_id}")
            else:
                # Update last active
                user.last_active = datetime.utcnow()
                if kwargs.get("username"):
                    user.username = kwargs.get("username")
                session.commit()
            
            return user
    
    def get_user(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        with self.get_session() as session:
            return session.query(User).filter(User.telegram_id == telegram_id).first()
    
    def update_user_preferences(
        self, 
        telegram_id: int, 
        risk_appetite: Optional[str] = None,
        portfolio_value: Optional[float] = None,
        investment_horizon: Optional[str] = None,
        **kwargs
    ) -> Optional[User]:
        """Update user preferences."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None
            
            if risk_appetite:
                try:
                    user.risk_appetite = RiskAppetite(risk_appetite.lower())
                except ValueError:
                    pass
            
            if portfolio_value is not None:
                user.portfolio_value = portfolio_value
            
            if investment_horizon:
                user.default_investment_horizon = investment_horizon
            
            # Update any additional kwargs
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            
            session.commit()
            session.refresh(user)
            session.expunge(user)
            return user
    
    def toggle_user_memory(self, telegram_id: int, enabled: bool) -> bool:
        """Enable/disable conversation memory for user."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            user.memory_enabled = enabled
            if not enabled:
                user.conversation_memory = None  # Clear memory when disabled
            session.commit()
            return True
    
    # ==================== Portfolio Operations ====================
    
    def add_to_portfolio(
        self, 
        telegram_id: int, 
        ticker: str, 
        quantity: int, 
        avg_price: float,
        **kwargs
    ) -> Optional[Portfolio]:
        """Add a holding to user's portfolio."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None
            
            # Check if already exists
            existing = session.query(Portfolio).filter(
                Portfolio.user_id == user.id,
                Portfolio.ticker == ticker.upper()
            ).first()
            
            if existing:
                # Update existing holding (average the price)
                total_value = (existing.quantity * existing.avg_price) + (quantity * avg_price)
                total_qty = existing.quantity + quantity
                existing.avg_price = total_value / total_qty
                existing.quantity = total_qty
                session.commit()
                session.refresh(existing)
                session.expunge(existing)
                return existing
            
            # Create new holding
            portfolio = Portfolio(
                user_id=user.id,
                ticker=ticker.upper(),
                quantity=quantity,
                avg_price=avg_price,
                buy_date=kwargs.get("buy_date"),
                target_price=kwargs.get("target_price"),
                stop_loss=kwargs.get("stop_loss"),
                notes=kwargs.get("notes"),
            )
            session.add(portfolio)
            session.commit()
            session.refresh(portfolio)
            session.expunge(portfolio)
            return portfolio
    
    def get_portfolio(self, telegram_id: int) -> List[Portfolio]:
        """Get all holdings for a user."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return []
            
            portfolios = session.query(Portfolio).filter(Portfolio.user_id == user.id).all()
            for portfolio in portfolios:
                session.expunge(portfolio)
            return portfolios
    
    def remove_from_portfolio(self, telegram_id: int, ticker: str) -> bool:
        """Remove a holding from portfolio."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            deleted = session.query(Portfolio).filter(
                Portfolio.user_id == user.id,
                Portfolio.ticker == ticker.upper()
            ).delete()
            
            session.commit()
            return deleted > 0
    
    def update_portfolio_prices(self, ticker: str, current_price: float):
        """Update current price for all holdings of a ticker."""
        with self.get_session() as session:
            holdings = session.query(Portfolio).filter(Portfolio.ticker == ticker.upper()).all()
            
            for holding in holdings:
                holding.current_price = current_price
                holding.current_value = holding.quantity * current_price
                holding.pnl = holding.current_value - (holding.quantity * holding.avg_price)
                holding.pnl_percent = (holding.pnl / (holding.quantity * holding.avg_price)) * 100
            
            session.commit()
    
    # ==================== Analysis History ====================
    
    def save_analysis(
        self,
        telegram_id: int,
        ticker: str,
        intent: str,
        recommendation: Optional[str] = None,
        confidence: Optional[float] = None,
        scores: Optional[dict] = None,
        full_output: Optional[dict] = None,
        execution_time: Optional[float] = None,
        **kwargs
    ) -> Optional[AnalysisHistory]:
        """Save an analysis to history."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None
            
            scores = scores or {}
            
            analysis = AnalysisHistory(
                user_id=user.id,
                ticker=ticker.upper(),
                intent=intent,
                recommendation=recommendation,
                confidence=confidence,
                fundamental_score=scores.get("fundamental"),
                technical_score=scores.get("technical"),
                market_intel_score=scores.get("market_intel"),
                risk_score=scores.get("risk"),
                price_at_analysis=kwargs.get("price"),
                target_price=kwargs.get("target_price"),
                stop_loss=kwargs.get("stop_loss"),
                full_output=full_output,
                execution_time_seconds=execution_time,
                agents_used=kwargs.get("agents_used"),
            )
            session.add(analysis)
            session.commit()
            session.refresh(analysis)
            session.expunge(analysis)
            return analysis
    
    def get_analysis_history(
        self, 
        telegram_id: int, 
        ticker: Optional[str] = None,
        limit: int = 10
    ) -> List[AnalysisHistory]:
        """Get analysis history for a user."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return []
            
            query = session.query(AnalysisHistory).filter(AnalysisHistory.user_id == user.id)
            
            if ticker:
                query = query.filter(AnalysisHistory.ticker == ticker.upper())
            
            analyses = query.order_by(desc(AnalysisHistory.created_at)).limit(limit).all()
            for analysis in analyses:
                session.expunge(analysis)
            return analyses
    
    def get_recent_analyses(self, hours: int = 24) -> List[AnalysisHistory]:
        """Get all analyses in the last N hours."""
        with self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(hours=hours)
            analyses = session.query(AnalysisHistory).filter(
                AnalysisHistory.created_at >= cutoff
            ).all()
            for analysis in analyses:
                session.expunge(analysis)
            return analyses
    
    # ==================== Price Alerts ====================
    
    def create_alert(
        self,
        telegram_id: int,
        ticker: str,
        target_price: float,
        alert_type: str,  # "above" or "below"
        current_price: Optional[float] = None,
        expires_in_days: Optional[int] = None
    ) -> Optional[PriceAlert]:
        """Create a price alert."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None
            
            alert = PriceAlert(
                user_id=user.id,
                ticker=ticker.upper(),
                target_price=target_price,
                alert_type=alert_type.lower(),
                price_when_set=current_price,
                status=AlertStatus.ACTIVE,
            )
            
            if expires_in_days:
                alert.expires_at = datetime.utcnow() + timedelta(days=expires_in_days)
            
            session.add(alert)
            session.commit()
            session.refresh(alert)
            session.expunge(alert)
            return alert

    def get_active_alerts(self, telegram_id: Optional[int] = None) -> List[PriceAlert]:
        """Get active alerts, optionally filtered by user."""
        with self.get_session() as session:
            query = session.query(PriceAlert).filter(PriceAlert.status == AlertStatus.ACTIVE)
            
            if telegram_id:
                user = session.query(User).filter(User.telegram_id == telegram_id).first()
                if user:
                    query = query.filter(PriceAlert.user_id == user.id)

            alerts = query.all()
            for alert in alerts:
                session.expunge(alert)
            return alerts
    
    def trigger_alert(self, alert_id: int, triggered_price: float) -> bool:
        """Mark an alert as triggered."""
        with self.get_session() as session:
            alert = session.query(PriceAlert).filter(PriceAlert.id == alert_id).first()
            if not alert:
                return False
            
            alert.status = AlertStatus.TRIGGERED
            alert.triggered_at = datetime.utcnow()
            alert.triggered_price = triggered_price
            session.commit()
            return True
    
    def cancel_alert(self, telegram_id: int, alert_id: int) -> bool:
        """Cancel an alert."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            alert = session.query(PriceAlert).filter(
                PriceAlert.id == alert_id,
                PriceAlert.user_id == user.id
            ).first()
            
            if not alert:
                return False
            
            alert.status = AlertStatus.CANCELLED
            session.commit()
            return True
    
    def check_alerts_for_ticker(self, ticker: str, current_price: float) -> List[tuple]:
        """Check if any alerts should be triggered for a ticker.
        
        Returns list of (alert, user_telegram_id) tuples for triggered alerts.
        """
        triggered = []
        
        with self.get_session() as session:
            alerts = session.query(PriceAlert, User.telegram_id).join(User).filter(
                PriceAlert.ticker == ticker.upper(),
                PriceAlert.status == AlertStatus.ACTIVE
            ).all()
            
            for alert, telegram_id in alerts:
                should_trigger = False
                
                if alert.alert_type == "above" and current_price >= alert.target_price:
                    should_trigger = True
                elif alert.alert_type == "below" and current_price <= alert.target_price:
                    should_trigger = True
                
                if should_trigger:
                    alert.status = AlertStatus.TRIGGERED
                    alert.triggered_at = datetime.utcnow()
                    alert.triggered_price = current_price
                    session.expunge(alert)
                    triggered.append((alert, telegram_id))

            session.commit()

        return triggered
    
    # ==================== Conversation Context ====================
    
    def get_context(self, telegram_id: int) -> Optional[ConversationContext]:
        """Get conversation context for user."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None
            
            context = session.query(ConversationContext).filter(
                ConversationContext.user_id == user.id
            ).first()
            if context:
                session.expunge(context)
            return context
    
    def update_context(
        self,
        telegram_id: int,
        context_data: Optional[dict] = None,
        last_ticker: Optional[str] = None,
        last_result: Optional[dict] = None,
    ) -> Optional[ConversationContext]:
        """Update or create conversation context."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return None
            
            context = session.query(ConversationContext).filter(
                ConversationContext.user_id == user.id
            ).first()
            
            if not context:
                context = ConversationContext(
                    user_id=user.id,
                    context_data=context_data or {},
                    expires_at=datetime.utcnow() + timedelta(hours=24)
                )
                session.add(context)
            else:
                if context_data:
                    context.context_data = context_data
                context.updated_at = datetime.utcnow()
                context.expires_at = datetime.utcnow() + timedelta(hours=24)
            
            if last_ticker:
                context.last_analysis_ticker = last_ticker
                # Update recent tickers list
                recent = context.recent_tickers or []
                if last_ticker not in recent:
                    recent = [last_ticker] + recent[:4]  # Keep last 5
                context.recent_tickers = recent
            
            if last_result:
                context.last_analysis_result = last_result

            session.commit()
            session.refresh(context)
            session.expunge(context)
            return context
    
    def clear_context(self, telegram_id: int) -> bool:
        """Clear conversation context for user."""
        with self.get_session() as session:
            user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not user:
                return False
            
            deleted = session.query(ConversationContext).filter(
                ConversationContext.user_id == user.id
            ).delete()
            
            session.commit()
            return deleted > 0
    
    # ==================== Cleanup Operations ====================
    
    def cleanup_old_analyses(self, days: int = 30) -> int:
        """Delete analyses older than N days."""
        with self.get_session() as session:
            cutoff = datetime.utcnow() - timedelta(days=days)
            deleted = session.query(AnalysisHistory).filter(
                AnalysisHistory.created_at < cutoff
            ).delete()
            session.commit()
            logger.info(f"Deleted {deleted} old analyses")
            return deleted
    
    def cleanup_expired_alerts(self) -> int:
        """Mark expired alerts."""
        with self.get_session() as session:
            now = datetime.utcnow()
            updated = session.query(PriceAlert).filter(
                PriceAlert.status == AlertStatus.ACTIVE,
                PriceAlert.expires_at < now
            ).update({PriceAlert.status: AlertStatus.EXPIRED})
            session.commit()
            return updated
    
    def cleanup_expired_contexts(self) -> int:
        """Delete expired conversation contexts."""
        with self.get_session() as session:
            now = datetime.utcnow()
            deleted = session.query(ConversationContext).filter(
                ConversationContext.expires_at < now
            ).delete()
            session.commit()
            return deleted


# Global instance
db_manager = DatabaseManager()
