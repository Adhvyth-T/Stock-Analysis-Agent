"""Agent output schemas using Pydantic."""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime
from enum import Enum


class Rating(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"


class Signal(str, Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MODERATE = "MODERATE"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class Confidence(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# ============ Fundamental Analysis Schema ============

class Valuation(BaseModel):
    current_pe: Optional[float] = None
    sector_avg_pe: Optional[float] = None
    fair_pe: Optional[float] = None
    fair_value: Optional[float] = None
    upside_potential_percent: Optional[float] = None
    margin_of_safety: Optional[float] = None


class QualityMetrics(BaseModel):
    roe: Optional[float] = None
    roce: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    earnings_quality_score: Optional[int] = None


class GrowthMetrics(BaseModel):
    revenue_growth_3y_cagr: Optional[float] = None
    profit_growth_3y_cagr: Optional[float] = None
    growth_consistency_score: Optional[int] = None


class FinancialHealth(BaseModel):
    debt_to_equity: Optional[float] = None
    interest_coverage: Optional[float] = None
    current_ratio: Optional[float] = None
    free_cash_flow: Optional[float] = None
    balance_sheet_strength_score: Optional[int] = None


class PeerComparison(BaseModel):
    peer: str
    fundamental_score: Optional[int] = None
    pe_ratio: Optional[float] = None
    roe: Optional[float] = None


class FundamentalAnalysis(BaseModel):
    """Output schema for Fundamental Agent."""
    score: int = Field(ge=0, le=100, description="Overall fundamental score 0-100")
    rating: Rating
    recommendation: str  # UNDERVALUED, FAIRLY_VALUED, OVERVALUED
    valuation: Valuation
    quality_metrics: QualityMetrics
    growth_metrics: GrowthMetrics
    financial_health: FinancialHealth
    strengths: List[str] = []
    concerns: List[str] = []
    peer_comparison: List[PeerComparison] = []


# ============ Technical Analysis Schema ============

class TrendAnalysis(BaseModel):
    short_term: str  # Uptrend, Downtrend, Sideways
    medium_term: str
    long_term: str
    overall_trend: str


class TradingSetup(BaseModel):
    pattern_identified: Optional[str] = None
    pattern_reliability: Optional[str] = None  # High, Medium, Low
    entry_zone: List[float] = []
    target_1: Optional[float] = None
    target_2: Optional[float] = None
    target_3: Optional[float] = None
    stop_loss: Optional[float] = None
    risk_reward_ratio: Optional[float] = None
    time_horizon: Optional[str] = None


class IndicatorValue(BaseModel):
    value: float
    signal: str  # Bullish, Bearish, Neutral
    interpretation: str


class MovingAverages(BaseModel):
    ema_20: Optional[float] = None
    ema_50: Optional[float] = None
    ema_200: Optional[float] = None
    price_vs_ema20: Optional[str] = None
    price_vs_ema50: Optional[str] = None
    price_vs_ema200: Optional[str] = None


class Indicators(BaseModel):
    rsi_14: Optional[IndicatorValue] = None
    macd: Optional[Dict[str, Any]] = None
    moving_averages: Optional[MovingAverages] = None
    bollinger_bands: Optional[Dict[str, Any]] = None


class SupportResistance(BaseModel):
    immediate_resistance: List[float] = []
    major_resistance: List[float] = []
    immediate_support: List[float] = []
    major_support: List[float] = []


class VolumeAnalysis(BaseModel):
    current_volume: int
    avg_volume_20d: int
    volume_trend: str
    interpretation: str


class TechnicalAnalysis(BaseModel):
    """Output schema for Technical Agent."""
    score: int = Field(ge=0, le=100, description="Overall technical score 0-100")
    signal: Signal
    confidence: Confidence
    trend_analysis: TrendAnalysis
    trading_setup: TradingSetup
    indicators: Indicators
    support_resistance: SupportResistance
    volume_analysis: Optional[VolumeAnalysis] = None
    key_observations: List[str] = []


# ============ Market Intelligence Schema ============

class NewsAnalysisSummary(BaseModel):
    score: int
    sentiment: str
    article_count_7d: int
    positive_count: int
    neutral_count: int
    negative_count: int
    key_headlines: List[str] = []
    summary: str


class SocialSentiment(BaseModel):
    score: int
    sentiment: str
    trending_topics: List[str] = []
    influencer_sentiment: Optional[str] = None


class AnalystConsensus(BaseModel):
    score: int
    consensus: str  # BUY, HOLD, SELL
    total_analysts: int
    average_target_price: Optional[float] = None
    target_upside_percent: Optional[float] = None


class MarketContext(BaseModel):
    market_regime: str  # Bullish, Bearish, Volatile
    nifty_trend: str
    sector_performance: Dict[str, Any] = {}
    fii_activity: Optional[Dict[str, Any]] = None
    dii_activity: Optional[Dict[str, Any]] = None
    vix: Optional[Dict[str, Any]] = None


class Catalyst(BaseModel):
    event: str
    date: Optional[str] = None
    days_away: Optional[int] = None
    expected_impact: str  # High, Medium, Low

    
class MarketIntelAnalysis(BaseModel):
    """Output schema for Market Intelligence Agent."""
    score: int = Field(ge=0, le=100, description="Overall sentiment score 0-100")
    overall_sentiment: str  # POSITIVE, NEGATIVE, NEUTRAL
    sentiment_trend: str  # Improving, Stable, Declining
    news_analysis: NewsAnalysisSummary
    social_sentiment: Optional[SocialSentiment] = None
    analyst_consensus: Optional[AnalystConsensus] = None
    market_context: MarketContext
    catalysts: List[Catalyst] = []
    concerns: List[str] = []
    opportunities: List[str] = []


# ============ Risk Analysis Schema ============

class StockRiskMetrics(BaseModel):
    beta: float
    interpretation: str
    volatility_30d: float
    volatility_rating: str
    max_drawdown_1y: float
    max_drawdown_3y: Optional[float] = None
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None


class LiquidityAnalysis(BaseModel):
    avg_daily_volume: int
    avg_daily_value: float
    liquidity_rating: str  # Excellent, Good, Moderate, Poor
    impact_cost_10L: Optional[float] = None
    impact_cost_1Cr: Optional[float] = None


class PositionSizeRecommendation(BaseModel):
    percentage: str
    amount_range: List[float]
    shares: List[int]
    rationale: str


class PositionSizing(BaseModel):
    portfolio_value_assumed: float
    conservative: PositionSizeRecommendation
    moderate: PositionSizeRecommendation
    aggressive: PositionSizeRecommendation
    recommended: Dict[str, Any]


class ScenarioAnalysis(BaseModel):
    market_crash_minus20: Dict[str, Any]
    sector_correction_minus10: Dict[str, Any]
    stop_loss_triggered: Dict[str, Any]


class RiskFactor(BaseModel):
    factor: str
    severity: str  # Low, Medium, High
    description: str


class RiskAnalysis(BaseModel):
    """Output schema for Risk Agent."""
    risk_score: int = Field(ge=0, le=100, description="Risk score 0-100 (higher = riskier)")
    risk_rating: RiskLevel
    risk_level: str
    stock_risk_metrics: StockRiskMetrics
    liquidity_analysis: LiquidityAnalysis
    position_sizing: PositionSizing
    scenario_analysis: ScenarioAnalysis
    risk_factors: List[RiskFactor] = []
    risk_mitigation: List[str] = []


# ============ Synthesized Recommendation Schema ============

class Tranche(BaseModel):
    allocation: str
    price_range: List[float]
    timing: str


class Target(BaseModel):
    target_price: float
    gain_percent: float
    probability: int
    timeframe: str
    action: str


class StopLoss(BaseModel):
    price: float
    loss_percent: float
    type: str
    rationale: str


class ActionPlan(BaseModel):
    primary_action: str  # BUY, SELL, HOLD, WAIT, AVOID
    entry_strategy: str
    tranche_1: Optional[Tranche] = None
    tranche_2: Optional[Tranche] = None
    targets: List[Target] = []
    stop_loss: Optional[StopLoss] = None
    position_size: Dict[str, Any] = {}
    holding_period: str
    investment_type: str


class Reasoning(BaseModel):
    why_buy: List[str] = []
    key_concerns: List[str] = []
    what_could_go_wrong: List[str] = []
    why_confidence: List[str] = []


class ScoreBreakdown(BaseModel):
    fundamental_score: int
    technical_score: int
    market_intel_score: int
    risk_score: int
    weighted_average: float
    final_confidence: int


class SynthesizedRecommendation(BaseModel):
    """Output schema for Synthesizer Agent."""
    recommendation: str  # BUY, SELL, HOLD, WAIT, AVOID
    confidence: int = Field(ge=0, le=100)
    confidence_level: Confidence
    action_plan: ActionPlan
    reasoning: Reasoning
    score_breakdown: ScoreBreakdown
    agent_consensus: Dict[str, str] = {}
    monitoring_plan: Dict[str, List[str]] = {}
    user_suitability: Dict[str, str] = {}


# ============ LangGraph State Schema ============

class AgentState(BaseModel):
    """State schema for LangGraph orchestration."""
    # Input
    ticker: str
    intent: str  # price_check, single_aspect, full_analysis, comparison, deep_dive
    aspect: Optional[str] = None  # For single_aspect: fundamental, technical, sentiment
    compare_with: Optional[str] = None  # For comparison intent
    user_context: Dict[str, Any] = {}
    
    # Data collection
    stock_data: Optional[Dict[str, Any]] = None
    news_data: Optional[Dict[str, Any]] = None
    market_data: Optional[Dict[str, Any]] = None
    
    # Agent outputs
    fundamental_analysis: Optional[Dict[str, Any]] = None
    technical_analysis: Optional[Dict[str, Any]] = None
    market_intel_analysis: Optional[Dict[str, Any]] = None
    risk_analysis: Optional[Dict[str, Any]] = None
    final_recommendation: Optional[Dict[str, Any]] = None
    
    # Comparison data (for comparison intent)
    comparison_stock_data: Optional[Dict[str, Any]] = None
    comparison_fundamental: Optional[Dict[str, Any]] = None
    comparison_technical: Optional[Dict[str, Any]] = None
    
    # Execution tracking
    agents_completed: List[str] = []
    errors: List[str] = []
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    class Config:
        arbitrary_types_allowed = True
