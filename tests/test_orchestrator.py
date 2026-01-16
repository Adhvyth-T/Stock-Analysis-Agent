"""Test LangGraph orchestrator workflow with detailed output."""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from orchestrator.intent_classifier import Intent, IntentType
from orchestrator.langgraph_flow import StockAnalysisGraph
from data_collector.cache_manager import CacheManager


def save_results(test_name: str, result: dict):
    """Save results to JSON file for inspection."""
    output_dir = Path("test_results")
    output_dir.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = output_dir / f"{test_name}_{timestamp}.json"
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, default=str)
    
    print(f"💾 Results saved to: {filename}")
    return filename


def print_agent_details(result: dict, agent_name: str, key: str):
    """Print detailed agent output."""
    data = result.get(key, {})
    
    if not data:
        print(f"  ❌ {agent_name}: NO DATA")
        return
    
    print(f"\n  {'='*60}")
    print(f"  {agent_name.upper()}")
    print(f"  {'='*60}")
    
    # Check for common fields
    if 'score' in data:
        print(f"  Score: {data['score']}/100")
    if 'rating' in data:
        print(f"  Rating: {data['rating']}")
    if 'signal' in data:
        print(f"  Signal: {data['signal']}")
    if 'recommendation' in data and agent_name != "Synthesizer":
        print(f"  Recommendation: {data['recommendation']}")
    if 'risk_score' in data:
        print(f"  Risk Score: {data['risk_score']}/100")
    if 'risk_rating' in data:
        print(f"  Risk Rating: {data['risk_rating']}")
    
    # Show first few keys to verify it's not fallback
    print(f"  Available keys: {list(data.keys())[:5]}...")
    
    # Check for specific indicators of real data
    if agent_name == "Fundamental":
        val = data.get('valuation', {})
        print(f"  PE Ratio: {val.get('current_pe', 'N/A')}")
        print(f"  Fair Value: {val.get('fair_value', 'N/A')}")
        
    elif agent_name == "Technical":
        trend = data.get('trend_analysis', {})
        print(f"  Overall Trend: {trend.get('overall_trend', 'N/A')}")
        setup = data.get('trading_setup', {})
        print(f"  Entry Zone: {setup.get('entry_zone', 'N/A')}")
        
    elif agent_name == "Market Intel":
        news = data.get('news_analysis', {})
        print(f"  Articles (7d): {news.get('article_count_7d', 0)}")
        print(f"  Sentiment: {data.get('overall_sentiment', 'N/A')}")
        
    elif agent_name == "Risk":
        metrics = data.get('stock_risk_metrics', {})
        print(f"  Beta: {metrics.get('beta', 'N/A')}")
        print(f"  Volatility: {metrics.get('volatility_30d', 'N/A')}%")


async def test_price_check():
    """Test fast path - price check only."""
    print("\n" + "="*60)
    print("TESTING: Price Check (Fast Path)")
    print("="*60)
    
    cache = CacheManager()
    graph = StockAnalysisGraph(cache_manager=cache)
    
    intent = Intent(
        type=IntentType.PRICE_CHECK,
        tickers=["TCS.NS"],
        raw_query="price of TCS"
    )
    
    try:
        result = await graph.run(intent=intent, user_id="test_user")
        
        print(f"✅ Execution completed")
        print(f"Ticker: {result.get('ticker')}")
        print(f"Price: ₹{result.get('stock_data', {}).get('price_data', {}).get('current_price')}")
        print(f"Errors: {result.get('errors', [])}")
        
        save_results("price_check", result)
        
        assert result.get('stock_data') is not None, "No stock data returned!"
        return result
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_fundamental_analysis():
    """Test single aspect - fundamental only."""
    print("\n" + "="*60)
    print("TESTING: Fundamental Analysis Only")
    print("="*60)
    
    cache = CacheManager()
    graph = StockAnalysisGraph(cache_manager=cache)
    
    intent = Intent(
        type=IntentType.FUNDAMENTAL_ANALYSIS,
        tickers=["TCS.NS"],
        raw_query="fundamental analysis of TCS"
    )
    
    try:
        result = await graph.run(intent=intent, user_id="test_user")
        
        print(f"✅ Execution completed")
        print_agent_details(result, "Fundamental", "fundamental_analysis")
        if result.get('fundamental_analysis', {}).get('score') == 0 and 'absence of' in result.get('fundamental_analysis', {}).get('recommendation', '').lower():
            print("  ⚠️ Detected fallback response!")
        print(f"\nErrors: {result.get('errors', [])}")
        
        save_results("fundamental_only", result)
        
        assert result.get('fundamental_analysis') is not None, "No fundamental analysis!"
        return result
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None
        
        

