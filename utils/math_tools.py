"""Math and financial calculation tools for agents."""

import numpy as np
from typing import List, Optional
from pydantic import BaseModel, Field


class CalculationResult(BaseModel):
    """Result of a calculation."""
    result: float
    formula: str
    interpretation: Optional[str] = None


def calculate_cagr(
    initial_value: float,
    final_value: float,
    years: float
) -> CalculationResult:
    """
    Calculate Compound Annual Growth Rate.
    
    CAGR = (Final/Initial)^(1/n) - 1
    """
    if initial_value <= 0 or years <= 0:
        return CalculationResult(
            result=0.0,
            formula="CAGR = (Final/Initial)^(1/n) - 1",
            interpretation="Invalid input values"
        )
    
    cagr = ((final_value / initial_value) ** (1 / years) - 1) * 100
    
    return CalculationResult(
        result=round(cagr, 2),
        formula=f"CAGR = ({final_value}/{initial_value})^(1/{years}) - 1",
        interpretation=f"{cagr:.2f}% annual growth rate"
    )


def calculate_pe_ratio(
    price: float,
    eps: float
) -> CalculationResult:
    """Calculate Price-to-Earnings ratio."""
    if eps <= 0:
        return CalculationResult(
            result=0.0,
            formula="PE = Price / EPS",
            interpretation="Negative or zero EPS"
        )
    
    pe = price / eps
    
    interpretation = "Expensive" if pe > 30 else "Moderate" if pe > 15 else "Cheap"
    
    return CalculationResult(
        result=round(pe, 2),
        formula=f"PE = {price} / {eps}",
        interpretation=f"PE of {pe:.2f} is considered {interpretation}"
    )


def calculate_fair_value_pe(
    eps: float,
    fair_pe: float
) -> CalculationResult:
    """Calculate fair value based on PE multiple."""
    fair_value = eps * fair_pe
    
    return CalculationResult(
        result=round(fair_value, 2),
        formula=f"Fair Value = EPS × Fair PE = {eps} × {fair_pe}",
        interpretation=f"Fair value estimate: ₹{fair_value:.2f}"
    )


def calculate_dcf_value(
    free_cash_flow: float,
    growth_rate: float,  # as percentage
    discount_rate: float,  # as percentage
    terminal_growth: float = 3.0,  # as percentage
    years: int = 5,
    shares_outstanding: float = 1.0
) -> CalculationResult:
    """
    Calculate intrinsic value using DCF model.
    
    Simple 2-stage DCF with terminal value.
    """
    g = growth_rate / 100
    r = discount_rate / 100
    tg = terminal_growth / 100
    
    # Project cash flows
    projected_cf = []
    cf = free_cash_flow
    pv_sum = 0
    
    for year in range(1, years + 1):
        cf = cf * (1 + g)
        pv = cf / ((1 + r) ** year)
        projected_cf.append(pv)
        pv_sum += pv
    
    # Terminal value
    terminal_cf = cf * (1 + tg)
    terminal_value = terminal_cf / (r - tg)
    pv_terminal = terminal_value / ((1 + r) ** years)
    
    total_value = pv_sum + pv_terminal
    per_share = total_value / shares_outstanding if shares_outstanding > 0 else total_value
    
    return CalculationResult(
        result=round(per_share, 2),
        formula=f"DCF with {growth_rate}% growth, {discount_rate}% discount, {terminal_growth}% terminal",
        interpretation=f"Intrinsic value: ₹{per_share:.2f} per share"
    )


def calculate_beta(
    stock_returns: List[float],
    market_returns: List[float]
) -> CalculationResult:
    """
    Calculate stock beta relative to market.
    
    Beta = Cov(stock, market) / Var(market)
    """
    if len(stock_returns) != len(market_returns) or len(stock_returns) < 2:
        return CalculationResult(
            result=1.0,
            formula="Beta = Cov(stock, market) / Var(market)",
            interpretation="Insufficient data, defaulting to beta of 1"
        )
    
    covariance = np.cov(stock_returns, market_returns)[0][1]
    market_variance = np.var(market_returns)
    
    if market_variance == 0:
        return CalculationResult(
            result=1.0,
            formula="Beta = Cov(stock, market) / Var(market)",
            interpretation="Zero market variance, defaulting to beta of 1"
        )
    
    beta = covariance / market_variance
    
    if beta > 1.5:
        interpretation = "High volatility - moves more than market"
    elif beta > 1:
        interpretation = "Moderate volatility - slightly more volatile than market"
    elif beta > 0.5:
        interpretation = "Low volatility - less volatile than market"
    else:
        interpretation = "Very low volatility - defensive stock"
    
    return CalculationResult(
        result=round(beta, 2),
        formula=f"Beta = {covariance:.4f} / {market_variance:.4f}",
        interpretation=interpretation
    )


def calculate_volatility(
    returns: List[float],
    annualize: bool = True
) -> CalculationResult:
    """
    Calculate historical volatility.
    
    Volatility = Std Dev of returns × √252 (annualized)
    """
    if len(returns) < 2:
        return CalculationResult(
            result=0.0,
            formula="Volatility = Std Dev × √252",
            interpretation="Insufficient data"
        )
    
    std_dev = np.std(returns)
    
    if annualize:
        volatility = std_dev * np.sqrt(252) * 100  # Annualized, as percentage
        formula = f"Volatility = {std_dev:.4f} × √252 × 100"
    else:
        volatility = std_dev * 100
        formula = f"Volatility = {std_dev:.4f} × 100"
    
    if volatility > 40:
        interpretation = "Very high volatility"
    elif volatility > 25:
        interpretation = "High volatility"
    elif volatility > 15:
        interpretation = "Moderate volatility"
    else:
        interpretation = "Low volatility"
    
    return CalculationResult(
        result=round(volatility, 2),
        formula=formula,
        interpretation=f"{volatility:.2f}% - {interpretation}"
    )


