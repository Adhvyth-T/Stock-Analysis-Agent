"""Response formatters for Telegram messages with proper HTML formatting."""

from typing import Dict, Any, Optional
from datetime import datetime

from utils.helpers import format_currency, format_percentage, format_large_number, is_market_open


class ResponseFormatter:
    """Formats analysis results for Telegram with HTML."""
    
    @staticmethod
    def format_price(data: Dict[str, Any]) -> str:
        """Format price check response."""
        price_data = data.get("price_data")
        ticker = data.get("ticker", "N/A")
        
        current_price = price_data.get("current_price", 0)
        change_percent = price_data.get("change_percent", 0)
        volume = price_data.get("volume", 0)
        day_high = price_data.get("day_high", 0)
        day_low = price_data.get("day_low", 0)
        prev_close = price_data.get("previous_close", 0)
        
        # Determine emoji based on change
        if change_percent > 0:
            change_emoji = "🟢"
            change_sign = "+"
        elif change_percent < 0:
            change_emoji = "🔴"
            change_sign = ""
        else:
            change_emoji = "⚪"
            change_sign = ""
        
        change_amount = current_price - prev_close if prev_close else 0
        market_status = "🟢 OPEN" if is_market_open()[0] else "🔴 CLOSED"
        
        return f"""💹 <b>{ticker}</b>

<b>Price:</b> {format_currency(current_price)} ({change_sign}{change_percent:.2f}%) {change_emoji}
<b>Change:</b> {change_sign}{format_currency(change_amount)}
<b>Volume:</b> {format_large_number(volume)}

<b>Day Range:</b> {format_currency(day_low)} - {format_currency(day_high)}
<b>Prev Close:</b> {format_currency(prev_close)}

Market: {market_status}
<i>Updated: {datetime.now().strftime('%I:%M %p IST')}</i>"""
    
    @staticmethod
    def format_full_analysis(state: Dict[str, Any]) -> str:
        """Format full analysis response."""
        ticker = state.get("ticker", "N/A")
        stock_data = state.get("stock_data") or {}
        recommendation = state.get("synthesized_recommendation") or {}
        fundamental = state.get("fundamental_analysis") or {}
        technical = state.get("technical_analysis") or {}
        market_intel = state.get("market_intel_analysis") or {}
        risk = state.get("risk_analysis") or {}
        
        # Get price info
        price_data = stock_data.get("price_data") or {}
        current_price = price_data.get("current_price", 0)
        change_percent = price_data.get("change_percent", 0)
        
        # Get recommendation info
        rec = recommendation.get("recommendation", "N/A")
        confidence = recommendation.get("confidence", 0)
        action_plan = recommendation.get("action_plan") or {}
        reasoning = recommendation.get("reasoning") or {}
        
        # Emoji mapping
        rec_emoji = {
            "BUY": "🟢",
            "STRONG_BUY": "🟢🟢",
            "HOLD": "🟡",
            "WAIT": "⏳",
            "AVOID": "🔴",
            "SELL": "🔴",
            "STRONG_SELL": "🔴🔴",
        }.get(rec, "❓")
        
        confidence = confidence or 0
        confidence_level = "High" if confidence >= 70 else "Medium" if confidence >= 50 else "Low"
        
        # Format scores
        fund_score = fundamental.get("score") if fundamental else 0
        tech_score = technical.get("score") if technical else 0
        intel_score = market_intel.get("score") if market_intel else 0
        risk_score = risk.get("risk_score") if risk else 0
        
        # Build response
        response = f"""📊 <b>{ticker}</b> Analysis

💰 <b>Price:</b> {format_currency(current_price)} ({change_percent:+.2f}%)

━━━━━━━━━━━━━━━━━━

{rec_emoji} <b>Recommendation: {rec}</b>
📈 <b>Confidence: {confidence}%</b> ({confidence_level})

━━━ <b>Scores</b> ━━━
💼 Fundamental: {fund_score}/100
📈 Technical: {tech_score}/100
📰 Market Intel: {intel_score}/100
⚠️ Risk: {risk_score}/100

"""
        
        # Add why buy/concerns
        why_reasons = reasoning.get("why_buy", []) or reasoning.get("why_hold", []) or reasoning.get("why_avoid", [])
        if why_reasons and isinstance(why_reasons, list):
            response += "━━━ <b>Key Points</b> ━━━\n"
            for reason in why_reasons[:3]:
                if reason:
                    response += f"• {reason}\n"
            response += "\n"
        
        concerns = reasoning.get("key_concerns", [])
        if concerns and isinstance(concerns, list):
            response += "⚠️ <b>Concerns:</b>\n"
            for concern in concerns[:2]:
                if concern:
                    response += f"• {concern}\n"
            response += "\n"
        
        # Add action plan if BUY
        if rec in ["BUY", "STRONG_BUY"] and action_plan:
            response += "━━━ <b>Action Plan</b> ━━━\n"

            # Entry zones from tranches
            tranche1 = action_plan.get("tranche_1")
            tranche2 = action_plan.get("tranche_2")

            if tranche1:
                price_range = tranche1.get("price_range", [])
                if price_range and len(price_range) == 2:
                    response += f"📊 Entry Zone 1: {format_currency(price_range[0])} - {format_currency(price_range[1])}\n"
                    response += f"   {tranche1.get('allocation', 'N/A')} - {tranche1.get('timing', '')}\n"

            if tranche2:
                price_range = tranche2.get("price_range", [])
                if price_range and len(price_range) == 2:
                    response += f"📊 Entry Zone 2: {format_currency(price_range[0])} - {format_currency(price_range[1])}\n"
                    response += f"   {tranche2.get('allocation', 'N/A')} - {tranche2.get('timing', '')}\n"

            # Targets
            targets = action_plan.get("targets", [])
            if targets and isinstance(targets, list):
                for i, target in enumerate(targets[:2], 1):
                    if isinstance(target, dict):
                        target_price = target.get("target_price")
                        if target_price:
                            gain = target.get("gain_percent", 0)
                            timeframe = target.get("timeframe", "N/A")
                            response += f"🎯 Target {i}: {format_currency(target_price)} (+{gain:.1f}% in {timeframe})\n"

            # Stop loss
            stop_loss = action_plan.get("stop_loss") or {}
            sl_price = stop_loss.get("price")
            if sl_price:
                loss_pct = stop_loss.get("loss_percent", 0)
                response += f"🛑 Stop Loss: {format_currency(sl_price)} (-{loss_pct:.1f}%)\n"

            response += "\n"
        
        # Position sizing
        if risk:
            position = risk.get("position_sizing", {})
            if position:
                recommended = position.get("recommended", {})
                if recommended:
                    pct = recommended.get('percentage', '0%')
                    shares = recommended.get('shares')
                    if isinstance(shares, list) and len(shares) == 2:
                        response += f"💰 <b>Position:</b> {pct} ({shares[0]}-{shares[1]} shares)\n"
                    elif isinstance(shares, int):
                        response += f"💰 <b>Position:</b> {pct} (~{shares} shares)\n"
                    else:
                        response += f"💰 <b>Position:</b> {pct}\n"

            # Holding period
            holding = action_plan.get("holding_period")
            if holding:
                response += f"⏳ <b>Holding Period:</b> {holding}\n"

            response += "\n"

        response += f"<i>Analysis time: {datetime.now().strftime('%I:%M %p IST')}</i>"
        
        return response
    
    @staticmethod
    def format_technical_analysis(state: Dict[str, Any]) -> str:
        """Format technical analysis response."""
        ticker = state.get("ticker", "N/A")
        technical = state.get("technical_analysis") or {}
        stock_data = state.get("stock_data") or {}
        
        price_data = stock_data.get("price_data") or {}
        current_price = price_data.get("current_price", 0)

        score = technical.get("score", 0)
        signal = technical.get("signal", "N/A")
        trend = technical.get("trend_analysis") or {}
        indicators = technical.get("indicators") or {}
        setup = technical.get("trading_setup") or {}
        support_resistance = technical.get("support_resistance") or {}
        observations = technical.get("key_observations", [])
        
        signal_emoji = {"BULLISH": "🟢", "BEARISH": "🔴", "NEUTRAL": "🟡"}.get(signal, "❓")
        
        response = f"""📈 <b>{ticker}</b> Technical Analysis

💰 <b>Price:</b> {format_currency(current_price)}
📊 <b>Score:</b> {score}/100
{signal_emoji} <b>Signal:</b> {signal}

━━━ <b>Trend Analysis</b> ━━━
Short-term: {trend.get('short_term', 'N/A')}
Medium-term: {trend.get('medium_term', 'N/A')}
Long-term: {trend.get('long_term', 'N/A')}

━━━ <b>Key Indicators</b> ━━━
"""
        
        # RSI
        rsi = indicators.get("rsi_14") or {}
        if rsi:
            response += f"RSI(14): {rsi.get('value', 'N/A')} - {rsi.get('signal', 'N/A')}\n"
        
        # MACD
        macd = indicators.get("macd") or {}
        if macd:
            response += f"MACD: {macd.get('signal', 'N/A')}\n"
        
        # Moving Averages
        ma = indicators.get("moving_averages") or {}
        if ma:
            response += f"vs EMA20: {ma.get('price_vs_ema20', 'N/A')}\n"
            response += f"vs EMA200: {ma.get('price_vs_ema200', 'N/A')}\n"
        
        response += "\n━━━ <b>Levels</b> ━━━\n"
        
        # Support/Resistance
        supports = support_resistance.get("immediate_support", [])
        resistances = support_resistance.get("immediate_resistance", [])
        
        if resistances:
            response += f"Resistance: {', '.join([format_currency(r) for r in resistances[:2]])}\n"
        if supports:
            response += f"Support: {', '.join([format_currency(s) for s in supports[:2]])}\n"
        
        # Trading setup
        if setup:
            response += f"\n━━━ <b>Trading Setup</b> ━━━\n"
            if setup.get("pattern_identified"):
                response += f"Pattern: {setup['pattern_identified']}\n"
            if setup.get("entry_zone"):
                entry = setup["entry_zone"]
                response += f"Entry: {format_currency(entry[0])} - {format_currency(entry[1])}\n"
            if setup.get("stop_loss"):
                response += f"Stop Loss: {format_currency(setup['stop_loss'])}\n"
            targets = [setup.get("target_1"), setup.get("target_2")]
            targets = [t for t in targets if t]
            if targets:
                response += f"Targets: {', '.join([format_currency(t) for t in targets])}\n"
        
        # Key observations
        if observations:
            response += "\n━━━ <b>Observations</b> ━━━\n"
            for obs in observations[:3]:
                response += f"• {obs}\n"
        
        return response
    
    @staticmethod
    def format_fundamental_analysis(state: Dict[str, Any]) -> str:
        """Format fundamental analysis response."""
        ticker = state.get("ticker", "N/A")
        fundamental = state.get("fundamental_analysis") or {}
        stock_data = state.get("stock_data") or {}
        
        price_data = stock_data.get("price_data") or {}
        current_price = price_data.get("current_price", 0)

        score = fundamental.get("score", 0)
        rating = fundamental.get("rating", "N/A")
        if rating == "NOT_APPLICABLE":
            return f"""💼 <b>{ticker}</b> Fundamental Analysis

💰 <b>Price:</b> {format_currency(current_price)}

⚠️ <b>Not Applicable</b>

This instrument (ETF/commodity/index) does not have traditional company fundamentals like earnings, P/E ratio, or balance sheet metrics.

For ETFs and commodities, consider:
- Underlying asset performance
- Expense ratio (for ETFs)
- Tracking error (for ETFs)
- Supply/demand dynamics (for commodities)
"""

        valuation = fundamental.get("valuation") or {}
        quality = fundamental.get("quality_metrics") or {}
        growth = fundamental.get("growth_metrics") or {}
        health = fundamental.get("financial_health") or {}
        strengths = fundamental.get("strengths", [])
        concerns = fundamental.get("concerns", [])
        
        rating_emoji = {
            "STRONG_BUY": "🟢🟢",
            "BUY": "🟢",
            "HOLD": "🟡",
            "SELL": "🔴",
            "STRONG_SELL": "🔴🔴",
        }.get(rating, "❓")
        
        response = f"""💼 <b>{ticker}</b> Fundamental Analysis

💰 <b>Price:</b> {format_currency(current_price)}
📊 <b>Score:</b> {score}/100
{rating_emoji} <b>Rating:</b> {rating}

━━━ <b>Valuation</b> ━━━
P/E Ratio: {valuation.get('current_pe', 'N/A')}
Fair Value: {format_currency(valuation.get('fair_value', 0))}
Upside: {valuation.get('upside_potential_percent', 0):.1f}%

━━━ <b>Quality Metrics</b> ━━━
ROE: {quality.get('roe', 'N/A')}%
ROCE: {quality.get('roce', 'N/A')}%
Net Margin: {quality.get('net_margin', 'N/A')}%

━━━ <b>Growth</b> ━━━
Revenue CAGR (3Y): {growth.get('revenue_growth_3y_cagr', 'N/A')}%
Profit CAGR (3Y): {growth.get('profit_growth_3y_cagr', 'N/A')}%

━━━ <b>Financial Health</b> ━━━
Debt/Equity: {health.get('debt_to_equity', 'N/A')}
Current Ratio: {health.get('current_ratio', 'N/A')}

"""
        
        if strengths:
            response += "━━━ <b>Strengths</b> ━━━\n"
            for s in strengths[:3]:
                response += f"✅ {s}\n"
            response += "\n"
        
        if concerns:
            response += "━━━ <b>Concerns</b> ━━━\n"
            for c in concerns[:2]:
                response += f"⚠️ {c}\n"
        
        return response
    
    @staticmethod
    def format_sentiment_analysis(state: Dict[str, Any]) -> str:
        """Format sentiment/market intel analysis response."""
        ticker = state.get("ticker", "N/A")
        market_intel = state.get("market_intel_analysis") or {}

        score = market_intel.get("score", 0)
        sentiment = market_intel.get("overall_sentiment", "N/A")
        news = market_intel.get("news_analysis") or {}
        social = market_intel.get("social_sentiment") or {}
        analyst = market_intel.get("analyst_consensus") or {}
        context = market_intel.get("market_context") or {}
        catalysts = market_intel.get("catalysts", [])
        concerns = market_intel.get("concerns", [])
        opportunities = market_intel.get("opportunities", [])

        sentiment_emoji = {
            "POSITIVE": "🟢",
            "NEGATIVE": "🔴",
            "NEUTRAL": "🟡",
        }.get(sentiment, "❓")

        response = f"""📰 <b>{ticker}</b> Market Intelligence

📊 <b>Score:</b> {score}/100
{sentiment_emoji} <b>Sentiment:</b> {sentiment}

━━━ <b>News Analysis</b> ━━━
News Score: {news.get('score', 'N/A')}/100
Articles (7d): {news.get('article_count_7d', 0)}
Positive: {news.get('positive_count', 0)} | Negative: {news.get('negative_count', 0)}

"""

        # Key headlines
        headlines = news.get("key_headlines", [])
        if headlines and isinstance(headlines, list):
            response += "📌 <b>Recent Headlines:</b>\n"
            for headline_item in headlines[:3]:
                if isinstance(headline_item, str):
                    # Handle string headlines
                    truncated = headline_item[:80] + "..." if len(headline_item) > 80 else headline_item
                    response += f"• {truncated}\n"
                elif isinstance(headline_item, dict):
                    # Handle dict headlines (extract headline field)
                    headline_text = headline_item.get("headline", "")
                    if headline_text:
                        truncated = headline_text[:80] + "..." if len(headline_text) > 80 else headline_text
                        response += f"• {truncated}\n"
            response += "\n"

        # Analyst consensus
        if analyst:
            avg_target = analyst.get('average_target_price')
            response += f"""━━━ <b>Analyst Consensus</b> ━━━
Rating: {analyst.get('consensus', 'N/A')}
"""
            if avg_target:
                response += f"Target Price: {format_currency(avg_target)}\n"
            response += f"Total Analysts: {analyst.get('total_analysts', 0)}\n\n"

        # Market context
        if context:
            fii = context.get("fii_activity") or {}
            dii = context.get("dii_activity") or {}
            vix = context.get("vix") or {}

            response += f"""━━━ <b>Market Context</b> ━━━
Market Regime: {context.get('market_regime', 'N/A')}
NIFTY Trend: {context.get('nifty_trend', 'N/A')}
"""
            if vix:
                response += f"VIX: {vix.get('value', 'N/A')} ({vix.get('trend', 'N/A')})\n"
            if fii:
                response += f"FII Activity: {fii.get('trend', 'N/A')}\n"
            if dii:
                response += f"DII Activity: {dii.get('trend', 'N/A')}\n"
            response += "\n"

        # Catalysts
        if catalysts and isinstance(catalysts, list):
            response += "━━━ <b>Upcoming Events</b> ━━━\n"
            for event in catalysts[:2]:
                if isinstance(event, str):
                    # Handle string events
                    response += f"📅 {event}\n"
                elif isinstance(event, dict):
                    # Handle dict events - extract fields safely
                    event_name = event.get('event', 'N/A')
                    event_date = event.get('date', '')
                    response += f"📅 {event_name}"
                    if event_date:
                        response += f" - {event_date}"
                    response += "\n"
            response += "\n"

        # Concerns
        if concerns and isinstance(concerns, list):
            response += "━━━ <b>Key Concerns</b> ━━━\n"
            for concern in concerns[:3]:
                if concern:
                    # Truncate long concerns
                    truncated = concern[:100] + "..." if len(concern) > 100 else concern
                    response += f"⚠️ {truncated}\n"
            response += "\n"

        # Opportunities
        if opportunities and isinstance(opportunities, list):
            response += "━━━ <b>Opportunities</b> ━━━\n"
            for opp in opportunities[:3]:
                if opp:
                    # Truncate long opportunities
                    truncated = opp[:100] + "..." if len(opp) > 100 else opp
                    response += f"✅ {truncated}\n"

        return response
    
    @staticmethod
    def format_comparison(state: Dict[str, Any]) -> str:
        """Format comparison analysis response."""
        ticker1 = state.get("ticker", "N/A")
        ticker2 = state.get("ticker_2", "N/A")
        recommendation = state.get("synthesized_recommendation") or {}

        fund1 = state.get("fundamental_analysis") or {}
        fund2 = state.get("fundamental_analysis_2") or {}
        tech1 = state.get("technical_analysis") or {}
        tech2 = state.get("technical_analysis_2") or {}

        stock1 = state.get("stock_data") or {}
        stock2 = state.get("stock_data_2") or {}
        
        price1 = (stock1.get("price_data") or {}).get("current_price", 0)
        price2 = (stock2.get("price_data") or {}).get("current_price", 0)
        
        winner = recommendation.get("winner", "")
        reasoning = recommendation.get("comparison_reasoning", [])
        
        response = f"""⚖️ <b>{ticker1} vs {ticker2}</b>

━━━━━━━━━━━━━━━━━━

📊 <b>{ticker1}</b>
Price: {format_currency(price1)}
Fundamental: {fund1.get('score', 0)}/100
Technical: {tech1.get('score', 0)}/100
Rating: {fund1.get('rating', 'N/A')}

📊 <b>{ticker2}</b>
Price: {format_currency(price2)}
Fundamental: {fund2.get('score', 0)}/100
Technical: {tech2.get('score', 0)}/100
Rating: {fund2.get('rating', 'N/A')}

━━━━━━━━━━━━━━━━━━

🏆 <b>Winner: {winner}</b>

"""
        
        if reasoning:
            response += "<b>Why:</b>\n"
            for r in reasoning[:3]:
                response += f"• {r}\n"
        
        return response
    
    @staticmethod
    def format_error(message: str) -> str:
        """Format error message."""
        return f"""❌ <b>Error</b>

{message}

Try <code>/help</code> for available commands."""
    
    @staticmethod
    def format_progress(messages: list[str]) -> str:
        """Format progress update."""
        return "\n".join(messages)