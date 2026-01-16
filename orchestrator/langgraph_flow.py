"""LangGraph-based orchestration for stock analysis agents."""

import asyncio
from typing import TypedDict, Annotated, Literal, Optional, Any, Dict
from datetime import datetime,timezone

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from pydantic import BaseModel

from agents.schemas import (
    AgentState,
    FundamentalAnalysis,
    TechnicalAnalysis,
    MarketIntelAnalysis,
    RiskAnalysis,
    SynthesizedRecommendation,
)
from agents.fundamental_agent import FundamentalAgent
from agents.technical_agent import TechnicalAgent
from agents.market_intel_agent import MarketIntelAgent
from agents.risk_agent import RiskAgent
from agents.synthesizer_agent import SynthesizerAgent, ComparisonSynthesizerAgent
from data_collector.yahoo_finance import YahooFinanceCollector
from data_collector.news_scraper import NewsCollector
from data_collector.cache_manager import CacheManager
from orchestrator.intent_classifier import Intent, IntentType
from utils.logger import logger


class GraphState(TypedDict):
    """State for LangGraph workflow."""
    # Input
    ticker: str
    ticker_2: Optional[str]  # For comparison
    intent: IntentType
    user_id: Optional[str]
    
    # Data
    stock_data: Optional[Dict[str, Any]]
    stock_data_2: Optional[Dict[str, Any]]  # For comparison
    news_data: Optional[Dict[str, Any]]
    market_data: Optional[Dict[str, Any]]
    
    # Agent outputs
    fundamental_analysis: Optional[Dict[str, Any]]
    fundamental_analysis_2: Optional[Dict[str, Any]]  # For comparison
    technical_analysis: Optional[Dict[str, Any]]
    technical_analysis_2: Optional[Dict[str, Any]]  # For comparison
    market_intel_analysis: Optional[Dict[str, Any]]
    risk_analysis: Optional[Dict[str, Any]]
    synthesized_recommendation: Optional[Dict[str, Any]]
    
    # Metadata
    errors: list[str]
    progress: list[str]
    start_time: str
    execution_path: str


