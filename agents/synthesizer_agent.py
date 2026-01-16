"""Synthesizer Agent - combines all analyses into final recommendation."""

from typing import Any, Dict, Type
from pydantic import BaseModel
from loguru import logger

from .base_agent import BaseAgent
from .schemas import SynthesizedRecommendation, Confidence


class SynthesizerAgent(BaseAgent):
    """Agent that synthesizes all analyses into a final recommendation."""
    
    def __init__(self):
        super().__init__("Synthesizer")
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert investment strategist synthesizing multiple analyses for Indian equities (NSE/BSE).
Your role is to combine fundamental, technical, sentiment, and risk analyses into a coherent recommendation.

Weighting Guidelines:
- Long-term Investment: Fundamental 50%, Technical 20%, Sentiment 20%, Risk 10%
- Short-term Trading: Fundamental 15%, Technical 50%, Sentiment 25%, Risk 10%
- Swing Trading (2-4 weeks): Fundamental 30%, Technical 40%, Sentiment 20%, Risk 10%

Conflict Resolution:
- If fundamental = Strong BUY but technical = SELL: Recommend HOLD/WAIT ("Good company, wrong time")
- If fundamental = SELL but technical = BUY: Recommend AVOID ("Technical bounce in weak stock")
- If sentiment = Negative but fundamentals + technicals = Positive: Reduce confidence by 20%

Recommendations:
- BUY: Score >= 70, all agents reasonably aligned
- HOLD: Score 55-69, or mixed signals
- WAIT: Score 40-54, or significant conflicts
- AVOID: Score < 40, or major red flags

Confidence Levels:
- HIGH: All agents agree, no red flags (80-100%)
- MEDIUM: Minor conflicts or concerns (60-79%)
- LOW: Major conflicts or data issues (0-59%)