def calculate_sharpe_ratio(
    returns: List[float],
    risk_free_rate: float = 6.0  # Indian govt bond rate
) -> CalculationResult:
    """
    Calculate Sharpe Ratio.
    
    Sharpe = (Return - Risk Free) / Volatility
    """
    if len(returns) < 2:
        return CalculationResult(
            result=0.0,
            formula="Sharpe = (Return - Rf) / σ",
            interpretation="Insufficient data"
        )
    
    avg_return = np.mean(returns) * 252 * 100  # Annualized
    volatility = np.std(returns) * np.sqrt(252) * 100
    
    if volatility == 0:
        return CalculationResult(
            result=0.0,
            formula="Sharpe = (Return - Rf) / σ",
            interpretation="Zero volatility"
        )
    
    sharpe = (avg_return - risk_free_rate) / volatility
    
    if sharpe > 2:
        interpretation = "Excellent risk-adjusted returns"
    elif sharpe > 1:
        interpretation = "Good risk-adjusted returns"
    elif sharpe > 0:
        interpretation = "Acceptable risk-adjusted returns"
    else:
        interpretation = "Poor risk-adjusted returns"
    
    return CalculationResult(
        result=round(sharpe, 2),
        formula=f"Sharpe = ({avg_return:.2f}% - {risk_free_rate}%) / {volatility:.2f}%",
        interpretation=interpretation
    )


def calculate_max_drawdown(prices: List[float]) -> CalculationResult:
    """
    Calculate maximum drawdown.
    
    Max Drawdown = (Trough - Peak) / Peak
    """
    if len(prices) < 2:
        return CalculationResult(
            result=0.0,
            formula="MDD = (Trough - Peak) / Peak",
            interpretation="Insufficient data"
        )
    
    peak = prices[0]
    max_dd = 0
    
    for price in prices:
        if price > peak:
            peak = price
        drawdown = (peak - price) / peak
        if drawdown > max_dd:
            max_dd = drawdown
    
    max_dd_pct = max_dd * 100
    
    if max_dd_pct > 30:
        interpretation = "Severe drawdown risk"
    elif max_dd_pct > 20:
        interpretation = "Significant drawdown risk"
    elif max_dd_pct > 10:
        interpretation = "Moderate drawdown risk"
    else:
        interpretation = "Low drawdown risk"
    
    return CalculationResult(
        result=round(max_dd_pct, 2),
        formula="MDD = max((Peak - Current) / Peak)",
        interpretation=f"{max_dd_pct:.2f}% - {interpretation}"
    )


def calculate_position_size(
    portfolio_value: float,
    risk_per_trade: float,  # as percentage (e.g., 2%)
    entry_price: float,
    stop_loss: float
) -> CalculationResult:
    """
    Calculate position size based on risk.
    
    Position Size = (Portfolio × Risk%) / (Entry - Stop Loss)
    """
    risk_amount = portfolio_value * (risk_per_trade / 100)
    risk_per_share = abs(entry_price - stop_loss)
    
    if risk_per_share == 0:
        return CalculationResult(
            result=0.0,
            formula="Position = Risk Amount / Risk per Share",
            interpretation="Invalid stop loss"
        )
    
    shares = risk_amount / risk_per_share
    position_value = shares * entry_price
    position_pct = (position_value / portfolio_value) * 100
    
    return CalculationResult(
        result=int(shares),
        formula=f"Shares = {risk_amount:.0f} / {risk_per_share:.2f}",
        interpretation=f"{int(shares)} shares (₹{position_value:,.0f}, {position_pct:.1f}% of portfolio)"
    )


def calculate_risk_reward_ratio(
    entry: float,
    target: float,
    stop_loss: float
) -> CalculationResult:
    """Calculate risk-reward ratio."""
    risk = abs(entry - stop_loss)
    reward = abs(target - entry)
    
    if risk == 0:
        return CalculationResult(
            result=0.0,
            formula="R:R = Reward / Risk",
            interpretation="Invalid risk (zero)"
        )
    
    ratio = reward / risk
    
    if ratio >= 3:
        interpretation = "Excellent risk-reward"
    elif ratio >= 2:
        interpretation = "Good risk-reward"
    elif ratio >= 1:
        interpretation = "Acceptable risk-reward"
    else:
        interpretation = "Poor risk-reward - avoid"
    
    return CalculationResult(
        result=round(ratio, 2),
        formula=f"R:R = {reward:.2f} / {risk:.2f}",
        interpretation=f"1:{ratio:.1f} - {interpretation}"
    )


def calculate_rsi(prices: List[float], period: int = 14) -> CalculationResult:
    """Calculate Relative Strength Index."""
    if len(prices) < period + 1:
        return CalculationResult(
            result=50.0,
            formula="RSI = 100 - (100 / (1 + RS))",
            interpretation="Insufficient data"
        )
    
    # Calculate price changes
    changes = np.diff(prices)
    
    # Separate gains and losses
    gains = np.where(changes > 0, changes, 0)
    losses = np.where(changes < 0, -changes, 0)
    
    # Calculate average gain and loss
    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])
    
    if avg_loss == 0:
        rsi = 100.0
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    if rsi > 70:
        interpretation = "Overbought - potential reversal down"
    elif rsi < 30:
        interpretation = "Oversold - potential reversal up"
    else:
        interpretation = "Neutral"
    
    return CalculationResult(
        result=round(rsi, 2),
        formula=f"RSI({period}) = 100 - (100 / (1 + {avg_gain:.4f}/{avg_loss:.4f}))",
        interpretation=interpretation
    )
