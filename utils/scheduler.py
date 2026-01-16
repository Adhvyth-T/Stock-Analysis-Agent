"""Scheduler for daily portfolio analysis and other automated tasks."""

import asyncio
from datetime import datetime, time
from typing import Optional, Callable
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from loguru import logger
import pytz

from config.settings import settings
from database.queries import DatabaseManager


class PortfolioScheduler:
    """Scheduler for automated portfolio analysis."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        """Initialize scheduler."""
        self.db = db_manager or DatabaseManager()
        self.scheduler = AsyncIOScheduler(timezone=pytz.timezone("Asia/Kolkata"))
        self.is_running = False
        
        # Callback for sending Telegram messages
        self.telegram_callback: Optional[Callable] = None
    
    def set_telegram_callback(self, callback: Callable):
        """
        Set callback function for sending Telegram messages.
        
        Callback signature: async def send_message(telegram_id: int, message: str)
        """
        self.telegram_callback = callback
    
    def start(self):
        """Start the scheduler."""
        if self.is_running:
            logger.warning("Scheduler already running")
            return
        
        # Add daily portfolio analysis job (9:30 AM IST)
        self.scheduler.add_job(
            func=self._run_daily_portfolio_analysis,
            trigger=CronTrigger(hour=9, minute=30, timezone="Asia/Kolkata"),
            id="daily_portfolio_analysis",
            name="Daily Portfolio Analysis at 9:30 AM IST",
            replace_existing=True,
        )
        
        # Add cleanup jobs
        self.scheduler.add_job(
            func=self._cleanup_old_data,
            trigger=CronTrigger(hour=2, minute=0, timezone="Asia/Kolkata"),  # 2 AM daily
            id="daily_cleanup",
            name="Daily Data Cleanup",
            replace_existing=True,
        )
        
        self.scheduler.start()
        self.is_running = True
        logger.info("Portfolio scheduler started")
        logger.info("Daily portfolio analysis scheduled for 9:30 AM IST")
    
    def stop(self):
        """Stop the scheduler."""
        if not self.is_running:
            return
        
        self.scheduler.shutdown(wait=False)
        self.is_running = False
        logger.info("Portfolio scheduler stopped")
    
    def add_user_schedule(self, telegram_id: int, hour: int = 9, minute: int = 30):
        """
        Add custom schedule for a specific user.
        
        Args:
            telegram_id: User's Telegram ID
            hour: Hour (0-23)
            minute: Minute (0-59)
        """
        job_id = f"portfolio_analysis_{telegram_id}"
        
        # Remove existing job if present
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
        
        # Add new job
        self.scheduler.add_job(
            func=self._run_user_portfolio_analysis,
            trigger=CronTrigger(hour=hour, minute=minute, timezone="Asia/Kolkata"),
            args=[telegram_id],
            id=job_id,
            name=f"Portfolio Analysis for user {telegram_id}",
            replace_existing=True,
        )
        
        logger.info(f"Scheduled portfolio analysis for user {telegram_id} at {hour:02d}:{minute:02d} IST")
    
    def remove_user_schedule(self, telegram_id: int):
        """Remove custom schedule for a user."""
        job_id = f"portfolio_analysis_{telegram_id}"
        
        if self.scheduler.get_job(job_id):
            self.scheduler.remove_job(job_id)
            logger.info(f"Removed schedule for user {telegram_id}")
    
    def get_user_schedule(self, telegram_id: int) -> Optional[dict]:
        """Get schedule info for a user."""
        job_id = f"portfolio_analysis_{telegram_id}"
        job = self.scheduler.get_job(job_id)
        
        if not job:
            return None
        
        # Extract time from CronTrigger
        trigger = job.trigger
        if isinstance(trigger, CronTrigger):
            # Get next run time
            next_run = job.next_run_time
            return {
                "hour": trigger.fields[3].expressions[0].first,  # hour field
                "minute": trigger.fields[4].expressions[0].first,  # minute field
                "next_run": next_run.isoformat() if next_run else None,
            }
        
        return None
    
    async def _run_daily_portfolio_analysis(self):
        """Run portfolio analysis for all users with holdings."""
        logger.info("Starting daily portfolio analysis for all users")
        
        try:
            # Import here to avoid circular dependency
            from orchestrator.portfolio_workflow import PortfolioAnalysisWorkflow
            from telegram_bot.formatters import format_portfolio_analysis
            
            workflow = PortfolioAnalysisWorkflow(self.db)
            
            # Get all users with portfolios
            # This is a simplified version - you'd want to optimize this
            with self.db.get_session() as session:
                from database.models import User, Portfolio
                users_with_portfolios = session.query(User.telegram_id).join(
                    Portfolio, User.id == Portfolio.user_id
                ).distinct().all()
            
            logger.info(f"Found {len(users_with_portfolios)} users with portfolios")
            
            # Analyze each user's portfolio
            for (telegram_id,) in users_with_portfolios:
                try:
                    logger.info(f"Analyzing portfolio for user {telegram_id}")
                    
                    # Run analysis
                    result = await workflow.analyze_portfolio(telegram_id)
                    
                    # Format message
                    message = format_portfolio_analysis(result, daily=True)
                    
                    # Send via Telegram callback
                    if self.telegram_callback:
                        await self.telegram_callback(telegram_id, message)
                        logger.info(f"Sent portfolio analysis to user {telegram_id}")
                    
                    # Small delay between users to avoid rate limits
                    await asyncio.sleep(1)
                    
                except Exception as e:
                    logger.error(f"Error analyzing portfolio for user {telegram_id}: {e}")
                    continue
            
            logger.info("Daily portfolio analysis completed")
            
        except Exception as e:
            logger.error(f"Error in daily portfolio analysis: {e}")
    
    async def _run_user_portfolio_analysis(self, telegram_id: int):
        """Run portfolio analysis for a specific user."""
        logger.info(f"Running scheduled analysis for user {telegram_id}")
        
        try:
            from orchestrator.portfolio_workflow import PortfolioAnalysisWorkflow
            from telegram_bot.formatters import format_portfolio_analysis
            
            workflow = PortfolioAnalysisWorkflow(self.db)
            
            # Run analysis
            result = await workflow.analyze_portfolio(telegram_id)
            
            # Format message
            message = format_portfolio_analysis(result, daily=True)
            
            # Send via Telegram
            if self.telegram_callback:
                await self.telegram_callback(telegram_id, message)
            
        except Exception as e:
            logger.error(f"Error in scheduled analysis for user {telegram_id}: {e}")
    
    async def _cleanup_old_data(self):
        """Clean up old data from database."""
        logger.info("Running daily data cleanup")
        
        try:
            # Clean up old analyses (keep 30 days)
            deleted_analyses = self.db.cleanup_old_analyses(days=30)
            logger.info(f"Deleted {deleted_analyses} old analyses")
            
            # Clean up expired alerts
            expired_alerts = self.db.cleanup_expired_alerts()
            logger.info(f"Marked {expired_alerts} alerts as expired")
            
            # Clean up expired contexts
            deleted_contexts = self.db.cleanup_expired_contexts()
            logger.info(f"Deleted {deleted_contexts} expired contexts")
            
        except Exception as e:
            logger.error(f"Error in data cleanup: {e}")


# Helper function to format portfolio analysis for Telegram
def format_portfolio_analysis(result: dict, daily: bool = False) -> str:
    """
    Format portfolio analysis result for Telegram message.
    
    Args:
        result: Portfolio analysis result dict
        daily: Whether this is a daily automated analysis
        
    Returns:
        Formatted message string
    """
    if result.get("error"):
        return f"❌ Error: {result['error']}"
    
    # Header
    if daily:
        header = "🌅 *Good Morning! Daily Portfolio Analysis*\n"
        header += f"📅 {datetime.now().strftime('%d %b %Y, %I:%M %p')}\n\n"
    else:
        header = "📊 *Portfolio Analysis*\n\n"
    
    # Summary
    insights = result.get("portfolio_insights", {})
    emoji = insights.get("health_emoji", "⚪")
    
    summary = f"{emoji} *Portfolio Health:* {insights.get('overall_health', 'N/A')}\n"
    summary += f"💰 *Total Value:* ₹{result.get('total_value', 0):,.2f}\n"
    summary += f"📈 *Total P&L:* ₹{result.get('total_pnl', 0):,.2f} "
    summary += f"({result.get('total_pnl_percent', 0):+.2f}%)\n"
    summary += f"📦 *Holdings:* {result.get('total_holdings', 0)} stocks\n\n"
    
    # Urgent actions
    urgent = insights.get("urgent_actions", 0)
    high = insights.get("high_priority_actions", 0)
    
    if urgent > 0 or high > 0:
        summary += "⚠️ *ACTION REQUIRED*\n"
        if urgent > 0:
            summary += f"  🔴 {urgent} URGENT action(s)\n"
        if high > 0:
            summary += f"  🟠 {high} HIGH priority action(s)\n"
        summary += "\n"
    
    # Stock-by-stock breakdown
    stocks_msg = "━━━━━━━━━━━━━━━━━━━━\n\n"
    
    analyses = result.get("stock_analyses", [])
    
    # Sort by priority: URGENT > HIGH > MEDIUM > LOW
    priority_order = {"URGENT": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    sorted_analyses = sorted(
        analyses,
        key=lambda x: priority_order.get(x.get("priority", "LOW"), 3)
    )
    
    for idx, analysis in enumerate(sorted_analyses, 1):
        ticker = analysis.get("ticker", "Unknown")
        pnl_percent = analysis.get("pnl_percent", 0)
        action = analysis.get("action", "HOLD")
        priority = analysis.get("priority", "LOW")
        reason = analysis.get("action_reason", "")
        
        # Priority emoji
        priority_emoji = {
            "URGENT": "🔴",
            "HIGH": "🟠",
            "MEDIUM": "🟡",
            "LOW": "🟢",
        }
        
        # Action emoji
        action_emoji = {
            "HOLD": "✋",
            "ADD_MORE": "➕",
            "BOOK_PARTIAL_25": "💰",
            "BOOK_PARTIAL_50": "💰",
            "BOOK_ALL": "🚪",
            "STOP_LOSS_HIT": "🛑",
            "TRAILING_STOP": "📍",
        }
        
        stocks_msg += f"{idx}. *{ticker}*\n"
        stocks_msg += f"   Current: ₹{analysis.get('current_price', 0):.2f} | "
        stocks_msg += f"P&L: {pnl_percent:+.1f}%\n"
        stocks_msg += f"   {priority_emoji.get(priority, '⚪')} {action_emoji.get(action, '📊')} "
        stocks_msg += f"*{action.replace('_', ' ')}*\n"
        stocks_msg += f"   {reason}\n\n"
    
    # Action summary
    actions_summary = result.get("actions_summary", {})
    actions_msg = "━━━━━━━━━━━━━━━━━━━━\n\n"
    actions_msg += "*Action Summary:*\n"
    
    action_labels = {
        "STOP_LOSS_HIT": "🛑 Stop Loss Hit",
        "BOOK_ALL": "🚪 Exit Completely",
        "BOOK_PARTIAL_50": "💰 Book 50% Profit",
        "BOOK_PARTIAL_25": "💰 Book 25% Profit",
        "ADD_MORE": "➕ Add More",
        "TRAILING_STOP": "📍 Use Trailing Stop",
        "HOLD": "✋ Hold",
    }
    
    for action, tickers in actions_summary.items():
        if tickers:
            label = action_labels.get(action, action)
            stocks = ", ".join(tickers)
            actions_msg += f"{label}: {stocks}\n"
    
    # Footer
    if daily:
        footer = "\n_Use /portfolio for detailed view_\n"
        footer += "_Reply to change schedule or disable_"
    else:
        footer = "\n_Analysis based on current market conditions_\n"
        footer += "_Not financial advice. Do your own research._"
    
    return header + summary + stocks_msg + actions_msg + footer


# Global scheduler instance
_scheduler: Optional[PortfolioScheduler] = None


def get_scheduler(db_manager: Optional[DatabaseManager] = None) -> PortfolioScheduler:
    """Get or create global scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = PortfolioScheduler(db_manager)
    return _scheduler