IMPORTANT:
- Always provide specific entry zones, targets, and stop losses
- Include position sizing recommendations
- Be clear about what could go wrong
- Mention monitoring triggers
- Never guarantee returns"""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return SynthesizedRecommendation
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize all analyses into final recommendation.
        
        Args:
            data: Dict containing all analysis results
            
        Returns:
            SynthesizedRecommendation as dictionary
        """
        logger.info(f"Synthesizing recommendation for {data.get('ticker', 'unknown')}")
        
        stock_data = data.get('stock_data', {})
        fundamental = data.get('fundamental_analysis', {})
        technical = data.get('technical_analysis', {})
        market_intel = data.get('market_intel_analysis', {})
        risk = data.get('risk_analysis', {})
        user_context = data.get('user_context', {})
        
        # Pre-calculate weighted scores
        scores = self._calculate_weighted_scores(
            fundamental,
            technical,
            market_intel,
            risk,
            user_context,
        )
        
        # Build prompt
        prompt = self._build_analysis_prompt(
            stock_data,
            fundamental,
            technical,
            market_intel,
            risk,
            user_context,
            scores,
        )
        
        # Run LLM analysis
        result = await self._run_llm_analysis(prompt)
        
        return result
    
    def _calculate_weighted_scores(
        self,
        fundamental: Dict[str, Any],
        technical: Dict[str, Any],
        market_intel: Dict[str, Any],
        risk: Dict[str, Any],
        user_context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Calculate weighted scores based on investment horizon."""
        
        time_horizon = user_context.get('time_horizon', 'medium')
        
        # Determine weights based on time horizon
        if 'long' in time_horizon.lower():
            weights = {'fundamental': 0.50, 'technical': 0.20, 'market_intel': 0.20, 'risk': 0.10}
        elif 'short' in time_horizon.lower():
            weights = {'fundamental': 0.15, 'technical': 0.50, 'market_intel': 0.25, 'risk': 0.10}
        else:  # Medium-term / swing
            weights = {'fundamental': 0.30, 'technical': 0.40, 'market_intel': 0.20, 'risk': 0.10}
        
        # Get scores (default to 50 if not available)
        fund_score = fundamental.get('score', 50)
        tech_score = technical.get('score', 50)
        intel_score = market_intel.get('score', 50)
        risk_score = 100 - risk.get('risk_score', 50)  # Invert risk score
        
        # Calculate weighted average
        weighted = (
            fund_score * weights['fundamental'] +
            tech_score * weights['technical'] +
            intel_score * weights['market_intel'] +
            risk_score * weights['risk']
        )
        
        # Check for conflicts
        signals = [
            self._normalize_signal(fundamental.get('rating', 'HOLD')),
            self._normalize_signal(technical.get('signal', 'NEUTRAL')),
            self._normalize_signal(market_intel.get('overall_sentiment', 'NEUTRAL')),
        ]
        
        conflicts = self._detect_conflicts(signals)
        
        # Adjust for conflicts
        confidence_adjustment = 0
        if not conflicts:
            confidence_adjustment = 10  # All aligned
        elif len(conflicts) >= 2:
            confidence_adjustment = -20  # Major conflict
        
        return {
            'fundamental_score': fund_score,
            'technical_score': tech_score,
            'market_intel_score': intel_score,
            'risk_score': risk.get('risk_score', 50),
            'weighted_average': round(weighted, 2),
            'confidence_adjustment': confidence_adjustment,
            'final_score': round(weighted + confidence_adjustment, 2),
            'weights_used': weights,
            'conflicts': conflicts,
        }
    
    def _normalize_signal(self, signal: str) -> str:
        """Normalize signal to bullish/bearish/neutral."""
        signal = signal.upper()
        
        bullish = ['STRONG_BUY', 'BUY', 'BULLISH', 'POSITIVE', 'UNDERVALUED']
        bearish = ['STRONG_SELL', 'SELL', 'BEARISH', 'NEGATIVE', 'OVERVALUED']
        
        if any(s in signal for s in bullish):
            return 'BULLISH'
        elif any(s in signal for s in bearish):
            return 'BEARISH'
        return 'NEUTRAL'
    
    def _detect_conflicts(self, signals: list[str]) -> list[str]:
        """Detect conflicts between agent signals."""
        conflicts = []
        
        bullish_count = signals.count('BULLISH')
        bearish_count = signals.count('BEARISH')
        
        if bullish_count > 0 and bearish_count > 0:
            conflicts.append(f"Mixed signals: {bullish_count} bullish, {bearish_count} bearish")
        
        return conflicts
    
    def _build_analysis_prompt(
        self,
        stock_data: Dict[str, Any],
        fundamental: Dict[str, Any],
        technical: Dict[str, Any],
        market_intel: Dict[str, Any],
        risk: Dict[str, Any],
        user_context: Dict[str, Any],
        scores: Dict[str, Any],
    ) -> str:
        """Build the synthesis prompt."""
        
        ticker = stock_data.get('ticker', 'Unknown')
        name = stock_data.get('name', ticker)
        price_data = stock_data.get('price_data', {})
        
        prompt = f"""Synthesize a final recommendation for {name} ({ticker}).

=== CURRENT PRICE ===
Price: ₹{price_data.get('current_price', 'N/A')}
Change: {price_data.get('change_percent', 0):+.2f}%

=== FUNDAMENTAL ANALYSIS ===
Score: {fundamental.get('score', 'N/A')}/100
Rating: {fundamental.get('rating', 'N/A')}
Recommendation: {fundamental.get('recommendation', 'N/A')}
Fair Value: ₹{fundamental.get('valuation', {}).get('fair_value', 'N/A')}
Key Strengths: {', '.join(fundamental.get('strengths', [])[:3])}
Key Concerns: {', '.join(fundamental.get('concerns', [])[:3])}

=== TECHNICAL ANALYSIS ===
Score: {technical.get('score', 'N/A')}/100
Signal: {technical.get('signal', 'N/A')}
Confidence: {technical.get('confidence', 'N/A')}
Trend: {technical.get('trend_analysis', {}).get('overall_trend', 'N/A')}
Entry Zone: {technical.get('trading_setup', {}).get('entry_zone', 'N/A')}
Target 1: ₹{technical.get('trading_setup', {}).get('target_1', 'N/A')}
Target 2: ₹{technical.get('trading_setup', {}).get('target_2', 'N/A')}
Stop Loss: ₹{technical.get('trading_setup', {}).get('stop_loss', 'N/A')}
Risk-Reward: {technical.get('trading_setup', {}).get('risk_reward_ratio', 'N/A')}

=== MARKET INTELLIGENCE ===
Score: {market_intel.get('score', 'N/A')}/100
Sentiment: {market_intel.get('overall_sentiment', 'N/A')}
Trend: {market_intel.get('sentiment_trend', 'N/A')}
Catalysts: {', '.join([c.get('event', '') for c in market_intel.get('catalysts', [])[:3]])}
Concerns: {', '.join(market_intel.get('concerns', [])[:2])}
Opportunities: {', '.join(market_intel.get('opportunities', [])[:2])}

=== RISK ANALYSIS ===
Risk Score: {risk.get('risk_score', 'N/A')}/100
Risk Rating: {risk.get('risk_rating', 'N/A')}
Beta: {risk.get('stock_risk_metrics', {}).get('beta', 'N/A')}
Volatility: {risk.get('stock_risk_metrics', {}).get('volatility_30d', 'N/A')}%
Recommended Position: {risk.get('position_sizing', {}).get('recommended', {}).get('percentage', 'N/A')} of portfolio
Key Risks: {', '.join([r.get('factor', '') for r in risk.get('risk_factors', [])[:3]])}

=== WEIGHTED ANALYSIS ===
Fundamental Score: {scores.get('fundamental_score', 'N/A')}/100 (weight: {scores.get('weights_used', {}).get('fundamental', 0)*100:.0f}%)
Technical Score: {scores.get('technical_score', 'N/A')}/100 (weight: {scores.get('weights_used', {}).get('technical', 0)*100:.0f}%)
Market Intel Score: {scores.get('market_intel_score', 'N/A')}/100 (weight: {scores.get('weights_used', {}).get('market_intel', 0)*100:.0f}%)
Risk Score (inverted): {100 - scores.get('risk_score', 50)}/100 (weight: {scores.get('weights_used', {}).get('risk', 0)*100:.0f}%)
Weighted Average: {scores.get('weighted_average', 'N/A')}/100
Conflicts: {scores.get('conflicts', [])}
Confidence Adjustment: {scores.get('confidence_adjustment', 0):+d}
Final Score: {scores.get('final_score', 'N/A')}/100

=== USER CONTEXT ===
Risk Appetite: {user_context.get('risk_appetite', 'Moderate')}
Investment Horizon: {user_context.get('time_horizon', 'Medium-term')}
Portfolio Value: ₹{user_context.get('portfolio_value', 1000000):,}

Based on ALL the above analyses, provide:
1. Final recommendation (BUY, HOLD, WAIT, AVOID)
2. Confidence level (0-100) and category (HIGH, MEDIUM, LOW)
3. Detailed action plan:
   - Entry strategy (tranches if applicable)
   - Specific price targets with timeframes
   - Stop loss level
   - Position sizing
4. Reasoning:
   - Why this recommendation
   - Key concerns
   - What could go wrong
   - Why the confidence level
5. Agent consensus summary
6. Monitoring triggers
7. User suitability assessment

Be specific, actionable, and realistic. Never guarantee returns."""

        return prompt
    
    def _get_fallback_response(self, error: str) -> Dict[str, Any]:
        """Get fallback response when synthesis fails."""
        return {
            "recommendation": "HOLD",
            "confidence": 50,
            "confidence_level": "LOW",
            "action_plan": {
                "primary_action": "HOLD",
                "entry_strategy": "Wait for better clarity",
                "targets": [],
                "stop_loss": None,
                "position_size": {},
                "holding_period": "N/A",
                "investment_type": "N/A",
            },
            "reasoning": {
                "why_buy": [],
                "key_concerns": [f"Analysis incomplete: {error}"],
                "what_could_go_wrong": ["Insufficient data for recommendation"],
                "why_confidence": ["Low confidence due to analysis errors"],
            },
            "score_breakdown": {
                "fundamental_score": 50,
                "technical_score": 50,
                "market_intel_score": 50,
                "risk_score": 50,
                "weighted_average": 50,
                "final_confidence": 50,
            },
            "agent_consensus": {
                "message": "Analysis incomplete",
            },
            "monitoring_plan": {
                "review_triggers": [],
                "weekly_checks": [],
            },
            "user_suitability": {
                "note": "Cannot assess due to incomplete analysis",
            },
        }


class ComparisonSynthesizerAgent(SynthesizerAgent):
    """Special synthesizer for comparing two stocks."""
    
    async def compare(
        self,
        stock1_data: Dict[str, Any],
        stock2_data: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Compare two stocks and provide recommendation."""
        
        logger.info(f"Comparing {stock1_data.get('ticker')} vs {stock2_data.get('ticker')}")
        
        prompt = self._build_comparison_prompt(stock1_data, stock2_data)
        
        # For comparison, we use simple text generation
        result = await self.llm.generate_simple(
            prompt=prompt,
            system_prompt=self._get_comparison_system_prompt(),
        )
        
        return {"comparison_analysis": result}
    
    def _get_comparison_system_prompt(self) -> str:
        return """You are an expert investment analyst comparing two Indian stocks.
Provide a clear, concise comparison covering:
1. Head-to-head metrics comparison
2. Relative strengths and weaknesses
3. Which stock is better for different investor profiles
4. Clear recommendation on which to prefer and why

Be objective and data-driven."""
    
    def _build_comparison_prompt(
        self,
        stock1: Dict[str, Any],
        stock2: Dict[str, Any],
    ) -> str:
        """Build comparison prompt."""
        
        s1 = stock1.get('stock_data', {})
        s2 = stock2.get('stock_data', {})
        
        f1 = stock1.get('fundamental_analysis', {})
        f2 = stock2.get('fundamental_analysis', {})
        
        t1 = stock1.get('technical_analysis', {})
        t2 = stock2.get('technical_analysis', {})
        
        return f"""Compare these two stocks:

=== STOCK 1: {s1.get('name', s1.get('ticker', 'Stock 1'))} ===
Price: ₹{s1.get('price_data', {}).get('current_price', 'N/A')}
Fundamental Score: {f1.get('score', 'N/A')}/100
Technical Score: {t1.get('score', 'N/A')}/100
Rating: {f1.get('rating', 'N/A')}
P/E: {s1.get('fundamental_data', {}).get('pe_ratio', 'N/A')}
ROE: {s1.get('fundamental_data', {}).get('roe', 'N/A')}%

=== STOCK 2: {s2.get('name', s2.get('ticker', 'Stock 2'))} ===
Price: ₹{s2.get('price_data', {}).get('current_price', 'N/A')}
Fundamental Score: {f2.get('score', 'N/A')}/100
Technical Score: {t2.get('score', 'N/A')}/100
Rating: {f2.get('rating', 'N/A')}
P/E: {s2.get('fundamental_data', {}).get('pe_ratio', 'N/A')}
ROE: {s2.get('fundamental_data', {}).get('roe', 'N/A')}%

Provide a comprehensive comparison and clear recommendation."""
