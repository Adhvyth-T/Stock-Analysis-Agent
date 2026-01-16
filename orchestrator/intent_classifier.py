"""Intent classifier for determining user query type."""

import re
from enum import Enum
from typing import Optional, List, Tuple
from pydantic import BaseModel, Field

from utils.validators import extract_tickers_from_text, validate_ticker


class IntentType(str, Enum):
    """Types of user intents."""
    PRICE_CHECK = "price_check"
    TECHNICAL_ANALYSIS = "technical_analysis"
    FUNDAMENTAL_ANALYSIS = "fundamental_analysis"
    SENTIMENT_ANALYSIS = "sentiment_analysis"
    FULL_ANALYSIS = "full_analysis"
    COMPARISON = "comparison"
    DEEP_DIVE = "deep_dive"
    HELP = "help"
    UNKNOWN = "unknown"


class Intent(BaseModel):
    """Parsed user intent."""
    type: IntentType = Field(description="Type of intent detected")
    tickers: List[str] = Field(default_factory=list, description="Stock tickers mentioned")
    raw_query: str = Field(description="Original user query")
    confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Confidence in intent detection")
    aspect: Optional[str] = Field(default=None, description="Specific aspect for single-aspect queries")


class IntentClassifier:
    """Classifies user queries into intents using pattern matching."""
    
    # Pattern definitions for each intent type
    PATTERNS = {
        IntentType.PRICE_CHECK: [
            r"^/p\s+",
            r"\bprice\s+of\b",
            r"\bcurrent\s+price\b",
            r"\bquote\b",
            r"\bltp\b",
            r"\blast\s+traded\s+price\b",
            r"\bhow\s+much\s+is\b",
            r"\bwhat\s+is\s+.*\s+trading\s+at\b",
        ],
        IntentType.TECHNICAL_ANALYSIS: [
            r"^/t\s+",
            r"\btechnical\s+analysis\b",
            r"\btechnicals?\b",
            r"\bchart\s+analysis\b",
            r"\brsi\b",
            r"\bmacd\b",
            r"\bsupport\s+and\s+resistance\b",
            r"\bsupport\b.*\bresistance\b",
            r"\bmoving\s+average\b",
            r"\btrend\b",
            r"\bbollinger\b",
            r"\bbreakout\b",
            r"\bentry\s+point\b",
        ],
        IntentType.FUNDAMENTAL_ANALYSIS: [
            r"^/f\s+",
            r"\bfundamental\s+analysis\b",
            r"\bfundamentals?\b",
            r"\bfinancials?\b",
            r"\bpe\s+ratio\b",
            r"\bpb\s+ratio\b",
            r"\bearnings\b",
            r"\brevenue\b",
            r"\bprofit\b",
            r"\bbalance\s+sheet\b",
            r"\bvaluation\b",
            r"\broe\b",
            r"\broce\b",
            r"\bdebt\b",
        ],
        IntentType.SENTIMENT_ANALYSIS: [
            r"^/n\s+",
            r"\bnews\b",
            r"\bsentiment\b",
            r"\bwhat\s+.*\s+saying\b",
            r"\bmarket\s+mood\b",
            r"\banalyst\s+rating\b",
            r"\bfii\b",
            r"\bdii\b",
        ],
        IntentType.FULL_ANALYSIS: [
            r"^/a\s+",
            r"\bshould\s+i\s+buy\b",
            r"\bshould\s+i\s+sell\b",
            r"\bbuy\s+or\s+sell\b",
            r"\banalyze\b",
            r"\banalysis\b",
            r"\binvestment\s+view\b",
            r"\brecommendation\b",
            r"\bwhat\s+do\s+you\s+think\b",
            r"\bgood\s+to\s+buy\b",
            r"\bworth\s+buying\b",
        ],
        IntentType.COMPARISON: [
            r"^/c\s+",
            r"\bcompare\b",
            r"\bvs\.?\b",
            r"\bversus\b",
            r"\bwhich\s+is\s+better\b",
            r"\bor\b.*\bwhich\b",
            r"\bbetter\b.*\bor\b",
        ],
        IntentType.DEEP_DIVE: [
            r"^/dd\s+",
            r"\bdeep\s*dive\b",
            r"\bdetailed\s+analysis\b",
            r"\bfull\s+report\b",
            r"\bcomprehensive\b",
            r"\bin\s*depth\b",
        ],
        IntentType.HELP: [
            r"^/help\b",
            r"^/start\b",
            r"\bhelp\b",
            r"\bhow\s+to\s+use\b",
            r"\bwhat\s+can\s+you\s+do\b",
            r"\bcommands?\b",
        ],
    }
    
    # Command shortcuts
    COMMAND_SHORTCUTS = {
        "/p": IntentType.PRICE_CHECK,
        "/t": IntentType.TECHNICAL_ANALYSIS,
        "/f": IntentType.FUNDAMENTAL_ANALYSIS,
        "/n": IntentType.SENTIMENT_ANALYSIS,
        "/a": IntentType.FULL_ANALYSIS,
        "/c": IntentType.COMPARISON,
        "/dd": IntentType.DEEP_DIVE,
        "/help": IntentType.HELP,
        "/start": IntentType.HELP,
    }
    
    def __init__(self):
        """Initialize classifier with compiled patterns."""
        self.compiled_patterns = {
            intent: [re.compile(p, re.IGNORECASE) for p in patterns]
            for intent, patterns in self.PATTERNS.items()
        }
    
    def classify(self, query: str) -> Intent:
        """
        Classify user query into an intent.
        
        Args:
            query: User's message
            
        Returns:
            Intent object with type, tickers, and confidence
        """
        query = query.strip()
        
        # Check for command shortcuts first
        intent_type, confidence = self._check_command(query)
        
        if intent_type == IntentType.UNKNOWN:
            # Try pattern matching
            intent_type, confidence = self._match_patterns(query)
        
        # Extract tickers
        tickers = self._extract_tickers(query)
        
        # Determine aspect for single-aspect queries
        aspect = self._determine_aspect(intent_type)
        
        # If we found a ticker but no clear intent, default to full analysis
        if intent_type == IntentType.UNKNOWN and tickers:
            intent_type = IntentType.FULL_ANALYSIS
            confidence = 0.6
        
        return Intent(
            type=intent_type,
            tickers=tickers,
            raw_query=query,
            confidence=confidence,
            aspect=aspect,
        )
    
    def _check_command(self, query: str) -> Tuple[IntentType, float]:
        """Check if query starts with a command shortcut."""
        query_lower = query.lower()
        for cmd, intent in self.COMMAND_SHORTCUTS.items():
            if query_lower.startswith(cmd):
                return intent, 1.0
        return IntentType.UNKNOWN, 0.0
    
    def _match_patterns(self, query: str) -> Tuple[IntentType, float]:
        """Match query against intent patterns."""
        matches = []
        
        for intent, patterns in self.compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(query):
                    matches.append(intent)
                    break
        
        if not matches:
            return IntentType.UNKNOWN, 0.0
        
        # If multiple intents match, prioritize
        priority_order = [
            IntentType.DEEP_DIVE,
            IntentType.COMPARISON,
            IntentType.FULL_ANALYSIS,
            IntentType.TECHNICAL_ANALYSIS,
            IntentType.FUNDAMENTAL_ANALYSIS,
            IntentType.SENTIMENT_ANALYSIS,
            IntentType.PRICE_CHECK,
            IntentType.HELP,
        ]
        
        for priority_intent in priority_order:
            if priority_intent in matches:
                confidence = 0.9 if len(matches) == 1 else 0.7
                return priority_intent, confidence
        
        return matches[0], 0.7
    
    def _extract_tickers(self, query: str) -> List[str]:
        """Extract stock tickers from query."""
        tickers = []
        
        # Check for command format: /p RELIANCE
        parts = query.split()
        for part in parts[1:] if parts else []:  # Skip command
            cleaned = part.upper().strip(",.!?")
            if validate_ticker(cleaned):
                tickers.append(cleaned)
        
        # Also try general extraction
        extracted = extract_tickers_from_text(query)
        for ticker in extracted:
            if ticker not in tickers:
                tickers.append(ticker)
        
        return tickers[:2]  # Max 2 for comparison
    
    def _determine_aspect(self, intent_type: IntentType) -> Optional[str]:
        """Determine the specific aspect for single-aspect queries."""
        aspect_map = {
            IntentType.TECHNICAL_ANALYSIS: "technical",
            IntentType.FUNDAMENTAL_ANALYSIS: "fundamental",
            IntentType.SENTIMENT_ANALYSIS: "sentiment",
        }
        return aspect_map.get(intent_type)
    
    def get_help_text(self) -> str:
        """Return help text for available commands with proper HTML escaping."""
        return """🤖 <b>Stock Analysis Bot Commands</b>

<b>Quick Commands:</b>
• <code>/p TICKER</code> - Quick price check
• <code>/a TICKER</code> - Full analysis with recommendation
• <code>/t TICKER</code> - Technical analysis only
• <code>/f TICKER</code> - Fundamental analysis only
• <code>/n TICKER</code> - News &amp; sentiment analysis
• <code>/c TICKER1 TICKER2</code> - Compare two stocks
• <code>/dd TICKER</code> - Deep dive (comprehensive report)
• <code>/portfolio</code> - list of portfolio commands

<b>Examples:</b>
• <code>/p RELIANCE</code> - Get current price
• <code>/a TCS</code> - Full analysis of TCS
• <code>/c INFY TCS</code> - Compare Infosys vs TCS
• Type naturally: "Should I buy HDFC?"

<b>Tips:</b>
• Use NSE tickers (RELIANCE, TCS, INFY)
• Add .NS suffix for clarity (RELIANCE.NS)
• For BSE, use .BO suffix (TATASTEEL.BO)

<i>Disclaimer: This bot provides analysis, not financial advice. Always do your own research.</i>"""