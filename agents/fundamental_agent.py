"""Fundamental Analysis Agent - FIXED VERSION."""

from typing import Any, Dict, Type
from pydantic import BaseModel
from loguru import logger
import numpy as np

from .base_agent import BaseAgent
from .schemas import FundamentalAnalysis, Rating
from utils.math_tools import (
    calculate_pe_ratio,
    calculate_fair_value_pe,
    calculate_cagr,
)


class FundamentalAgent(BaseAgent):
    """Agent for fundamental analysis of stocks."""
    
    def __init__(self):
        super().__init__("Fundamental Analyst")
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert fundamental analyst specializing in Indian equities (NSE/BSE).
Your role is to evaluate a company's intrinsic value and financial health.

Focus on:
1. Valuation ratios (P/E, P/B, PEG, EV/EBITDA)
2. Profitability metrics (ROE, ROCE, ROA, margins)
3. Financial health (Debt/Equity, Current Ratio, Interest Coverage)
4. Growth metrics (revenue, profit CAGR)
5. Cash flow analysis
6. Dividend sustainability
7. Promoter holding and pledge status

DO NOT analyze:
- Technical charts or price patterns
- Market sentiment or news
- Sector trends beyond peer comparison

Provide scores from 0-100 where:
- 80-100: Strong fundamentals, undervalued
- 60-79: Good fundamentals, fairly valued
- 40-59: Average fundamentals
- 20-39: Weak fundamentals
- 0-19: Poor fundamentals, avoid

