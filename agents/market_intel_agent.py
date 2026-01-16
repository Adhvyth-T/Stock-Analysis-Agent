"""Market Intelligence Agent for sentiment and context analysis."""

from typing import Any, Dict, Type, List
from pydantic import BaseModel
from loguru import logger
from datetime import datetime

from .base_agent import BaseAgent
from .schemas import MarketIntelAnalysis


class MarketIntelAgent(BaseAgent):
    """Agent for market intelligence and sentiment analysis."""
    
    def __init__(self):
        super().__init__("Market Intelligence")
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert market intelligence analyst specializing in Indian equities (NSE/BSE).
Your role is to understand external context and sentiment around a stock.

Focus on:
1. News sentiment analysis
2. Social media discussions and sentiment
3. Analyst ratings and consensus
4. Market regime (bull/bear/volatile)
5. Sector performance and trends
6. FII/DII activity
7. Upcoming catalysts and events
8. Regulatory changes

DO NOT analyze:
- Company financial statements
- Technical charts or indicators
- Specific valuation metrics

Sentiment scoring (-100 to +100):
- +70 to +100: Very positive sentiment
- +30 to +69: Positive sentiment
- -29 to +29: Neutral sentiment
- -69 to -30: Negative sentiment
- -100 to -70: Very negative sentiment

Be objective. Distinguish between short-term noise and meaningful signals."""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return MarketIntelAnalysis
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform market intelligence analysis.
        
        Args:
            data: Dict containing stock_data, news_data, and market_data
            
        Returns:
            MarketIntelAnalysis as dictionary
        """
        logger.info(f"Running market intelligence for {data.get('ticker', 'unknown')}")
        
        stock_data = data.get('stock_data', {})
        news_data = data.get('news_data', {})
        market_data = data.get('market_data', {})
        
        # Build prompt
        prompt = self._build_analysis_prompt(stock_data, news_data, market_data)
        
        # Run LLM analysis
        result = await self._run_llm_analysis(prompt)
        
        return result
    
    def _build_analysis_prompt(
        self,
        stock_data: Dict[str, Any],
        news_data: Dict[str, Any],
        market_data: Dict[str, Any],
    ) -> str:
        """Build the analysis prompt."""
        
        ticker = stock_data.get('ticker', 'Unknown')
        name = stock_data.get('name', ticker)
        
        # Format news
        news_section = self._format_news(news_data)
        
        # Format market context
        market_section = self._format_market_context(market_data)
        
        # Format stock info
        fund_data = stock_data.get('fundamental_data', {})
        ownership = stock_data.get('ownership_data', {})
        
        prompt = f"""Analyze market intelligence and sentiment for {name} ({ticker}).

=== COMPANY CONTEXT ===
Sector: {fund_data.get('sector', 'N/A')}
Industry: {fund_data.get('industry', 'N/A')}
Promoter Holding: {ownership.get('promoter_holding', 'N/A')}%
FII Holding: {ownership.get('fii_holding', 'N/A')}%
DII Holding: {ownership.get('dii_holding', 'N/A')}%

=== RECENT NEWS ===
{news_section}

=== MARKET CONTEXT ===
{market_section}

Based on this information, provide:
1. Overall sentiment score (0-100, where 50 is neutral, >50 is positive, <50 is negative)
2. Overall sentiment (POSITIVE, NEGATIVE, NEUTRAL)
3. Sentiment trend (Improving, Stable, Declining)
4. News analysis summary
5. Market context assessment
6. Upcoming catalysts
7. Key concerns (list 2-4)
8. Key opportunities (list 2-4)

Focus only on sentiment and external factors. Ignore technical and fundamental analysis."""

        return prompt
    
    def _format_news(self, news_data: Dict[str, Any]) -> str:
        """Format news data for prompt."""
        if not news_data:
            return "No recent news available."
        
        articles = news_data.get('articles', [])
        
        if not articles:
            return "No recent news available."
        
        lines = [
            f"Total Articles (7 days): {news_data.get('total_count', len(articles))}",
            f"Positive: {news_data.get('positive_count', 0)}",
            f"Negative: {news_data.get('negative_count', 0)}",
            f"Neutral: {news_data.get('neutral_count', 0)}",
            f"Overall Sentiment: {news_data.get('overall_sentiment', 'Unknown')}",
            "",
            "Recent Headlines:"
        ]
        
        for article in articles[:10]:
            sentiment = article.get('sentiment', 'neutral')
            source = article.get('source', 'Unknown')
            title = article.get('title', 'No title')
            date = article.get('published_at', '')
            
            if isinstance(date, datetime):
                date = date.strftime('%Y-%m-%d')
            elif hasattr(date, 'isoformat'):
                date = date.isoformat()[:10]
            
            lines.append(f"  [{sentiment.upper()}] {source} ({date}): {title[:100]}")
        
        return "\n".join(lines)
    
    def _format_market_context(self, market_data: Dict[str, Any]) -> str:
        """Format market context for prompt."""
        if not market_data:
            return "Market data not available."
        
        lines = [
            f"NIFTY 50: {market_data.get('nifty_50', 'N/A')} ({market_data.get('nifty_change_percent', 0):+.2f}%)",
            f"SENSEX: {market_data.get('sensex', 'N/A')} ({market_data.get('sensex_change_percent', 0):+.2f}%)",
            f"India VIX: {market_data.get('india_vix', 'N/A')}",
            f"Market Status: {market_data.get('market_status', 'Unknown')}",
        ]
        
        if market_data.get('fii_net_buy') is not None:
            lines.append(f"FII Net: ₹{market_data.get('fii_net_buy'):,.0f} Cr")
        if market_data.get('dii_net_buy') is not None:
            lines.append(f"DII Net: ₹{market_data.get('dii_net_buy'):,.0f} Cr")
        
        return "\n".join(lines)
    
    def _get_fallback_response(self, error: str) -> Dict[str, Any]:
        """Get fallback response when analysis fails."""
        return {
            "score": 50,
            "overall_sentiment": "NEUTRAL",
            "sentiment_trend": "Stable",
            "news_analysis": {
                "score": 50,
                "sentiment": "Neutral",
                "article_count_7d": 0,
                "positive_count": 0,
                "neutral_count": 0,
                "negative_count": 0,
                "key_headlines": [],
                "summary": f"Analysis incomplete: {error}",
            },
            "market_context": {
                "market_regime": "Unknown",
                "nifty_trend": "Unknown",
                "sector_performance": {},
            },
            "catalysts": [],
            "concerns": [f"Analysis error: {error}"],
            "opportunities": [],
        }
