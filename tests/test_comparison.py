"""Test comparison analysis separately."""

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


def print_comparison_summary(result: dict):
    """Print detailed comparison summary."""
    print("\n" + "="*70)
    print("COMPARISON ANALYSIS SUMMARY")
    print("="*70)
    
    ticker1 = result.get('ticker')
    ticker2 = result.get('ticker_2')
    
    # Stock 1 Analysis
    fund1 = result.get('fundamental_analysis', {})
    tech1 = result.get('technical_analysis', {})
    
    print(f"\n📊 {ticker1}:")
    print(f"  Fundamental Score: {fund1.get('score', 'N/A')}/100")
    print(f"  Fundamental Rating: {fund1.get('rating', 'N/A')}")
    print(f"  Technical Score: {tech1.get('score', 'N/A')}/100")
    print(f"  Technical Signal: {tech1.get('signal', 'N/A')}")
    
    # Key metrics for stock 1
    if fund1:
        val1 = fund1.get('valuation', {})
        print(f"  PE Ratio: {val1.get('current_pe', 'N/A')}")
        print(f"  Fair Value: ₹{val1.get('fair_value', 'N/A')}")
        qual1 = fund1.get('quality_metrics', {})
        print(f"  ROE: {qual1.get('roe', 'N/A')}%")
    
    # Stock 2 Analysis
    fund2 = result.get('fundamental_analysis_2', {})
    tech2 = result.get('technical_analysis_2', {})
    
    print(f"\n📊 {ticker2}:")
    print(f"  Fundamental Score: {fund2.get('score', 'N/A')}/100")
    print(f"  Fundamental Rating: {fund2.get('rating', 'N/A')}")
    print(f"  Technical Score: {tech2.get('score', 'N/A')}/100")
    print(f"  Technical Signal: {tech2.get('signal', 'N/A')}")
    
    # Key metrics for stock 2
    if fund2:
        val2 = fund2.get('valuation', {})
        print(f"  PE Ratio: {val2.get('current_pe', 'N/A')}")
        print(f"  Fair Value: ₹{val2.get('fair_value', 'N/A')}")
        qual2 = fund2.get('quality_metrics', {})
        print(f"  ROE: {qual2.get('roe', 'N/A')}%")
    
    # Final Recommendation
    synth = result.get('synthesized_recommendation', {})
    if synth:
        print("\n" + "="*70)
        print("FINAL VERDICT")
        print("="*70)
        print(f"  Winner: {synth.get('winner', 'N/A')}")
        print(f"  Recommendation: {synth.get('recommendation', 'N/A')}")
        print(f"  Confidence: {synth.get('confidence', 0)}/100")
        
        reasoning = synth.get('reasoning', {})
        if reasoning:
            print(f"\n  Why {synth.get('winner', 'N/A')}:")
            for reason in reasoning.get('why_winner', [])[:3]:
                print(f"    • {reason}")
    
    # Errors
    errors = result.get('errors', [])
    if errors:
        print(f"\n⚠️  Errors: {errors}")
    
    print("\n" + "="*70)


async def test_comparison_tcs_vs_infy():
    """Test TCS vs Infosys comparison."""
    print("\n" + "="*70)
    print("TESTING: TCS vs INFOSYS COMPARISON")
    print("="*70)
    
    cache = CacheManager()
    graph = StockAnalysisGraph(cache_manager=cache)
    
    intent = Intent(
        type=IntentType.COMPARISON,
        tickers=["TCS.NS", "INFY.NS"],
        raw_query="compare TCS and Infosys"
    )
    
    progress_updates = []
    
    async def progress_callback(msg: str):
        progress_updates.append(msg)
        print(f"  📍 Progress: {msg}")
    
    try:
        print("\n🚀 Starting comparison analysis...")
        
        result = await graph.run(
            intent=intent,
            user_id="test_comparison",
            progress_callback=progress_callback
        )
        
        if result:
            print(f"\n✅ Comparison completed!")
            print(f"Progress updates: {len(progress_updates)}")
            
            # Print detailed summary
            print_comparison_summary(result)
            
            # Save results
            filename = save_results("comparison_tcs_infy", result)
            
            return result
        else:
            print("❌ Comparison returned None")
            return None
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_comparison_reliance_vs_ongc():
    """Test Reliance vs ONGC comparison (different sector)."""
    print("\n" + "="*70)
    print("TESTING: RELIANCE vs ONGC COMPARISON")
    print("="*70)
    
    cache = CacheManager()
    graph = StockAnalysisGraph(cache_manager=cache)
    
    intent = Intent(
        type=IntentType.COMPARISON,
        tickers=["RELIANCE.NS", "ONGC.NS"],
        raw_query="compare Reliance and ONGC"
    )
    
    try:
        print("\n🚀 Starting comparison analysis...")
        
        result = await graph.run(intent=intent, user_id="test_comparison")
        
        if result:
            print(f"\n✅ Comparison completed!")
            print_comparison_summary(result)
            save_results("comparison_reliance_ongc", result)
            return result
        else:
            print("❌ Comparison returned None")
            return None
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """Run comparison tests."""
    print("\n" + "="*70)
    print("STOCK COMPARISON ANALYSIS - STANDALONE TEST")
    print("="*70)
    
    # Test 1: Same sector comparison (IT)
    result1 = await test_comparison_tcs_vs_infy()
    
    # Test 2: Different sector comparison (Optional - uncomment to test)
    # result2 = await test_comparison_reliance_vs_ongc()
    
    # Summary
    print("\n" + "="*70)
    print("TEST SUMMARY")
    print("="*70)
    print(f"TCS vs INFY:     {'✅ PASS' if result1 else '❌ FAIL'}")
    # print(f"REL vs ONGC:     {'✅ PASS' if result2 else '❌ FAIL'}")
    
    print("\n📂 Check 'test_results/' folder for detailed JSON outputs")


if __name__ == "__main__":
    asyncio.run(main())