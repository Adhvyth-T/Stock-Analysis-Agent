"""Risk Analysis Agent."""

from typing import Any, Dict, Type, List
from pydantic import BaseModel
from loguru import logger
import numpy as np

from .base_agent import BaseAgent
from .schemas import RiskAnalysis, RiskLevel
from utils.math_tools import (
    calculate_beta,
    calculate_volatility,
    calculate_sharpe_ratio,
    calculate_max_drawdown,
    calculate_position_size,
)


class RiskAgent(BaseAgent):
    """Agent for risk assessment and position sizing."""
    
    def __init__(self):
        super().__init__("Risk Calculator")
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert risk analyst specializing in Indian equities (NSE/BSE).
Your role is to quantify risks and recommend position sizing.

Focus on:
1. Stock-specific risk metrics (beta, volatility)
2. Maximum drawdown analysis
3. Liquidity assessment
4. Position sizing recommendations
5. Scenario analysis
6. Risk factors identification
7. Risk mitigation strategies

DO NOT:
- Make buy/sell recommendations
- Analyze fundamentals or technicals in detail
- Explain why risks exist (other agents do this)

Risk scoring (0-100, higher = riskier):
- 0-25: Low risk
- 26-50: Moderate risk
- 51-75: High risk
- 76-100: Very high risk

Position sizing should consider:
- Conservative: 2-3% of portfolio
- Moderate: 3-5% of portfolio
- Aggressive: 5-8% of portfolio

