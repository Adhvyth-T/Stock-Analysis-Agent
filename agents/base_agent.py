"""Base agent class for all specialized agents."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from loguru import logger

from .llm_provider import llm, LLMProvider


class BaseAgent(ABC):
    """Base class for all analysis agents."""
    
    def __init__(self, name: str):
        self.name = name
        self.llm = llm
    
    @property
    @abstractmethod
    def system_prompt(self) -> str:
        """System prompt for the agent."""
        pass
    
    @property
    @abstractmethod
    def output_schema(self) -> Type[BaseModel]:
        """Pydantic schema for agent output."""
        pass
    
    @abstractmethod
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform analysis on the provided data.
        
        Args:
            data: Input data for analysis
            
        Returns:
            Analysis results as dictionary
        """
        pass
    
    def _build_analysis_prompt(self, data: Dict[str, Any]) -> str:
        """Build the analysis prompt from data."""
        raise NotImplementedError
    
    async def _run_llm_analysis(
        self,
        prompt: str,
        schema: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        """
        Run LLM analysis with error handling.
        
        Args:
            prompt: Analysis prompt
            schema: Optional output schema
            
        Returns:
            Analysis results
        """
        try:
            result = await self.llm.generate(
                prompt=prompt,
                system_prompt=self.system_prompt,
                response_schema=schema or self.output_schema,
            )
            
            if isinstance(result, BaseModel):
                return result.model_dump()
            
            if not isinstance(result, dict):
                logger.error(f"{self.name}: LLM returned non-dict result: {type(result)}")
                return self._get_fallback_response("Invalid LLM response format")
            
            return result
            
        except Exception as e:
            logger.error(f"{self.name} analysis failed: {e}", exc_info=True)
            return self._get_fallback_response(str(e))
    
    def _get_fallback_response(self, error: str) -> Dict[str, Any]:
        """Get fallback response when analysis fails."""
        return {
            "error": error,
            "score": 50,
            "confidence": "LOW",
            "message": f"{self.name} analysis could not be completed",
        }
    
    def _format_price_data(self, price_data: Dict[str, Any]) -> str:
        """Format price data for prompt."""
        return f"""
Current Price: ₹{price_data.get('current_price', 'N/A')}
Change: {price_data.get('change_percent', 0):.2f}%
Volume: {price_data.get('volume', 0):,}
Day High: ₹{price_data.get('day_high', 'N/A')}
Day Low: ₹{price_data.get('day_low', 'N/A')}
52-Week High: ₹{price_data.get('week_52_high', price_data.get('52_week_high', 'N/A'))}
52-Week Low: ₹{price_data.get('week_52_low', price_data.get('52_week_low', 'N/A'))}
Average Volume: {price_data.get('avg_volume', 0):,}
"""
    
    def _format_fundamental_data(self, fund_data: Dict[str, Any]) -> str:
        """Format fundamental data for prompt."""
        return f"""
Market Cap: ₹{fund_data.get('market_cap', 0):,.0f}
P/E Ratio: {fund_data.get('pe_ratio', 'N/A')}
P/B Ratio: {fund_data.get('pb_ratio', 'N/A')}
EPS: ₹{fund_data.get('eps', 'N/A')}
ROE: {fund_data.get('roe', 'N/A')}%
ROCE: {fund_data.get('roce', 'N/A')}%
Debt/Equity: {fund_data.get('debt_to_equity', 'N/A')}
Current Ratio: {fund_data.get('current_ratio', 'N/A')}
Dividend Yield: {fund_data.get('dividend_yield', 0):.2f}%
Industry: {fund_data.get('industry', 'N/A')}
Sector: {fund_data.get('sector', 'N/A')}
"""
    
    def _format_ownership_data(self, ownership: Dict[str, Any]) -> str:
        """Format ownership data for prompt."""
        return f"""
Promoter Holding: {ownership.get('promoter_holding', 0):.2f}%
FII Holding: {ownership.get('fii_holding', 0):.2f}%
DII Holding: {ownership.get('dii_holding', 0):.2f}%
Public Holding: {ownership.get('public_holding', 0):.2f}%
Pledged Shares: {ownership.get('pledged_shares', 0):.2f}%
"""