class StockAnalysisGraph:
    """LangGraph-based stock analysis orchestrator."""
    
    def __init__(self, cache_manager: Optional[CacheManager] = None):
        """Initialize the graph with agents and data collectors."""
        self.cache = cache_manager or CacheManager()
        self.yahoo_collector = YahooFinanceCollector()
        self.news_collector = NewsCollector()
        
        # Initialize agents
        self.fundamental_agent = FundamentalAgent()
        self.technical_agent = TechnicalAgent()
        self.market_intel_agent = MarketIntelAgent()
        self.risk_agent = RiskAgent()
        self.synthesizer_agent = SynthesizerAgent()
        self.comparison_agent = ComparisonSynthesizerAgent()
        
        # Build graphs for different execution paths
        self.price_graph = self._build_price_graph()
        self.single_aspect_graph = self._build_single_aspect_graph()
        self.full_analysis_graph = self._build_full_analysis_graph()
        self.comparison_graph = self._build_comparison_graph()
        self.deep_dive_graph = self._build_deep_dive_graph()
    
    def _build_price_graph(self) -> StateGraph:
        """Build graph for price check (fast path)."""
        graph = StateGraph(GraphState)
        
        graph.add_node("collect_price", self._collect_price_data)
        
        graph.set_entry_point("collect_price")
        graph.add_edge("collect_price", END)
        
        return graph.compile()
    
    def _build_single_aspect_graph(self) -> StateGraph:
        """Build graph for single aspect analysis."""
        graph = StateGraph(GraphState)
        
        graph.add_node("collect_data", self._collect_stock_data)
        graph.add_node("run_agent", self._run_single_agent)
        
        graph.set_entry_point("collect_data")
        graph.add_edge("collect_data", "run_agent")
        graph.add_edge("run_agent", END)
        
        return graph.compile()
    
    def _build_full_analysis_graph(self) -> StateGraph:
        """Build graph for full analysis with all agents."""
        graph = StateGraph(GraphState)
        
        # Data collection
        graph.add_node("collect_all_data", self._collect_all_data)
        
        # Parallel analysis agents
        graph.add_node("parallel_analysis", self._run_parallel_analysis)
        
        # Sequential agents
        graph.add_node("risk_analysis_node", self._run_risk_analysis)
        graph.add_node("synthesize", self._run_synthesis)
        
        # Define flow
        graph.set_entry_point("collect_all_data")
        graph.add_edge("collect_all_data", "parallel_analysis")
        graph.add_edge("parallel_analysis", "risk_analysis_node")
        graph.add_edge("risk_analysis_node", "synthesize")
        graph.add_edge("synthesize", END)
        
        return graph.compile()
    
    def _build_comparison_graph(self) -> StateGraph:
        """Build graph for comparing two stocks."""
        graph = StateGraph(GraphState)
        
        graph.add_node("collect_comparison_data", self._collect_comparison_data)
        graph.add_node("parallel_comparison_analysis", self._run_parallel_comparison_analysis)
        graph.add_node("synthesize_comparison", self._run_comparison_synthesis)
        
        graph.set_entry_point("collect_comparison_data")
        graph.add_edge("collect_comparison_data", "parallel_comparison_analysis")
        graph.add_edge("parallel_comparison_analysis", "synthesize_comparison")
        graph.add_edge("synthesize_comparison", END)
        
        return graph.compile()
    
    def _build_deep_dive_graph(self) -> StateGraph:
        """Build graph for comprehensive deep dive analysis."""
        # Same as full analysis but agents run in detailed mode
        return self._build_full_analysis_graph()
    
    # Node implementations
    async def _collect_price_data(self, state: GraphState) -> GraphState:
        """Collect only price data (fast path)."""
        try:
            ticker = state["ticker"]
            
            # Check cache first
            cached = await self.cache.get_price(ticker)
            if cached:
                state["stock_data"] = {"price_data": cached, "ticker": ticker}
                state["progress"].append("✅ Price data (cached)")
                return state
            
            # Fetch from API
            price_data = await self.yahoo_collector.get_quick_price(ticker)
            if price_data:
                state["stock_data"] = {"price_data": price_data, "ticker": ticker}
                state["progress"].append("✅ Price data fetched")
            else:
                state["errors"].append(f"Could not fetch price for {ticker}")
                
        except Exception as e:
            logger.error(f"Error collecting price data: {e}")
            state["errors"].append(f"Price fetch error: {str(e)}")
        
        return state
    
    async def _collect_stock_data(self, state: GraphState) -> GraphState:
        """Collect stock data for single aspect analysis."""
        try:
            ticker = state["ticker"]
            
            # Fetch stock data
            stock_data = await self.yahoo_collector.get_stock_data(ticker)
            if stock_data:
                state["stock_data"] = stock_data.model_dump()
                state["progress"].append("✅ Stock data collected")
            else:
                state["errors"].append(f"Could not fetch data for {ticker}")
                
        except Exception as e:
            logger.error(f"Error collecting stock data: {e}")
            state["errors"].append(f"Data collection error: {str(e)}")
        
        return state
    
    async def _collect_all_data(self, state: GraphState) -> GraphState:
        """Collect all data for full analysis."""
        try:
            ticker = state["ticker"]

            # FIXED: Fetch stock data ONCE with historical data included
            # Don't fetch twice - it's wasteful and causes data structure issues
            results = await asyncio.gather(
                self.yahoo_collector.get_stock_data(ticker, include_historical=True, historical_days=180),
                self.news_collector.get_news(ticker),
                self.yahoo_collector.get_market_data(),
                return_exceptions=True
            )

            stock_data, news_data, market_data = results

            # Process stock data
            if isinstance(stock_data, Exception):
                state["errors"].append(f"Stock data error: {str(stock_data)}")
            elif stock_data:
                state["stock_data"] = stock_data.model_dump()

                # Verify historical data is present for technical analysis
                hist_count = len(stock_data.price_data.historical_ohlcv) if stock_data.price_data else 0
                if hist_count > 0:
                    state["progress"].append(f"✅ Stock data collected ({hist_count} days historical)")
                else:
                    state["progress"].append("✅ Stock data collected (no historical)")
                    state["errors"].append("Warning: No historical data available for technical analysis")

            # Process news data
            if isinstance(news_data, Exception):
                state["errors"].append(f"News data error: {str(news_data)}")
            elif news_data:
                state["news_data"] = news_data.model_dump() if hasattr(news_data, 'model_dump') else news_data
                state["progress"].append("✅ News data collected")

            # Process market data
            if isinstance(market_data, Exception):
                state["errors"].append(f"Market data error: {str(market_data)}")
            elif market_data:
                state["market_data"] = market_data.model_dump()
                state["progress"].append("✅ Market data collected")

        except Exception as e:
            logger.error(f"Error in collect_all_data: {e}")
            import traceback
            logger.error(traceback.format_exc())
            state["errors"].append(f"Data collection error: {str(e)}")

        return state
    
    async def _collect_comparison_data(self, state: GraphState) -> GraphState:
        """Collect data for both stocks in comparison."""
        try:
            ticker1 = state["ticker"]
            ticker2 = state.get("ticker_2")

            if not ticker2:
                state["errors"].append("Second ticker required for comparison")
                return state

            # Parallel data collection for both stocks
            results = await asyncio.gather(
                self.yahoo_collector.get_stock_data(ticker1),
                self.yahoo_collector.get_stock_data(ticker2),
                return_exceptions=True
            )

            stock1, stock2 = results

            if not isinstance(stock1, Exception) and stock1:
                state["stock_data"] = stock1.model_dump()
                state["progress"].append(f"✅ {ticker1} data collected")
            else:
                state["errors"].append(f"Error fetching {ticker1}: {str(stock1)}")

            if not isinstance(stock2, Exception) and stock2:
                state["stock_data_2"] = stock2.model_dump()
                state["progress"].append(f"✅ {ticker2} data collected")
            else:
                state["errors"].append(f"Error fetching {ticker2}: {str(stock2)}")

        except Exception as e:
            logger.error(f"Error in comparison data collection: {e}")
            state["errors"].append(f"Comparison data error: {str(e)}")

        return state
    
    async def _run_single_agent(self, state: GraphState) -> GraphState:
        """Run a single agent based on intent."""
        try:
            intent = state["intent"]
            stock_data = state.get("stock_data")
            
            if not stock_data:
                state["errors"].append("No stock data available")
                return state
            
            if intent == IntentType.TECHNICAL_ANALYSIS:
                result = await self.technical_agent.analyze({
                    'stock_data': stock_data,
                    'ticker': state.get('ticker')})
                if result:
                    state["technical_analysis"] = result
                    state["progress"].append(f"✅ Technical: {result.get('score', 0)}/100")
                else:
                    state["errors"].append("Technical analysis failed")

            elif intent == IntentType.FUNDAMENTAL_ANALYSIS:
                result = await self.fundamental_agent.analyze({
                    'stock_data': stock_data,
                    'ticker': state.get('ticker')})
                if result:
                    state["fundamental_analysis"] = result
                    state["progress"].append(f"✅ Fundamental: {result.get('score', 0)}/100")
                else:
                    state["errors"].append("Fundamental analysis failed")
                
            elif intent == IntentType.SENTIMENT_ANALYSIS:
                news_data = state.get("news_data") or {}
                market_data = state.get("market_data") or {}
                ticker = state.get("ticker") or {}
                result = await self.market_intel_agent.analyze({
                    'stock_data': stock_data,
                    'news_data': news_data,
                    'market_data': market_data,
                    'ticker': ticker
                })
                if result:
                    state["market_intel_analysis"] = result
                    state["progress"].append(f"✅ Market Intel: {result.get('score', 0)}/100")
                else:
                    state["errors"].append("Market Intel analysis failed")

        except Exception as e:
            logger.error(f"Error in single agent: {e}")
            state["errors"].append(f"Analysis error: {str(e)}")
        
        return state
    
    async def _run_parallel_analysis(self, state: GraphState) -> GraphState:
        """Run fundamental, technical, and market intel agents in parallel."""
        try:
            stock_data = state.get("stock_data")
            news_data = state.get("news_data") or {}
            market_data = state.get("market_data") or {}
            
            if not stock_data:
                state["errors"].append("No stock data for analysis")
                return state
            
            # Run agents in parallel
            tasks = [
                self.fundamental_agent.analyze({'stock_data': stock_data,'ticker': state.get('ticker')}),
                self.technical_agent.analyze({'stock_data': stock_data,'ticker': state.get('ticker')}),
                self.market_intel_agent.analyze({'stock_data': stock_data,'news_data': news_data,'market_data': market_data,'ticker': state.get('ticker')}),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    agent_names = ["Fundamental", "Technical", "Market Intel"]
                    state["errors"].append(f"{agent_names[i]} agent error: {str(result)}")
                else:
                    if i == 0:
                        state["fundamental_analysis"] = result
                        state["progress"].append(f"✅ Fundamental: {result.get('score', 0)}/100")
                    elif i == 1:
                        state["technical_analysis"] = result
                        state["progress"].append(f"✅ Technical: {result.get('score', 0)}/100")
                    else:
                        state["market_intel_analysis"] = result
                        state["progress"].append(f"✅ Market Intel: {result.get('score', 0)}/100")
                        
        except Exception as e:
            logger.error(f"Error in parallel analysis: {e}")
            state["errors"].append(f"Parallel analysis error: {str(e)}")
        
        return state
    
    async def _run_parallel_comparison_analysis(self, state: GraphState) -> GraphState:
        """Run analysis for both stocks in comparison."""
        try:
            stock_data_1 = state.get("stock_data")
            stock_data_2 = state.get("stock_data_2")
            
            if not stock_data_1 or not stock_data_2:
                state["errors"].append("Missing stock data for comparison")
                return state
            
            # Run fundamental and technical for both stocks
            tasks = [
                self.fundamental_agent.analyze({'stock_data': stock_data_1,'ticker': state.get('ticker')}),
                self.technical_agent.analyze({'stock_data': stock_data_1,'ticker': state.get('ticker')}),
                self.fundamental_agent.analyze({'stock_data': stock_data_2,'ticker': state.get('ticker_2')}),
                self.technical_agent.analyze({'stock_data': stock_data_2,'ticker': state.get('ticker_2')}),
            ]
            
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            if not isinstance(results[0], Exception):
                state["fundamental_analysis"] = results[0]
                state["progress"].append(f"✅ {state['ticker']} Fundamental: {results[0].get('score', 0)}/100")
            if not isinstance(results[1], Exception):
                state["technical_analysis"] = results[1]
                state["progress"].append(f"✅ {state['ticker']} Technical: {results[1].get('score', 0)}/100")
            if not isinstance(results[2], Exception):
                state["fundamental_analysis_2"] = results[2]
                state["progress"].append(f"✅ {state.get('ticker_2')} Fundamental: {results[2].get('score', 0)}/100")
            if not isinstance(results[3], Exception):
                state["technical_analysis_2"] = results[3]
                state["progress"].append(f"✅ {state.get('ticker_2')} Technical: {results[3].get('score', 0)}/100")
                
        except Exception as e:
            logger.error(f"Error in comparison analysis: {e}")
            state["errors"].append(f"Comparison analysis error: {str(e)}")
        
        return state
    
    async def _run_risk_analysis(self, state: GraphState) -> GraphState:
        """Run risk calculator agent."""
        try:
            stock_data = state.get("stock_data")
            fundamental = state.get("fundamental_analysis")
            technical = state.get("technical_analysis")
            
            if not stock_data:
                state["errors"].append("No stock data for risk analysis")
                return state
            
            result = await self.risk_agent.analyze({
                "stock_data": stock_data,
                "fundamental_analysis": fundamental,
                "technical_analysis": technical,
                'ticker': state.get('ticker')
            })
            state["risk_analysis"] = result
            state["progress"].append(f"✅ Risk: {result.get('risk_score', 0)}/100")
            
        except Exception as e:
            logger.error(f"Error in risk analysis: {e}")
            state["errors"].append(f"Risk analysis error: {str(e)}")
        
        return state
    
    async def _run_synthesis(self, state: GraphState) -> GraphState:
        """Run synthesizer agent to generate final recommendation."""
        try:
            stock_data = state.get("stock_data")
            fundamental = state.get("fundamental_analysis")
            technical = state.get("technical_analysis")
            market_intel = state.get("market_intel_analysis")
            risk = state.get("risk_analysis")
            
            result = await self.synthesizer_agent.analyze(
                data={'stock_data': stock_data,
                'fundamental': fundamental,
                'technical': technical,
                'market_intel': market_intel,
                'risk': risk}
            )
            state["synthesized_recommendation"] = result
            state["progress"].append("✅ Recommendation generated")
            
        except Exception as e:
            logger.error(f"Error in synthesis: {e}")
            state["errors"].append(f"Synthesis error: {str(e)}")
        
        return state
    
    async def _run_comparison_synthesis(self, state: GraphState) -> GraphState:
        """Run comparison synthesizer."""
        try:
            result = await self.comparison_agent.compare(
                ticker1=state["ticker"],
                ticker2=state.get("ticker_2", ""),
                stock_data_1=state.get("stock_data"),
                stock_data_2=state.get("stock_data_2"),
                fundamental_1=state.get("fundamental_analysis"),
                fundamental_2=state.get("fundamental_analysis_2"),
                technical_1=state.get("technical_analysis"),
                technical_2=state.get("technical_analysis_2"),
            )
            state["synthesized_recommendation"] = result
            state["progress"].append("✅ Comparison complete")
            
        except Exception as e:
            logger.error(f"Error in comparison synthesis: {e}")
            state["errors"].append(f"Comparison error: {str(e)}")
        
        return state
    
    # Public interface
    async def run(
        self,
        intent: Intent,
        user_id: Optional[str] = None,
        progress_callback: Optional[callable] = None,
    ) -> GraphState:
        """
        Run the appropriate analysis graph based on intent.
        
        Args:
            intent: Classified user intent
            user_id: Optional user identifier
            progress_callback: Optional async callback for progress updates
            
        Returns:
            Final state with analysis results
        """
        # Initialize state
        initial_state: GraphState = {
            "ticker": intent.tickers[0] if intent.tickers else "",
            "ticker_2": intent.tickers[1] if len(intent.tickers) > 1 else None,
            "intent": intent.type,
            "user_id": user_id,
            "stock_data": None,
            "stock_data_2": None,
            "news_data": None,
            "market_data": None,
            "fundamental_analysis": None,
            "fundamental_analysis_2": None,
            "technical_analysis": None,
            "technical_analysis_2": None,
            "market_intel_analysis": None,
            "risk_analysis": None,
            "synthesized_recommendation": None,
            "errors": [],
            "progress": [],
            "start_time": datetime.now(timezone.utc).isoformat(),
            "execution_path": intent.type.value,
        }
        
        if not initial_state["ticker"]:
            initial_state["errors"].append("No ticker provided")
            return initial_state
        
        # Select appropriate graph
        graph_map = {
            IntentType.PRICE_CHECK: self.price_graph,
            IntentType.TECHNICAL_ANALYSIS: self.single_aspect_graph,
            IntentType.FUNDAMENTAL_ANALYSIS: self.single_aspect_graph,
            IntentType.SENTIMENT_ANALYSIS: self.single_aspect_graph,
            IntentType.FULL_ANALYSIS: self.full_analysis_graph,
            IntentType.COMPARISON: self.comparison_graph,
            IntentType.DEEP_DIVE: self.deep_dive_graph,
        }
        
        graph = graph_map.get(intent.type, self.full_analysis_graph)
        
        # Run the graph
        try:
            # For single aspect, need to collect news data for sentiment
            if intent.type == IntentType.SENTIMENT_ANALYSIS:
                initial_state = await self._collect_all_data(initial_state)
            
            final_state = await graph.ainvoke(initial_state)
            
            # Call progress callback if provided
            if progress_callback and final_state.get("progress"):
                for msg in final_state["progress"]:
                    await progress_callback(msg)
            
            return final_state
            
        except Exception as e:
            logger.error(f"Graph execution error: {e}")
            initial_state["errors"].append(f"Execution error: {str(e)}")
            return initial_state