Always be conservative with risk estimates."""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return RiskAnalysis
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform risk analysis.
        
        Args:
            data: Dict containing stock_data, fundamental_analysis, technical_analysis
            
        Returns:
            RiskAnalysis as dictionary
        """
        logger.info(f"Running risk analysis for {data.get('ticker', 'unknown')}")
        
        stock_data = data.get('stock_data', {})
        fundamental = data.get('fundamental_analysis', {})
        technical = data.get('technical_analysis', {})
        user_context = data.get('user_context', {})
        
        # Calculate risk metrics
        risk_metrics = self._calculate_risk_metrics(stock_data)
        
        # Calculate position sizing
        position_sizing = self._calculate_position_sizing(
            stock_data,
            technical,
            user_context.get('portfolio_value', 1000000),
        )
        
        # Build prompt
        prompt = self._build_analysis_prompt(
            stock_data,
            fundamental,
            technical,
            risk_metrics,
            position_sizing,
            user_context,
        )
        
        # Run LLM analysis
        result = await self._run_llm_analysis(prompt)
        
        return result
    
    def _calculate_risk_metrics(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate risk metrics from historical data."""
        metrics = {}
        
        price_data = stock_data.get('price_data', {})
        historical = price_data.get('historical_ohlcv', [])
        
        if not historical or len(historical) < 30:
            return self._get_basic_risk_metrics(price_data)
        
        # Calculate returns
        closes = [h['close'] for h in historical]
        returns = []
        for i in range(1, len(closes)):
            ret = (closes[i] - closes[i-1]) / closes[i-1]
            returns.append(ret)
        
        # Volatility
        vol_result = calculate_volatility(returns)
        metrics['volatility'] = {
            'value': vol_result.result,
            'rating': self._get_volatility_rating(vol_result.result),
            'interpretation': vol_result.interpretation,
        }
        
        # Max Drawdown
        mdd_result = calculate_max_drawdown(closes)
        metrics['max_drawdown'] = {
            'value_1y': mdd_result.result,
            'interpretation': mdd_result.interpretation,
        }
        
        # Sharpe Ratio
        sharpe_result = calculate_sharpe_ratio(returns)
        metrics['sharpe_ratio'] = sharpe_result.result
        
        # Beta (assuming we had market returns, using 1.0 as default)
        metrics['beta'] = self._estimate_beta(stock_data)
        
        return metrics
    
    def _get_basic_risk_metrics(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get basic risk metrics when historical data is limited."""
        current = price_data.get('current_price', 0)
        high_52 = price_data.get('week_52_high', price_data.get('52_week_high', current))
        low_52 = price_data.get('week_52_low', price_data.get('52_week_low', current))
        
        # Estimate volatility from 52-week range
        if high_52 > 0 and low_52 > 0:
            range_pct = ((high_52 - low_52) / ((high_52 + low_52) / 2)) * 100
            estimated_vol = range_pct / 4  # Rough approximation
        else:
            estimated_vol = 25  # Default moderate volatility
        
        return {
            'volatility': {
                'value': estimated_vol,
                'rating': self._get_volatility_rating(estimated_vol),
                'interpretation': 'Estimated from 52-week range',
            },
            'max_drawdown': {
                'value_1y': ((high_52 - low_52) / high_52 * 100) if high_52 > 0 else 20,
                'interpretation': 'Estimated from 52-week range',
            },
            'beta': 1.0,
            'sharpe_ratio': None,
        }
    
    def _get_volatility_rating(self, volatility: float) -> str:
        """Get volatility rating."""
        if volatility > 40:
            return "Very High"
        elif volatility > 30:
            return "High"
        elif volatility > 20:
            return "Moderate"
        else:
            return "Low"
    
    def _estimate_beta(self, stock_data: Dict[str, Any]) -> float:
        """Estimate beta based on sector and volatility."""
        fund_data = stock_data.get('fundamental_data', {})
        sector = fund_data.get('sector', '').lower()
        
        # Sector-based beta estimates
        sector_betas = {
            'technology': 1.3,
            'financial': 1.2,
            'consumer cyclical': 1.1,
            'industrials': 1.1,
            'energy': 1.2,
            'healthcare': 0.8,
            'utilities': 0.6,
            'consumer defensive': 0.7,
            'real estate': 1.0,
        }
        
        for s, beta in sector_betas.items():
            if s in sector:
                return beta
        
        return 1.0  # Default market beta
    
    def _calculate_position_sizing(
        self,
        stock_data: Dict[str, Any],
        technical: Dict[str, Any],
        portfolio_value: float,
    ) -> Dict[str, Any]:
        """Calculate position sizing recommendations."""
        
        price_data = stock_data.get('price_data', {})
        current_price = price_data.get('current_price', 0)
        
        # Get stop loss from technical analysis if available
        trading_setup = technical.get('trading_setup', {})
        stop_loss = trading_setup.get('stop_loss')
        
        if not stop_loss and current_price > 0:
            # Default 5% stop loss
            stop_loss = current_price * 0.95
        
        # Calculate position sizes
        sizing = {
            'portfolio_value_assumed': portfolio_value,
        }
        
        if current_price > 0 and stop_loss > 0:
            for risk_level, (risk_pct, min_pct, max_pct) in {
                'conservative': (1.0, 2, 3),
                'moderate': (2.0, 3, 5),
                'aggressive': (3.0, 5, 8),
            }.items():
                result = calculate_position_size(
                    portfolio_value,
                    risk_pct,
                    current_price,
                    stop_loss,
                )
                
                # Also calculate based on percentage allocation
                min_shares = int((portfolio_value * min_pct / 100) / current_price)
                max_shares = int((portfolio_value * max_pct / 100) / current_price)
                
                sizing[risk_level] = {
                    'percentage': f"{min_pct}-{max_pct}%",
                    'amount_range': [
                        portfolio_value * min_pct / 100,
                        portfolio_value * max_pct / 100,
                    ],
                    'shares': [min_shares, max_shares],
                    'rationale': f"Based on {risk_pct}% risk per trade",
                }
            
            # Recommended (moderate)
            rec_shares = int((portfolio_value * 0.04) / current_price)
            sizing['recommended'] = {
                'percentage': '4%',
                'amount': portfolio_value * 0.04,
                'shares': rec_shares,
                'rationale': 'Balanced risk-reward for most investors',
            }
        
        return sizing
    
    def _build_analysis_prompt(
        self,
        stock_data: Dict[str, Any],
        fundamental: Dict[str, Any],
        technical: Dict[str, Any],
        risk_metrics: Dict[str, Any],
        position_sizing: Dict[str, Any],
        user_context: Dict[str, Any],
    ) -> str:
        """Build the analysis prompt."""
        
        ticker = stock_data.get('ticker', 'Unknown')
        name = stock_data.get('name', ticker)
        price_data = stock_data.get('price_data', {})
        fund_data = stock_data.get('fundamental_data', {})
        
        prompt = f"""Analyze the risk profile for {name} ({ticker}).

=== PRICE DATA ===
Current Price: ₹{price_data.get('current_price', 'N/A')}
52-Week High: ₹{price_data.get('week_52_high', price_data.get('52_week_high', 'N/A'))}
52-Week Low: ₹{price_data.get('week_52_low', price_data.get('52_week_low', 'N/A'))}
Average Volume: {price_data.get('avg_volume', 0):,}

=== CALCULATED RISK METRICS ===
Volatility: {risk_metrics.get('volatility', {}).get('value', 'N/A')}% ({risk_metrics.get('volatility', {}).get('rating', 'N/A')})
Max Drawdown (1Y): {risk_metrics.get('max_drawdown', {}).get('value_1y', 'N/A')}%
Beta (estimated): {risk_metrics.get('beta', 'N/A')}
Sharpe Ratio: {risk_metrics.get('sharpe_ratio', 'N/A')}

=== FUNDAMENTAL CONTEXT ===
Debt/Equity: {fund_data.get('debt_to_equity', 'N/A')}
Sector: {fund_data.get('sector', 'N/A')}
Fundamental Score: {fundamental.get('score', 'N/A')}/100

=== TECHNICAL CONTEXT ===
Technical Score: {technical.get('score', 'N/A')}/100
Stop Loss Level: ₹{technical.get('trading_setup', {}).get('stop_loss', 'N/A')}

=== POSITION SIZING (Pre-calculated) ===
Portfolio Value: ₹{position_sizing.get('portfolio_value_assumed', 1000000):,}
Conservative: {position_sizing.get('conservative', {}).get('percentage', 'N/A')} = {position_sizing.get('conservative', {}).get('shares', ['N/A'])} shares
Moderate: {position_sizing.get('moderate', {}).get('percentage', 'N/A')} = {position_sizing.get('moderate', {}).get('shares', ['N/A'])} shares
Aggressive: {position_sizing.get('aggressive', {}).get('percentage', 'N/A')} = {position_sizing.get('aggressive', {}).get('shares', ['N/A'])} shares

=== USER CONTEXT ===
Risk Appetite: {user_context.get('risk_appetite', 'Moderate')}
Investment Horizon: {user_context.get('time_horizon', 'Medium-term')}

Based on this data, provide:
1. Risk score (0-100, higher = riskier)
2. Risk rating (LOW, MODERATE, HIGH, VERY_HIGH)
3. Stock risk metrics assessment
4. Liquidity analysis
5. Position sizing recommendations
6. Scenario analysis (market crash, sector correction, stop loss)
7. Key risk factors (list 3-5)
8. Risk mitigation strategies (list 3-5)

Do NOT make buy/sell recommendations. Focus only on risk quantification."""

        return prompt
    
    def _get_fallback_response(self, error: str) -> Dict[str, Any]:
        """Get fallback response when analysis fails."""
        return {
            "risk_score": 50,
            "risk_rating": "MODERATE",
            "risk_level": "Medium",
            "stock_risk_metrics": {
                "beta": 1.0,
                "interpretation": "Default market beta",
                "volatility_30d": 25,
                "volatility_rating": "Moderate",
                "max_drawdown_1y": -20,
                "sharpe_ratio": None,
            },
            "liquidity_analysis": {
                "avg_daily_volume": 0,
                "avg_daily_value": 0,
                "liquidity_rating": "Unknown",
            },
            "position_sizing": {
                "portfolio_value_assumed": 1000000,
                "conservative": {
                    "percentage": "2-3%",
                    "amount_range": [20000, 30000],
                    "shares": [0, 0],
                    "rationale": "Conservative allocation",
                },
                "moderate": {
                    "percentage": "3-5%",
                    "amount_range": [30000, 50000],
                    "shares": [0, 0],
                    "rationale": "Moderate allocation",
                },
                "aggressive": {
                    "percentage": "5-8%",
                    "amount_range": [50000, 80000],
                    "shares": [0, 0],
                    "rationale": "Aggressive allocation",
                },
                "recommended": {
                    "percentage": "4%",
                    "amount": 40000,
                    "shares": 0,
                    "rationale": "Default recommendation",
                },
            },
            "scenario_analysis": {
                "market_crash_minus20": {"expected_stock_decline": -20, "comment": "Estimated"},
                "sector_correction_minus10": {"expected_stock_decline": -10, "comment": "Estimated"},
                "stop_loss_triggered": {"loss_percent": -5, "comment": "Default"},
            },
            "risk_factors": [f"Analysis incomplete: {error}"],
            "risk_mitigation": ["Use stop loss orders", "Diversify portfolio"],
        }
