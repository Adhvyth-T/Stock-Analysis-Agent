"""Portfolio Analysis Workflow - Analyzes all stocks in user's portfolio."""

import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from loguru import logger

from database.queries import DatabaseManager
from data_collector.yahoo_finance import YahooFinanceCollector
from agents.fundamental_agent import FundamentalAgent
from agents.technical_agent import TechnicalAgent
from agents.market_intel_agent import MarketIntelAgent
from agents.risk_agent import RiskAgent
from agents.synthesizer_agent import SynthesizerAgent
from data_collector.cache_manager import CacheManager


class PortfolioAction:
    """Portfolio action recommendations."""
    HOLD = "HOLD"
    ADD_MORE = "ADD_MORE"
    BOOK_PARTIAL_25 = "BOOK_PARTIAL_25"
    BOOK_PARTIAL_50 = "BOOK_PARTIAL_50"
    BOOK_ALL = "BOOK_ALL"
    STOP_LOSS_HIT = "STOP_LOSS_HIT"
    REBALANCE = "REBALANCE"
    TRAILING_STOP = "TRAILING_STOP"


class PortfolioAnalysisWorkflow:
    """Orchestrates portfolio-wide analysis."""
    
    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db = db_manager or DatabaseManager()
        self.cache = CacheManager()
        self.yahoo = YahooFinanceCollector()
        
        # Initialize agents
        self.fundamental_agent = FundamentalAgent()
        self.technical_agent = TechnicalAgent()
        self.market_intel_agent = MarketIntelAgent()
        self.risk_agent = RiskAgent()
        self.synthesizer_agent = SynthesizerAgent()
    
    async def analyze_portfolio(
        self,
        telegram_id: int,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Analyze entire portfolio and generate action recommendations.
        
        Args:
            telegram_id: User's Telegram ID
            progress_callback: Optional async callback for progress updates
            
        Returns:
            Dict with portfolio analysis results
        """
        logger.info(f"Starting portfolio analysis for user {telegram_id}")
        
        # Get user and portfolio
        user = self.db.get_user(telegram_id)
        if not user:
            return {"error": "User not found"}
        
        holdings = self.db.get_portfolio(telegram_id)
        if not holdings:
            return {"error": "Portfolio is empty"}
        
        if progress_callback:
            await progress_callback(f"📊 Analyzing {len(holdings)} stocks in your portfolio...")
        
        # Analyze each stock
        stock_analyses = []
        total_value = 0
        total_pnl = 0
        
        for idx, holding in enumerate(holdings, 1):
            if progress_callback:
                await progress_callback(f"⏳ Analyzing {holding.ticker} ({idx}/{len(holdings)})...")
            
            try:
                analysis = await self._analyze_single_holding(holding, user)
                stock_analyses.append(analysis)
                
                # Update totals
                if analysis.get("current_value"):
                    total_value += analysis["current_value"]
                if analysis.get("pnl"):
                    total_pnl += analysis["pnl"]
                
            except Exception as e:
                logger.error(f"Error analyzing {holding.ticker}: {e}")
                stock_analyses.append({
                    "ticker": holding.ticker,
                    "error": str(e),
                    "action": PortfolioAction.HOLD,
                })
        
        # Calculate portfolio metrics
        total_invested = sum(h.quantity * h.avg_price for h in holdings)
        total_pnl_percent = (total_pnl / total_invested * 100) if total_invested > 0 else 0
        
        # Categorize by action
        actions_summary = self._categorize_actions(stock_analyses)
        
        # Generate portfolio-level insights
        portfolio_insights = self._generate_portfolio_insights(
            stock_analyses,
            total_value,
            total_pnl_percent,
            actions_summary
        )
        
        result = {
            "user_id": telegram_id,
            "analysis_date": datetime.now(timezone.utc).isoformat(),
            "total_holdings": len(holdings),
            "total_invested": total_invested,
            "total_value": total_value,
            "total_pnl": total_pnl,
            "total_pnl_percent": round(total_pnl_percent, 2),
            "stock_analyses": stock_analyses,
            "actions_summary": actions_summary,
            "portfolio_insights": portfolio_insights,
        }
        
        # Save to database
        try:
            self.db.save_analysis(
                telegram_id=telegram_id,
                ticker="PORTFOLIO",
                intent="portfolio_analysis",
                full_output=result,
            )
        except Exception as e:
            logger.error(f"Error saving portfolio analysis: {e}")
        
        return result
    
    async def _analyze_single_holding(
        self,
        holding: Any,  # Portfolio model instance
        user: Any,  # User model instance
    ) -> Dict[str, Any]:
        """Analyze a single portfolio holding with action recommendation."""
        
        ticker = holding.ticker
        
        # Fetch current data
        stock_data = await self.yahoo.get_stock_data(ticker, include_historical=True)
        if not stock_data:
            return {
                "ticker": ticker,
                "error": "Could not fetch data",
                "action": PortfolioAction.HOLD,
            }
        
        # Calculate current metrics
        current_price = stock_data.price_data.current_price
        current_value = holding.quantity * current_price
        cost_basis = holding.quantity * holding.avg_price
        pnl = current_value - cost_basis
        pnl_percent = (pnl / cost_basis * 100) if cost_basis > 0 else 0
        
        # Days held
        days_held = 0
        if holding.buy_date:
            days_held = (datetime.now(timezone.utc) - holding.buy_date).days
        
        # Run lightweight analysis (parallel)
        try:
            
            fund_task = self.fundamental_agent.analyze({
                'stock_data': stock_data.model_dump(),
                'ticker': ticker
            })
            tech_task = self.technical_agent.analyze({
                'stock_data': stock_data.model_dump(),
                'ticker': ticker
            })
            
            fundamental, technical = await asyncio.gather(
                fund_task, tech_task, return_exceptions=True
            )
            
            if isinstance(fundamental, Exception):
                fundamental = None
            if isinstance(technical, Exception):
                technical = None
                
        except Exception as e:
            logger.error(f"Error in parallel analysis for {ticker}: {e}")
            fundamental = None
            technical = None
        
        # Determine action based on portfolio context
        action_result = self._determine_action(
            holding=holding,
            current_price=current_price,
            pnl_percent=pnl_percent,
            days_held=days_held,
            fundamental=fundamental,
            technical=technical,
            user=user,
        )
        
        return {
            "ticker": ticker,
            "name": stock_data.name,
            "quantity": holding.quantity,
            "avg_buy_price": holding.avg_price,
            "current_price": current_price,
            "current_value": current_value,
            "cost_basis": cost_basis,
            "pnl": pnl,
            "pnl_percent": round(pnl_percent, 2),
            "days_held": days_held,
            "action": action_result["action"],
            "action_reason": action_result["reason"],
            "priority": action_result["priority"],
            "fundamental_score": fundamental.get("score") if fundamental else None,
            "technical_score": technical.get("score") if technical else None,
            "notes": action_result.get("notes", []),
        }
    
    def _determine_action(
        self,
        holding: Any,
        current_price: float,
        pnl_percent: float,
        days_held: int,
        fundamental: Optional[Dict],
        technical: Optional[Dict],
        user: Any,
    ) -> Dict[str, Any]:
        """
        Determine action recommendation based on portfolio context.
        
        Priority: URGENT > HIGH > MEDIUM > LOW
        """
        
        action = PortfolioAction.HOLD
        reason = ""
        priority = "LOW"
        notes = []
        
        # Get scores
        fund_score = fundamental.get("score", 50) if fundamental else 50
        tech_score = technical.get("score", 50) if technical else 50
        
        # Check stop loss first (URGENT)
        if holding.stop_loss:
            stop_loss_distance = ((current_price - holding.stop_loss) / holding.stop_loss) * 100
            if stop_loss_distance <= 2:  # Within 2% of stop loss
                action = PortfolioAction.STOP_LOSS_HIT
                reason = f"Price near stop loss (₹{holding.stop_loss})"
                priority = "URGENT"
                notes.append(f"Current: ₹{current_price:.2f}, Stop: ₹{holding.stop_loss:.2f}")
                return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Check large losses (URGENT)
        if pnl_percent <= -15:
            if fund_score < 40:  # Fundamentals deteriorated
                action = PortfolioAction.BOOK_ALL
                reason = f"Large loss ({pnl_percent:.1f}%) with weak fundamentals"
                priority = "URGENT"
            else:
                action = PortfolioAction.HOLD
                reason = f"Down {pnl_percent:.1f}% but fundamentals intact - hold through volatility"
                priority = "HIGH"
            notes.append(f"Fundamental score: {fund_score}/100")
            return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Check target price achievement (HIGH)
        if holding.target_price and current_price >= holding.target_price:
            action = PortfolioAction.BOOK_PARTIAL_50
            reason = f"Target ₹{holding.target_price} reached"
            priority = "HIGH"
            notes.append(f"Consider moving to trailing stop")
            return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Check large profits (HIGH)
        if pnl_percent >= 25:
            if tech_score < 45:  # Technical weakening
                action = PortfolioAction.BOOK_PARTIAL_50
                reason = f"Profit {pnl_percent:.1f}% but technicals weakening"
                priority = "HIGH"
            elif pnl_percent >= 50:  # Very large profit
                action = PortfolioAction.BOOK_PARTIAL_25
                reason = f"Large profit ({pnl_percent:.1f}%) - secure some gains"
                priority = "MEDIUM"
            else:
                action = PortfolioAction.TRAILING_STOP
                reason = f"Good profit ({pnl_percent:.1f}%) - use trailing stop"
                priority = "MEDIUM"
            notes.append(f"Technical score: {tech_score}/100")
            return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Check fundamental deterioration (HIGH)
        if fund_score < 35:
            action = PortfolioAction.BOOK_ALL
            reason = "Fundamentals severely deteriorated"
            priority = "HIGH"
            notes.append(f"Fundamental score dropped to {fund_score}/100")
            return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Check technical breakout opportunity (MEDIUM)
        if tech_score >= 75 and pnl_percent < 10:
            action = PortfolioAction.ADD_MORE
            reason = "Strong technical setup - good to add"
            priority = "MEDIUM"
            notes.append(f"Technical score: {tech_score}/100")
            notes.append(f"Current position profitable by {pnl_percent:.1f}%")
            return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Check modest profit opportunities (MEDIUM)
        if 10 <= pnl_percent < 25:
            if fund_score >= 70 and tech_score >= 65:
                action = PortfolioAction.HOLD
                reason = f"Profit {pnl_percent:.1f}% - strong fundamentals & technicals, hold for more"
                priority = "LOW"
            else:
                action = PortfolioAction.BOOK_PARTIAL_25
                reason = f"Profit {pnl_percent:.1f}% - secure partial gains"
                priority = "MEDIUM"
            notes.append(f"Fund: {fund_score}/100, Tech: {tech_score}/100")
            return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Small loss range (-15% to 0%)
        if -15 < pnl_percent < 0:
            if fund_score >= 70 and tech_score >= 60:
                action = PortfolioAction.ADD_MORE
                reason = f"Down {pnl_percent:.1f}% but fundamentals strong - buying opportunity"
                priority = "MEDIUM"
            else:
                action = PortfolioAction.HOLD
                reason = f"Down {pnl_percent:.1f}% - monitor for improvement"
                priority = "LOW"
            notes.append(f"Fund: {fund_score}/100, Tech: {tech_score}/100")
            return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Small profit range (0% to 10%)
        if 0 <= pnl_percent < 10:
            if fund_score >= 70 and tech_score >= 70:
                action = PortfolioAction.HOLD
                reason = f"Up {pnl_percent:.1f}% with strong outlook - hold for more"
                priority = "LOW"
            else:
                action = PortfolioAction.HOLD
                reason = f"Up {pnl_percent:.1f}% - no action needed"
                priority = "LOW"
            notes.append(f"Fund: {fund_score}/100, Tech: {tech_score}/100")
            return {"action": action, "reason": reason, "priority": priority, "notes": notes}
        
        # Default: HOLD
        action = PortfolioAction.HOLD
        reason = "Position stable - continue monitoring"
        priority = "LOW"
        notes.append(f"Fund: {fund_score}/100, Tech: {tech_score}/100")
        
        return {"action": action, "reason": reason, "priority": priority, "notes": notes}
    
    def _categorize_actions(self, analyses: List[Dict]) -> Dict[str, List[str]]:
        """Categorize stocks by recommended action."""
        categories = {
            PortfolioAction.HOLD: [],
            PortfolioAction.ADD_MORE: [],
            PortfolioAction.BOOK_PARTIAL_25: [],
            PortfolioAction.BOOK_PARTIAL_50: [],
            PortfolioAction.BOOK_ALL: [],
            PortfolioAction.STOP_LOSS_HIT: [],
            PortfolioAction.TRAILING_STOP: [],
        }
        
        for analysis in analyses:
            action = analysis.get("action", PortfolioAction.HOLD)
            ticker = analysis.get("ticker", "Unknown")
            if action in categories:
                categories[action].append(ticker)
        
        return categories
    
    def _generate_portfolio_insights(
        self,
        analyses: List[Dict],
        total_value: float,
        total_pnl_percent: float,
        actions_summary: Dict,
    ) -> Dict[str, Any]:
        """Generate portfolio-level insights."""
        
        # Count by priority
        urgent = sum(1 for a in analyses if a.get("priority") == "URGENT")
        high = sum(1 for a in analyses if a.get("priority") == "HIGH")
        
        # Best and worst performers
        sorted_by_pnl = sorted(
            [a for a in analyses if a.get("pnl_percent") is not None],
            key=lambda x: x.get("pnl_percent", 0),
            reverse=True
        )
        
        best_performers = sorted_by_pnl[:3] if len(sorted_by_pnl) >= 3 else sorted_by_pnl
        worst_performers = sorted_by_pnl[-3:] if len(sorted_by_pnl) >= 3 else sorted_by_pnl
        
        # Overall health
        if total_pnl_percent >= 15:
            health = "EXCELLENT"
            health_emoji = "🟢"
        elif total_pnl_percent >= 5:
            health = "GOOD"
            health_emoji = "🟢"
        elif total_pnl_percent >= -5:
            health = "NEUTRAL"
            health_emoji = "🟡"
        elif total_pnl_percent >= -15:
            health = "CONCERNING"
            health_emoji = "🟠"
        else:
            health = "POOR"
            health_emoji = "🔴"
        
        return {
            "overall_health": health,
            "health_emoji": health_emoji,
            "urgent_actions": urgent,
            "high_priority_actions": high,
            "best_performers": [
                {"ticker": p["ticker"], "pnl_percent": p["pnl_percent"]}
                for p in best_performers
            ],
            "worst_performers": [
                {"ticker": p["ticker"], "pnl_percent": p["pnl_percent"]}
                for p in worst_performers
            ],
            "action_required_count": len(actions_summary.get(PortfolioAction.BOOK_ALL, [])) + 
                                    len(actions_summary.get(PortfolioAction.STOP_LOSS_HIT, [])) +
                                    len(actions_summary.get(PortfolioAction.BOOK_PARTIAL_50, [])),
        }
