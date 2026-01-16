"""Routing module for execution path selection."""

from typing import Dict, Any, Optional
from enum import Enum
from pydantic import BaseModel

from orchestrator.intent_classifier import Intent, IntentType


class ExecutionPath(str, Enum):
    """Execution paths with different complexity levels."""
    FAST = "fast"  # Price check only
    SINGLE = "single"  # Single agent analysis
    STANDARD = "standard"  # Full analysis
    COMPARISON = "comparison"  # Compare two stocks
    DEEP_DIVE = "deep_dive"  # Comprehensive analysis


class RouteInfo(BaseModel):
    """Information about selected route."""
    path: ExecutionPath
    agents_used: int
    expected_time_seconds: tuple[int, int]  # (min, max)
    description: str


class Router:
    """Routes intents to appropriate execution paths."""
    
    ROUTE_CONFIG: Dict[IntentType, RouteInfo] = {
        IntentType.PRICE_CHECK: RouteInfo(
            path=ExecutionPath.FAST,
            agents_used=0,
            expected_time_seconds=(1, 3),
            description="Quick price check",
        ),
        IntentType.TECHNICAL_ANALYSIS: RouteInfo(
            path=ExecutionPath.SINGLE,
            agents_used=1,
            expected_time_seconds=(5, 10),
            description="Technical analysis only",
        ),
        IntentType.FUNDAMENTAL_ANALYSIS: RouteInfo(
            path=ExecutionPath.SINGLE,
            agents_used=1,
            expected_time_seconds=(5, 10),
            description="Fundamental analysis only",
        ),
        IntentType.SENTIMENT_ANALYSIS: RouteInfo(
            path=ExecutionPath.SINGLE,
            agents_used=1,
            expected_time_seconds=(5, 10),
            description="News & sentiment analysis",
        ),
        IntentType.FULL_ANALYSIS: RouteInfo(
            path=ExecutionPath.STANDARD,
            agents_used=5,
            expected_time_seconds=(15, 25),
            description="Complete stock analysis",
        ),
        IntentType.COMPARISON: RouteInfo(
            path=ExecutionPath.COMPARISON,
            agents_used=3,
            expected_time_seconds=(18, 30),
            description="Compare two stocks",
        ),
        IntentType.DEEP_DIVE: RouteInfo(
            path=ExecutionPath.DEEP_DIVE,
            agents_used=5,
            expected_time_seconds=(25, 45),
            description="Comprehensive deep dive",
        ),
    }
    
    @classmethod
    def get_route(cls, intent: Intent) -> RouteInfo:
        """
        Get routing information for an intent.
        
        Args:
            intent: Classified user intent
            
        Returns:
            RouteInfo with path details
        """
        return cls.ROUTE_CONFIG.get(
            intent.type,
            RouteInfo(
                path=ExecutionPath.STANDARD,
                agents_used=5,
                expected_time_seconds=(15, 25),
                description="Standard analysis",
            )
        )
    
    @classmethod
    def get_progress_message(cls, intent: Intent) -> str:
        """Get initial progress message based on route."""
        route = cls.get_route(intent)
        ticker = intent.tickers[0] if intent.tickers else "stock"
        
        messages = {
            ExecutionPath.FAST: f"⚡ Fetching price for {ticker}...",
            ExecutionPath.SINGLE: f"⏳ Analyzing {ticker}...",
            ExecutionPath.STANDARD: f"⏳ Running full analysis on {ticker}...\nExpected time: {route.expected_time_seconds[0]}-{route.expected_time_seconds[1]}s",
            ExecutionPath.COMPARISON: f"⏳ Comparing {intent.tickers[0]} vs {intent.tickers[1] if len(intent.tickers) > 1 else '?'}...",
            ExecutionPath.DEEP_DIVE: f"🔍 Starting deep dive on {ticker}...\nThis may take up to 45 seconds.",
        }
        
        return messages.get(route.path, f"⏳ Analyzing {ticker}...")
    
    @classmethod
    def should_show_progress(cls, intent: Intent) -> bool:
        """Check if progress updates should be shown."""
        route = cls.get_route(intent)
        # Show progress for analyses that take more than 5 seconds
        return route.expected_time_seconds[0] >= 5
    
    @classmethod
    def validate_intent(cls, intent: Intent) -> tuple[bool, Optional[str]]:
        """
        Validate intent before routing.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if intent.type == IntentType.UNKNOWN:
            return False, "I couldn't understand your request. Try `/help` for available commands."
        
        if intent.type == IntentType.HELP:
            return True, None
        
        if not intent.tickers:
            return False, "Please specify a stock ticker. Example: `/a RELIANCE`"
        
        if intent.type == IntentType.COMPARISON and len(intent.tickers) < 2:
            return False, "Please specify two tickers for comparison. Example: `/c TCS INFY`"
        
        return True, None
