"""Technical Analysis Agent."""

from typing import Any, Dict, Type, List
from pydantic import BaseModel
from loguru import logger
import numpy as np
import pandas as pd

from .base_agent import BaseAgent
from .schemas import TechnicalAnalysis, Signal, Confidence
from utils.math_tools import calculate_rsi, calculate_max_drawdown


class TechnicalAgent(BaseAgent):
    """Agent for technical analysis of stocks."""
    
    def __init__(self):
        super().__init__("Technical Analyst")
    
    @property
    def system_prompt(self) -> str:
        return """You are an expert technical analyst specializing in Indian equities (NSE/BSE).
Your role is to analyze price action and identify trading setups.

Focus on:
1. Trend analysis (short-term, medium-term, long-term)
2. Technical indicators (RSI, MACD, Bollinger Bands, Moving Averages)
3. Chart patterns (Triangles, Head & Shoulders, Cup & Handle, etc.)
4. Support and resistance levels
5. Volume analysis
6. Entry, exit, and stop-loss points

DO NOT analyze:
- Company fundamentals
- News or sentiment
- Macroeconomic factors

Scoring (0-100):
- 80-100: Strong bullish setup
- 60-79: Moderately bullish
- 40-59: Neutral/sideways
- 20-39: Moderately bearish
- 0-19: Strong bearish setup

Be specific with price levels. Always provide risk-reward ratios."""
    
    @property
    def output_schema(self) -> Type[BaseModel]:
        return TechnicalAnalysis
    
    async def analyze(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform technical analysis.
        
        Args:
            data: Dict containing stock_data with price_data and historical OHLCV
            
        Returns:
            TechnicalAnalysis as dictionary
        """
        logger.info(f"Running technical analysis for {data.get('ticker', 'unknown')}")
        
        stock_data = data.get('stock_data', {})
        
        # Calculate technical indicators
        indicators = self._calculate_indicators(stock_data)
        
        # Build prompt
        prompt = self._build_analysis_prompt(stock_data, indicators)
        
        # Run LLM analysis
        result = await self._run_llm_analysis(prompt)
        
        return result
    
    def _calculate_indicators(self, stock_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate technical indicators from historical data."""
        indicators = {}
        
        price_data = stock_data.get('price_data', {})
        historical = price_data.get('historical_ohlcv', [])
        
        if not historical or len(historical) < 20:
            return self._get_basic_indicators(price_data)
        
        # Convert to pandas DataFrame
        df = pd.DataFrame(historical)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        closes = df['close'].values.tolist()
        volumes = df['volume'].values.tolist()
        current_price = price_data.get('current_price', closes[-1] if closes else 0)
        
        # RSI
        rsi_result = calculate_rsi(closes)
        indicators['rsi'] = {
            'value': rsi_result.result,
            'signal': self._get_rsi_signal(rsi_result.result),
            'interpretation': rsi_result.interpretation,
        }
        
        # Moving Averages
        indicators['moving_averages'] = self._calculate_moving_averages(df, current_price)
        
        # MACD
        indicators['macd'] = self._calculate_macd(closes)
        
        # Bollinger Bands
        indicators['bollinger'] = self._calculate_bollinger_bands(closes, current_price)
        
        # Support/Resistance
        indicators['support_resistance'] = self._identify_support_resistance(df, current_price)
        
        # Volume analysis
        indicators['volume'] = self._analyze_volume(volumes, price_data.get('volume', 0))
        
        # Trend
        indicators['trend'] = self._determine_trend(df, current_price)
        
        # Max drawdown
        mdd_result = calculate_max_drawdown(closes)
        indicators['max_drawdown'] = mdd_result.result
        
        return indicators
    
    def _get_basic_indicators(self, price_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get basic indicators when historical data is limited."""
        current = price_data.get('current_price', 0)
        high_52 = price_data.get('week_52_high', price_data.get('52_week_high', current))
        low_52 = price_data.get('week_52_low', price_data.get('52_week_low', current))
        
        # Calculate position in 52-week range
        if high_52 > low_52:
            position = (current - low_52) / (high_52 - low_52) * 100
        else:
            position = 50
        
        return {
            'rsi': {
                'value': 50,
                'signal': 'Neutral',
                'interpretation': 'Insufficient data for RSI',
            },
            'position_in_52w': position,
            'trend': {
                'short_term': 'Unknown',
                'medium_term': 'Unknown',
                'long_term': 'Unknown',
            },
        }
    
    def _get_rsi_signal(self, rsi: float) -> str:
        """Get RSI signal."""
        if rsi > 70:
            return "Overbought"
        elif rsi < 30:
            return "Oversold"
        elif rsi > 60:
            return "Bullish"
        elif rsi < 40:
            return "Bearish"
        return "Neutral"
    
    def _calculate_moving_averages(
        self,
        df: pd.DataFrame,
        current_price: float,
    ) -> Dict[str, Any]:
        """Calculate moving averages."""
        result = {}
        
        for period in [20, 50, 200]:
            if len(df) >= period:
                ema = df['close'].ewm(span=period, adjust=False).mean().iloc[-1]
                result[f'ema_{period}'] = round(ema, 2)
                
                if current_price > ema:
                    result[f'price_vs_ema{period}'] = f"Above (bullish)"
                else:
                    result[f'price_vs_ema{period}'] = f"Below (bearish)"
        
        return result
    
    def _calculate_macd(self, closes: List[float]) -> Dict[str, Any]:
        """Calculate MACD."""
        if len(closes) < 26:
            return {'value': 0, 'signal': 'Neutral', 'histogram': 0}
        
        closes_series = pd.Series(closes)
        ema_12 = closes_series.ewm(span=12, adjust=False).mean()
        ema_26 = closes_series.ewm(span=26, adjust=False).mean()
        
        macd_line = ema_12 - ema_26
        signal_line = macd_line.ewm(span=9, adjust=False).mean()
        histogram = macd_line - signal_line
        
        current_macd = macd_line.iloc[-1]
        current_signal = signal_line.iloc[-1]
        current_hist = histogram.iloc[-1]
        
        if current_macd > current_signal and current_hist > 0:
            signal = "Bullish"
        elif current_macd < current_signal and current_hist < 0:
            signal = "Bearish"
        else:
            signal = "Neutral"
        
        return {
            'value': round(current_macd, 2),
            'signal_line': round(current_signal, 2),
            'histogram': round(current_hist, 2),
            'signal': signal,
            'interpretation': f"MACD {'above' if current_macd > current_signal else 'below'} signal line",
        }
    
    def _calculate_bollinger_bands(
        self,
        closes: List[float],
        current_price: float,
    ) -> Dict[str, Any]:
        """Calculate Bollinger Bands."""
        if len(closes) < 20:
            return {}
        
        closes_series = pd.Series(closes)
        sma_20 = closes_series.rolling(window=20).mean().iloc[-1]
        std_20 = closes_series.rolling(window=20).std().iloc[-1]
        
        upper = sma_20 + (2 * std_20)
        lower = sma_20 - (2 * std_20)
        
        # Determine position
        if current_price > upper:
            position = "Above upper band (overbought)"
        elif current_price < lower:
            position = "Below lower band (oversold)"
        elif current_price > sma_20:
            position = "Above middle band (bullish)"
        else:
            position = "Below middle band (bearish)"
        
        return {
            'upper': round(upper, 2),
            'middle': round(sma_20, 2),
            'lower': round(lower, 2),
            'position': position,
            'width': round((upper - lower) / sma_20 * 100, 2),
        }
    
    def _identify_support_resistance(
        self,
        df: pd.DataFrame,
        current_price: float,
    ) -> Dict[str, List[float]]:
        """Identify support and resistance levels."""
        highs = df['high'].values
        lows = df['low'].values
        closes = df['close'].values
        
        # Find local maxima and minima
        resistance_levels = []
        support_levels = []
        
        # Recent highs as resistance
        for i in range(5, len(highs) - 5):
            if highs[i] == max(highs[i-5:i+5]):
                resistance_levels.append(highs[i])
        
        # Recent lows as support
        for i in range(5, len(lows) - 5):
            if lows[i] == min(lows[i-5:i+5]):
                support_levels.append(lows[i])
        
        # Filter to levels near current price
        resistance = sorted([r for r in resistance_levels if r > current_price])[:3]
        support = sorted([s for s in support_levels if s < current_price], reverse=True)[:3]
        
        # Add 52-week high/low if available
        if len(df) > 0:
            high_52 = df['high'].max()
            low_52 = df['low'].min()
            
            if high_52 > current_price and high_52 not in resistance:
                resistance.append(high_52)
            if low_52 < current_price and low_52 not in support:
                support.append(low_52)
        
        return {
            'immediate_resistance': [round(r, 2) for r in resistance[:2]] if resistance else [],
            'major_resistance': [round(r, 2) for r in resistance[2:4]] if len(resistance) > 2 else [],
            'immediate_support': [round(s, 2) for s in support[:2]] if support else [],
            'major_support': [round(s, 2) for s in support[2:4]] if len(support) > 2 else [],
        }
    
    def _analyze_volume(
        self,
        historical_volumes: List[int],
        current_volume: int,
    ) -> Dict[str, Any]:
        """Analyze volume patterns."""
        if not historical_volumes:
            return {
                'current_volume': current_volume,
                'avg_volume_20d': 0,
                'volume_trend': 'Unknown',
            }
        
        avg_20d = np.mean(historical_volumes[-20:]) if len(historical_volumes) >= 20 else np.mean(historical_volumes)
        
        if current_volume > 0 and avg_20d > 0:
            ratio = current_volume / avg_20d
            if ratio > 1.5:
                trend = f"Above average by {(ratio - 1) * 100:.0f}%"
                interpretation = "High volume - strong interest"
            elif ratio > 1:
                trend = f"Above average by {(ratio - 1) * 100:.0f}%"
                interpretation = "Moderate volume"
            elif ratio > 0.7:
                trend = f"Below average by {(1 - ratio) * 100:.0f}%"
                interpretation = "Low volume - weak conviction"
            else:
                trend = f"Below average by {(1 - ratio) * 100:.0f}%"
                interpretation = "Very low volume"
        else:
            trend = "Unknown"
            interpretation = "Insufficient data"
        
        return {
            'current_volume': current_volume,
            'avg_volume_20d': int(avg_20d),
            'volume_trend': trend,
            'interpretation': interpretation,
        }
    
    def _determine_trend(
        self,
        df: pd.DataFrame,
        current_price: float,
    ) -> Dict[str, str]:
        """Determine trend across timeframes."""
        trend = {
            'short_term': 'Sideways',
            'medium_term': 'Sideways',
            'long_term': 'Sideways',
        }
        
        closes = df['close'].values
        
        # Short-term (20 days)
        if len(closes) >= 20:
            short_ma = np.mean(closes[-20:])
            if current_price > short_ma * 1.02:
                trend['short_term'] = 'Uptrend'
            elif current_price < short_ma * 0.98:
                trend['short_term'] = 'Downtrend'
        
        # Medium-term (50 days)
        if len(closes) >= 50:
            medium_ma = np.mean(closes[-50:])
            if current_price > medium_ma * 1.05:
                trend['medium_term'] = 'Uptrend'
            elif current_price < medium_ma * 0.95:
                trend['medium_term'] = 'Downtrend'
        
        # Long-term (200 days)
        if len(closes) >= 200:
            long_ma = np.mean(closes[-200:])
            if current_price > long_ma * 1.1:
                trend['long_term'] = 'Uptrend'
            elif current_price < long_ma * 0.9:
                trend['long_term'] = 'Downtrend'
        
        return trend
    
    def _build_analysis_prompt(
        self,
        stock_data: Dict[str, Any],
        indicators: Dict[str, Any],
    ) -> str:
        """Build the analysis prompt."""
        
        ticker = stock_data.get('ticker', 'Unknown')
        name = stock_data.get('name', ticker)
        price_data = stock_data.get('price_data', {})
        
        prompt = f"""Analyze the technical setup for {name} ({ticker}).

=== PRICE DATA ===
{self._format_price_data(price_data)}

=== CALCULATED INDICATORS ===

RSI (14):
Value: {indicators.get('rsi', {}).get('value', 'N/A')}
Signal: {indicators.get('rsi', {}).get('signal', 'N/A')}
Interpretation: {indicators.get('rsi', {}).get('interpretation', 'N/A')}

Moving Averages:
{self._format_dict(indicators.get('moving_averages', {}))}

MACD:
{self._format_dict(indicators.get('macd', {}))}

Bollinger Bands:
{self._format_dict(indicators.get('bollinger', {}))}

Volume Analysis:
{self._format_dict(indicators.get('volume', {}))}

Support/Resistance Levels:
{self._format_dict(indicators.get('support_resistance', {}))}

Trend Analysis:
{self._format_dict(indicators.get('trend', {}))}

Max Drawdown (1Y): {indicators.get('max_drawdown', 'N/A')}%

Based on this technical data, provide:
1. Overall technical score (0-100)
2. Signal (BULLISH, BEARISH, NEUTRAL)
3. Confidence level (HIGH, MEDIUM, LOW)
4. Identified chart pattern (if any)
5. Entry zone, targets, and stop loss
6. Risk-reward ratio
7. Key observations (list 3-5)

Focus only on technical factors. Ignore fundamentals and news."""

        return prompt
    
    def _format_dict(self, d: Dict[str, Any]) -> str:
        """Format dictionary for prompt."""
        if not d:
            return "N/A"
        return "\n".join(f"  {k}: {v}" for k, v in d.items())
    
    def _get_fallback_response(self, error: str) -> Dict[str, Any]:
        """Get fallback response when analysis fails."""
        return {
            "score": 50,
            "signal": "NEUTRAL",
            "confidence": "LOW",
            "trend_analysis": {
                "short_term": "Unknown",
                "medium_term": "Unknown",
                "long_term": "Unknown",
                "overall_trend": "Unknown",
            },
            "trading_setup": {
                "pattern_identified": None,
                "entry_zone": [],
                "stop_loss": None,
            },
            "indicators": {},
            "support_resistance": {
                "immediate_resistance": [],
                "major_resistance": [],
                "immediate_support": [],
                "major_support": [],
            },
            "key_observations": [f"Analysis incomplete: {error}"],
        }