async def test_full_analysis():
    """Test full analysis - all agents."""
    print("\n" + "="*60)
    print("TESTING: Full Analysis (All Agents)")
    print("="*60)
    
    cache = CacheManager()
    graph = StockAnalysisGraph(cache_manager=cache)
    
    intent = Intent(
        type=IntentType.FULL_ANALYSIS,
        tickers=["TCS.NS"],
        raw_query="should I buy TCS"
    )
    
    progress_updates = []
    
    async def progress_callback(msg: str):
        progress_updates.append(msg)
        print(f"  Progress: {msg}")
    
    try:
        result = await graph.run(
            intent=intent,
            user_id="test_user",
            progress_callback=progress_callback
        )
        
        if result:
            print(f"\n✅ Execution completed")
            print(f"Progress updates: {len(progress_updates)}")
            
            # Detailed output for each agent
            print_agent_details(result, "Fundamental", "fundamental_analysis")
            print_agent_details(result, "Technical", "technical_analysis")
            print_agent_details(result, "Market Intel", "market_intel_analysis")
            print_agent_details(result, "Risk", "risk_analysis")
            
            # Final recommendation
            synth = result.get('synthesized_recommendation', {})
            if synth:
                print(f"\n  {'='*60}")
                print(f"  FINAL RECOMMENDATION")
                print(f"  {'='*60}")
                print(f"  Action: {synth.get('recommendation', 'N/A')}")
                print(f"  Confidence: {synth.get('confidence', 0)}/100")
                print(f"  Confidence Level: {synth.get('confidence_level', 'N/A')}")
                
                action_plan = synth.get('action_plan', {})
                if action_plan:
                    print(f"  Primary Action: {action_plan.get('primary_action', 'N/A')}")
            
            print(f"\n  Errors: {result.get('errors', [])}")
            
            # Save to file
            filename = save_results("full_analysis", result)
            
            # Validate
            assert result.get('fundamental_analysis') is not None, "No fundamental analysis!"
            assert result.get('technical_analysis') is not None, "No technical analysis!"
            assert result.get('synthesized_recommendation') is not None, "No recommendation!"
            
            return result
        else:
            print("❌ Test returned None")
            return None
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_comparison():
    """Test comparison analysis."""
    print("\n" + "="*60)
    print("TESTING: Comparison Analysis")
    print("="*60)
    
    cache = CacheManager()
    graph = StockAnalysisGraph(cache_manager=cache)
    
    intent = Intent(
        type=IntentType.COMPARISON,
        tickers=["TCS.NS", "INFY.NS"],
        raw_query="compare TCS and Infosys"
    )
    
    try:
        result = await graph.run(intent=intent, user_id="test_user")
        
        print(f"✅ Execution completed")
        print(f"Stock 1 Score: {result.get('fundamental_analysis', {}).get('score')}")
        print(f"Stock 2 Score: {result.get('fundamental_analysis_2', {}).get('score')}")
        print(f"Winner: {result.get('synthesized_recommendation', {}).get('winner')}")
        print(f"Errors: {result.get('errors', [])}")
        
        save_results("comparison", result)
        
        return result
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_orchestrator():
    """Test all orchestrator workflows."""
    print("\n" + "="*70)
    print("PHASE 2: TESTING LANGGRAPH ORCHESTRATOR")
    print("="*70)
    
    results = {
        "price_check": await test_price_check(),
        "fundamental_only": await test_fundamental_analysis(),
        "full_analysis": await test_full_analysis(),
        # "comparison": await test_comparison(),  # Uncomment if you want to test this
    }
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result is not None else "❌ FAIL"
        errors = len(result.get('errors', [])) if result else 'N/A'
        print(f"{test_name:20} {status:10} Errors: {errors}")
    
    print("\n📂 Check 'test_results/' folder for detailed JSON outputs")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_orchestrator())