Be objective and data-driven. Always explain your reasoning."""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return FundamentalAnalysis
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform fundamental analysis.

        Args:
            data: Dict containing stock_data with price_data, fundamental_data, ownership_data

        Returns:
            FundamentalAnalysis as dictionary
        """
        ticker = data.get('ticker', 'unknown')
        logger.info(f"Running fundamental analysis for {ticker}")

        stock_data = data.get('stock_data') or {}
        fundamental_data = stock_data.get('fundamental_data') or {}

        # ✅ Check if this is an ETF or commodity without fundamental data
        # Check if ALL fundamental fields are None/0 (except market_cap which can be 0)
        has_data = False
        for key, value in fundamental_data.items():
            if key == 'market_cap':
                continue
            if value not in (None, 0, 0.0, '', []):
                has_data = True
                break

        if not has_data:
            logger.warning(f"No fundamental data available for {ticker} - likely ETF/commodity/index")
            return {
                "score": 50,
                "rating": "NOT_APPLICABLE",
                "recommendation": "FAIRLY_VALUED",
                "valuation": {
                    "current_pe": None,
                    "sector_avg_pe": None,
                    "fair_pe": None,
                    "fair_value": None,
                    "upside_potential_percent": None,
                    "margin_of_safety": None,
                },
                "quality_metrics": {
                    "roe": None,
                    "roce": None,
                    "operating_margin": None,
                    "net_margin": None,
                    "earnings_quality_score": None,
                },
                "growth_metrics": {
                    "revenue_growth_3y_cagr": None,
                    "profit_growth_3y_cagr": None,
                    "growth_consistency_score": None,
                },
                "financial_health": {
                    "debt_to_equity": None,
                    "interest_coverage": None,
                    "current_ratio": None,
                    "free_cash_flow": None,
                    "balance_sheet_strength_score": None,
                },
                "strengths": ["This is an ETF/commodity/index - fundamental analysis not applicable"],
                "concerns": ["No company-specific fundamental data available"],
                "peer_comparison": [],
            }

        try:
            # Pre-calculate some metrics
            calculations = self._perform_calculations(stock_data) or {}

            # Build prompt
            prompt = self._build_analysis_prompt(stock_data, calculations)

            # Run LLM analysis
            result = await self._run_llm_analysis(prompt)

            # ✅ Validate result structure
            if not result or not isinstance(result, dict):
                logger.error(f"Invalid result from LLM: {type(result)}")
                return self._get_fallback_response("LLM returned invalid response")

            # ✅ Ensure required fields exist
            if 'score' not in result:
                logger.warning(f"Result missing 'score' field, using fallback")
                return self._get_fallback_response("Incomplete LLM response")

            return result

        except Exception as e:
            logger.error(f"Error in fundamental analysis: {e}", exc_info=True)
            return self._get_fallback_response(str(e))
    
    def _perform_calculations(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Pre-calculate fundamental metrics."""
        calculations = {}
        
        price_data = stock_data.get('price_data', {})
        fund_data = stock_data.get('fundamental_data', {})
        
        current_price = price_data.get('current_price', 0)
        eps = fund_data.get('eps')
        
        # Calculate PE
        if eps and eps > 0 and current_price > 0:
            pe_result = calculate_pe_ratio(current_price, eps)
            calculations['calculated_pe'] = pe_result.result
        
        # Calculate fair value (using sector average PE of 25 as default)
        sector_pe = 25  # Default, would be better with real sector data
        if eps and eps > 0:
            fair_value_result = calculate_fair_value_pe(eps, sector_pe)
            calculations['fair_value'] = fair_value_result.result
            
            if current_price > 0:
                calculations['upside'] = ((fair_value_result.result - current_price) / current_price) * 100
        
        # Calculate valuation score
        calculations['valuation_score'] = self._calculate_valuation_score(
            fund_data.get('pe_ratio'),
            fund_data.get('pb_ratio'),
        )
        
        # Calculate quality score
        calculations['quality_score'] = self._calculate_quality_score(
            fund_data.get('roe'),
            fund_data.get('roce'),
            fund_data.get('quarterly_results', {}).get('operating_margin'),
        )
        
        # Calculate safety score
        calculations['safety_score'] = self._calculate_safety_score(
            fund_data.get('debt_to_equity'),
            fund_data.get('current_ratio'),
        )
        
        return calculations
    
    def _calculate_valuation_score(
        self,
        pe: float | None,
        pb: float | None,
    ) -> int:
        """Calculate valuation score."""
        score = 50  # Base score
        
        if pe:
            if pe < 15:
                score += 20
            elif pe < 25:
                score += 10
            elif pe > 40:
                score -= 15
            elif pe > 30:
                score -= 10
        
        if pb:
            if pb < 2:
                score += 15
            elif pb < 4:
                score += 5
            elif pb > 6:
                score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_quality_score(
        self,
        roe: float | None,
        roce: float | None,
        operating_margin: float | None,
    ) -> int:
        """Calculate quality score."""
        score = 50
        
        if roe:
            if roe > 20:
                score += 20
            elif roe > 15:
                score += 10
            elif roe < 10:
                score -= 10
        
        if roce:
            if roce > 20:
                score += 15
            elif roce > 15:
                score += 5
            elif roce < 10:
                score -= 10
        
        if operating_margin:
            if operating_margin > 25:
                score += 15
            elif operating_margin > 15:
                score += 5
            elif operating_margin < 10:
                score -= 10
        
        return max(0, min(100, score))
    
    def _calculate_safety_score(
        self,
        debt_to_equity: float | None,
        current_ratio: float | None,
    ) -> int:
        """Calculate financial safety score."""
        score = 50
        
        if debt_to_equity is not None:
            if debt_to_equity < 0.3:
                score += 25
            elif debt_to_equity < 0.5:
                score += 15
            elif debt_to_equity < 1:
                score += 5
            elif debt_to_equity > 2:
                score -= 20
            elif debt_to_equity > 1:
                score -= 10
        
        if current_ratio:
            if current_ratio > 2:
                score += 15
            elif current_ratio > 1.5:
                score += 10
            elif current_ratio < 1:
                score -= 15
        
        return max(0, min(100, score))
    
    def _format_value(self, value: Any, format_type: str = "general") -> str:
        """Safely format values with appropriate fallbacks."""
        if value is None or (isinstance(value, float) and np.isnan(value)):
            return "N/A"
        
        try:
            if format_type == "currency":
                return f"₹{float(value):,.2f}"
            elif format_type == "large_currency":
                return f"₹{float(value):,.0f}"
            elif format_type == "percent":
                return f"{float(value):.2f}%"
            elif format_type == "ratio":
                return f"{float(value):.2f}"
            elif format_type == "number":
                return f"{int(value):,}"
            else:
                return str(value)
        except (ValueError, TypeError):
            return "N/A"
    
    def _build_analysis_prompt(
        self,
        stock_data: Dict[str, Any],
        calculations: Dict[str, Any],
    ) -> str:
        """Build the analysis prompt with safe formatting."""
        
        ticker = stock_data.get('ticker', 'Unknown')
        name = stock_data.get('name', ticker)
        
        price_data = stock_data.get('price_data', {})
        fund_data = stock_data.get('fundamental_data', {})
        ownership = stock_data.get('ownership_data', {})
        quarterly = fund_data.get('quarterly_results', {})
        
        # Format calculated metrics safely
        upside = calculations.get('upside')
        upside_str = f"{upside:.1f}%" if upside is not None else "N/A"
        
        fair_value = calculations.get('fair_value')
        fair_value_str = f"₹{fair_value:,.2f}" if fair_value is not None else "N/A"
        
        prompt = f"""Analyze the fundamental strength of {name} ({ticker}).

=== PRICE DATA ===
Current Price: {self._format_value(price_data.get('current_price'), 'currency')}
Change: {self._format_value(price_data.get('change_percent'), 'percent')}
Volume: {self._format_value(price_data.get('volume'), 'number')} shares
52W High: {self._format_value(price_data.get('52_week_high'), 'currency')}
52W Low: {self._format_value(price_data.get('52_week_low'), 'currency')}
Previous Close: {self._format_value(price_data.get('previous_close'), 'currency')}

=== FUNDAMENTAL DATA ===
Market Cap: {self._format_value(fund_data.get('market_cap'), 'large_currency')}
P/E Ratio: {self._format_value(fund_data.get('pe_ratio'), 'ratio')}
P/B Ratio: {self._format_value(fund_data.get('pb_ratio'), 'ratio')}
EPS: {self._format_value(fund_data.get('eps'), 'currency')}
Dividend Yield: {self._format_value(fund_data.get('dividend_yield'), 'percent')}
ROE: {self._format_value(fund_data.get('roe'), 'percent')}
ROCE: {self._format_value(fund_data.get('roce'), 'percent')}
Debt/Equity: {self._format_value(fund_data.get('debt_to_equity'), 'ratio')}
Current Ratio: {self._format_value(fund_data.get('current_ratio'), 'ratio')}
Book Value: {self._format_value(fund_data.get('book_value'), 'currency')}
Industry: {fund_data.get('industry', 'N/A')}
Sector: {fund_data.get('sector', 'N/A')}

=== QUARTERLY RESULTS ===
Revenue: {self._format_value(quarterly.get('revenue'), 'large_currency')}
Revenue Growth YoY: {self._format_value(quarterly.get('revenue_growth_yoy'), 'percent')}
Net Profit: {self._format_value(quarterly.get('net_profit'), 'large_currency')}
Profit Growth YoY: {self._format_value(quarterly.get('profit_growth_yoy'), 'percent')}
Operating Margin: {self._format_value(quarterly.get('operating_margin'), 'percent')}
Net Margin: {self._format_value(quarterly.get('net_margin'), 'percent')}

=== OWNERSHIP DATA ===
Promoter Holding: {self._format_value(ownership.get('promoter_holding'), 'percent')}
FII Holding: {self._format_value(ownership.get('fii_holding'), 'percent')}
DII Holding: {self._format_value(ownership.get('dii_holding'), 'percent')}
Public Holding: {self._format_value(ownership.get('public_holding'), 'percent')}
Pledged Shares: {self._format_value(ownership.get('pledged_shares'), 'percent')}

=== PRE-CALCULATED METRICS ===
Valuation Score: {calculations.get('valuation_score', 'N/A')}/100
Quality Score: {calculations.get('quality_score', 'N/A')}/100
Safety Score: {calculations.get('safety_score', 'N/A')}/100
Calculated Fair Value: {fair_value_str}
Potential Upside: {upside_str}

Based on this data, provide a comprehensive fundamental analysis including:
1. Overall fundamental score (0-100)
2. Rating (STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL)
3. Valuation assessment (UNDERVALUED, FAIRLY_VALUED, OVERVALUED)
4. Key strengths (list 3-5 concrete points)
5. Key concerns (list 2-4 concrete points)
6. Fair value estimate with clear reasoning

Focus only on fundamental factors. Do not consider technical analysis or market sentiment."""

        return prompt
    
    def _get_fallback_response(self, error: str) -> Dict[str, Any]:
        """Get fallback response when analysis fails."""
        logger.warning(f"Using fallback response due to: {error}")
        return {
            "score": 50,
            "rating": "HOLD",
            "recommendation": "FAIRLY_VALUED",
            "valuation": {
                "current_pe": None,
                "sector_avg_pe": None,
                "fair_pe": None,
                "fair_value": None,
                "upside_potential_percent": None,
                "margin_of_safety": None,
            },
            "quality_metrics": {
                "roe": None,
                "roce": None,
                "operating_margin": None,
                "net_margin": None,
                "earnings_quality_score": None,
            },
            "growth_metrics": {
                "revenue_growth_3y_cagr": None,
                "profit_growth_3y_cagr": None,
                "growth_consistency_score": None,
            },
            "financial_health": {
                "debt_to_equity": None,
                "interest_coverage": None,
                "current_ratio": None,
                "free_cash_flow": None,
                "balance_sheet_strength_score": None,
            },
            "strengths": [f"Analysis incomplete: {error[:100]}"],
            "concerns": ["Unable to complete fundamental analysis - please try again"],
            "peer_comparison": [],
        }