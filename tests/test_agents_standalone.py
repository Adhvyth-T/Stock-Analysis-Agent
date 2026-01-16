"""Test individual agents with mock data."""

import asyncio
import json
from pathlib import Path

# Mock data for testing
MOCK_STOCK_DATA = {
    "ticker": "TCS.NS",
    "name": "Tata Consultancy Services",
    "price_data": {
        "current_price": 3850.50,
        "change_percent": 1.25,
        "volume": 2500000,
        "day_high": 3870.00,
        "day_low": 3830.00,
        "previous_close": 3803.00,
        "52_week_high": 4050.00,
        "52_week_low": 3200.00,
    },
    "fundamental_data": {
        "market_cap": 14000000000000,
        "pe_ratio": 28.5,
        "pb_ratio": 12.8,
        "eps": 135.2,
        "dividend_yield": 1.8,
        "roe": 45.2,
        "roce": 52.3,
        "debt_to_equity": 0.02,
        "current_ratio": 2.8,
        "book_value": 300.5,
        "industry": "IT Services",
        "sector": "Information Technology",
        "quarterly_results": {
            "revenue": 590000000000,
            "revenue_growth_yoy": 14.5,
            "net_profit": 125000000000,
            "profit_growth_yoy": 12.8,
            "operating_margin": 25.5,
            "net_margin": 21.2,
        }
    },
    "ownership_data": {
        "promoter_holding": 72.05,
        "fii_holding": 12.50,
        "dii_holding": 8.25,
        "public_holding": 7.20,
        "pledged_shares": 0.0,
    },
    "corporate_actions": []
}


async def test_fundamental_agent():
    """Test Fundamental Agent."""
    print("\n" + "="*60)
    print("TESTING: Fundamental Agent")
    print("="*60)
    
    try:
        from agents.fundamental_agent import FundamentalAgent
        
        agent = FundamentalAgent()
        result = await agent.analyze({"stock_data": MOCK_STOCK_DATA})
        
        print(f"✅ Agent executed successfully")
        print(f"\nScore: {result.get('score')}")
        print(f"Rating: {result.get('rating')}")
        print(f"Recommendation: {result.get('recommendation')}")
        
        # Validate required fields
        assert result.get('score') is not None, "Score is None!"
        assert isinstance(result.get('score'), int), "Score is not an integer!"
        assert 0 <= result.get('score') <= 100, "Score out of range!"
        
        valuation = result.get('valuation', {})
        print(f"\nValuation:")
        print(f"  Fair Value: {valuation.get('fair_value')}")
        print(f"  Upside: {valuation.get('upside_potential_percent')}%")
        
        print(f"\n✅ All assertions passed!")
        return result
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_technical_agent():
    """Test Technical Agent."""
    print("\n" + "="*60)
    print("TESTING: Technical Agent")
    print("="*60)
    
    try:
        from agents.technical_agent import TechnicalAgent
        
        agent = TechnicalAgent()
        result = await agent.analyze({"stock_data": MOCK_STOCK_DATA})
        
        print(f"✅ Agent executed successfully")
        print(f"\nScore: {result.get('score')}")
        print(f"Signal: {result.get('signal')}")
        print(f"Confidence: {result.get('confidence')}")
        
        # Validate
        assert result.get('score') is not None, "Score is None!"
        assert isinstance(result.get('score'), int), "Score is not an integer!"
        
        print(f"\n✅ All assertions passed!")
        return result
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_market_intel_agent():
    """Test Market Intelligence Agent."""
    print("\n" + "="*60)
    print("TESTING: Market Intelligence Agent")
    print("="*60)
    
    try:
        from agents.market_intel_agent import MarketIntelAgent
        
        agent = MarketIntelAgent()
        result = await agent.analyze({
            "stock_data": MOCK_STOCK_DATA,
            "news_data": None,  # Will use fallback
        })
        
        print(f"✅ Agent executed successfully")
        print(f"\nScore: {result.get('score')}")
        print(f"Sentiment: {result.get('overall_sentiment')}")
        
        # Validate
        assert result.get('score') is not None, "Score is None!"
        
        print(f"\n✅ All assertions passed!")
        return result
        
    except Exception as e:
        print(f"❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return None


async def test_all_agents():
    """Test all agents sequentially."""
    print("\n" + "="*70)
    print("PHASE 1: TESTING INDIVIDUAL AGENTS")
    print("="*70)
    
    results = {
        "fundamental": await test_fundamental_agent(),
        "technical": await test_technical_agent(),
        "market_intel": await test_market_intel_agent(),
    }
    
    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    
    for agent_name, result in results.items():
        status = "✅ PASS" if result is not None else "❌ FAIL"
        score = result.get('score', 'N/A') if result else 'N/A'
        print(f"{agent_name:20} {status:10} Score: {score}")
    
    # Save results for inspection
    output_file = Path("agent_test_results.json")  # Save in current directory
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n📁 Results saved to: {output_file.absolute()}")
    
    return results


if __name__ == "__main__":
    asyncio.run(test_all_agents())