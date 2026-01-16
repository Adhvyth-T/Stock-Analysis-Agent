"""Complete Yahoo Finance data collector with caching and rate limiting."""

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from loguru import logger
import asyncio
import json
import hashlib
from functools import wraps
import time

from .schemas import (
    StockData,
    PriceData,
    FundamentalData,
    OwnershipData,
    HistoricalOHLCV,
    CorporateAction,
    QuarterlyResults,
    MarketData,
)

try:
    from config.settings import settings
    REDIS_URL = getattr(settings, 'REDIS_URL', None)
except:
    REDIS_URL = None

try:
    import redis.asyncio as redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logger.warning("Redis not available, using in-memory cache only")


class InMemoryCache:
    """Simple in-memory cache as fallback."""
    
    def __init__(self):
        self._cache: Dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key in self._cache:
                value, expiry = self._cache[key]
                if time.time() < expiry:
                    return value
                del self._cache[key]
            return None
    
    async def set(self, key: str, value: str, ex: int = 300):
        async with self._lock:
            self._cache[key] = (value, time.time() + ex)
    
    async def delete(self, key: str):
        async with self._lock:
            self._cache.pop(key, None)
    
    async def incr(self, key: str) -> int:
        async with self._lock:
            if key in self._cache:
                val, expiry = self._cache[key]
                if time.time() < expiry:
                    new_val = int(val) + 1
                    self._cache[key] = (str(new_val), expiry)
                    return new_val
            self._cache[key] = ("1", time.time() + 60)
            return 1
    
    async def expire(self, key: str, seconds: int):
        async with self._lock:
            if key in self._cache:
                value, _ = self._cache[key]
                self._cache[key] = (value, time.time() + seconds)
    
    async def close(self):
        """Close cache (no-op for in-memory)."""
        pass


class RateLimiter:
    """Rate limiter with exponential backoff."""
    
    def __init__(self, cache, max_requests: int = 100, window: int = 3600):
        self.cache = cache
        self.max_requests = max_requests
        self.window = window
        self._local_count = 0
        self._local_reset_time = time.time() + window
    
    async def check_limit(self, key: str = "yfinance:global") -> tuple[bool, int]:
        try:
            # Use local counter as primary check
            if time.time() > self._local_reset_time:
                self._local_count = 0
                self._local_reset_time = time.time() + self.window
            
            if self._local_count >= self.max_requests:
                wait_time = int(self._local_reset_time - time.time())
                return False, wait_time
            
            self._local_count += 1
            
            # Also track in cache
            count_key = f"{key}:count"
            try:
                count = await self.cache.incr(count_key)
                if count == 1:
                    await self.cache.expire(count_key, self.window)
                if count > self.max_requests:
                    return False, self.window
            except Exception:
                pass
            
            return True, 0
        except Exception as e:
            logger.error(f"Rate limit check error: {e}")
            return True, 0


def with_retry_and_cache(cache_ttl: int = 300):
    """Decorator for caching and retries."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            # Generate cache key
            cache_key = f"yf:{func.__name__}:{hashlib.md5(str(args).encode()).hexdigest()}"
            
            # Try cache first
            if self.cache:
                try:
                    cached = await self.cache.get(cache_key)
                    if cached:
                        logger.debug(f"Cache hit for {cache_key}")
                        # For get_stock_data, need to deserialize to StockData
                        if func.__name__ == 'get_stock_data':
                            data = json.loads(cached)
                            return StockData(**data) if data else None
                        elif func.__name__ == 'get_market_data':
                            data = json.loads(cached)
                            return MarketData(**data) if data else MarketData()
                        else:
                            return json.loads(cached)
                except Exception as e:
                    logger.warning(f"Cache get error: {e}")
            
            # Check rate limit
            if self.rate_limiter:
                allowed, wait_seconds = await self.rate_limiter.check_limit()
                if not allowed:
                    logger.warning(f"Rate limit hit, waiting {wait_seconds}s")
                    await asyncio.sleep(min(wait_seconds, 60))
            
            # Execute with retries
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    result = await func(self, *args, **kwargs)
                    
                    # Cache the result
                    if result is not None and self.cache:
                        try:
                            # Serialize StockData and MarketData objects
                            if isinstance(result, (StockData, MarketData)):
                                cache_data = result.dict()
                            else:
                                cache_data = result
                            
                            await self.cache.set(
                                cache_key,
                                json.dumps(cache_data, default=str),
                                ex=cache_ttl
                            )
                        except Exception as e:
                            logger.warning(f"Cache set error: {e}")
                    
                    return result
                    
                except Exception as e:
                    error_str = str(e)
                    
                    if "429" in error_str or "Too Many Requests" in error_str:
                        if attempt < max_retries - 1:
                            wait_time = 2 ** attempt * 5
                            logger.warning(f"Rate limited, waiting {wait_time}s...")
                            await asyncio.sleep(wait_time)
                            continue
                    
                    if "Expecting value" in error_str or "JSONDecodeError" in error_str:
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2 ** attempt)
                            continue
                    
                    if attempt == max_retries - 1:
                        logger.error(f"Failed after {max_retries} attempts: {e}")
                        raise
                    
                    await asyncio.sleep(2 ** attempt)
            
            return None
            
        return wrapper
    return decorator


class YahooFinanceCollector:
    """Complete Yahoo Finance data collector with caching and rate limiting."""
    
    def __init__(
        self,
        redis_url: Optional[str] = None,
        max_requests_per_hour: int = 100
    ):
        self.redis_url = redis_url or REDIS_URL
        self.cache = None
        self.rate_limiter = None
        self._initialized = False
        self.max_requests_per_hour = max_requests_per_hour
    
    async def initialize(self):
        """Initialize cache and rate limiter."""
        if self._initialized:
            return
        
        # Setup cache
        if REDIS_AVAILABLE and self.redis_url:
            try:
                self.cache = await redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                logger.info("✅ Connected to Redis cache")
            except Exception as e:
                logger.warning(f"Redis connection failed: {e}, using in-memory cache")
                self.cache = InMemoryCache()
        else:
            self.cache = InMemoryCache()
            logger.info("Using in-memory cache")
        
        # Setup rate limiter
        self.rate_limiter = RateLimiter(
            self.cache,
            max_requests=self.max_requests_per_hour,
            window=3600
        )
        
        self._initialized = True
    
    async def close(self):
        """Close connections."""
        if self.cache:
            await self.cache.close()
    
    @with_retry_and_cache(cache_ttl=600)  # 10 minutes for full data
    async def get_stock_data(
        self,
        ticker: str,
        include_historical: bool = True,
        historical_days: int = 365
    ) -> Optional[StockData]:
        """
        Fetch comprehensive stock data with caching.
        
        Args:
            ticker: Stock ticker symbol (e.g., 'RELIANCE.NS')
            include_historical: Whether to include historical data
            historical_days: Number of days of historical data
            
        Returns:
            StockData object or None if fetch fails
        """
        await self.initialize()
        
        try:
            logger.info(f"Fetching data for {ticker}")
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
            info = await loop.run_in_executor(None, lambda: stock.info)
            
            if not info or ('currentPrice' not in info and 'regularMarketPrice' not in info and 'previousClose' not in info):
                logger.warning(f"No price data found for {ticker}")
                return None
            
            # Get price data
            price_data = await self._extract_price_data(stock, info, include_historical, historical_days)
            
            # Get fundamental data
            fundamental_data = self._extract_fundamental_data(info)
            
            # Get ownership data
            ownership_data = await self._extract_ownership_data(stock)
            
            # Get corporate actions
            corporate_actions = await self._extract_corporate_actions(stock)
            
            return StockData(
                ticker=ticker,
                name=info.get('longName', info.get('shortName', ticker)),
                timestamp=datetime.now(),
                price_data=price_data,
                fundamental_data=fundamental_data,
                ownership_data=ownership_data,
                corporate_actions=corporate_actions,
            )
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None
    
    async def _extract_price_data(
        self,
        stock: yf.Ticker,
        info: dict,
        include_historical: bool,
        historical_days: int
    ) -> PriceData:
        """Extract price-related data."""
        
        current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
        previous_close = info.get('previousClose', current_price)
        
        change = current_price - previous_close
        change_percent = (change / previous_close * 100) if previous_close else 0
        
        historical = []
        if include_historical:
            historical = await self._get_historical_data(stock, historical_days)
        
        return PriceData(
            current_price=current_price,
            change_percent=round(change_percent, 2),
            change_absolute=round(change, 2),
            volume=info.get('volume', 0) or 0,
            previous_close=previous_close,
            day_high=info.get('dayHigh', current_price) or current_price,
            day_low=info.get('dayLow', current_price) or current_price,
            **{"52_week_high": info.get('fiftyTwoWeekHigh', 0) or 0},
            **{"52_week_low": info.get('fiftyTwoWeekLow', 0) or 0},
            avg_volume=info.get('averageVolume', 0) or 0,
            historical_ohlcv=historical,
        )
    
    async def _get_historical_data(
        self,
        stock: yf.Ticker,
        days: int
    ) -> List[HistoricalOHLCV]:
        """Get historical OHLCV data."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Run in thread pool
            loop = asyncio.get_event_loop()
            hist = await loop.run_in_executor(
                None,
                lambda: stock.history(start=start_date, end=end_date)
            )
            
            if hist.empty:
                return []
            
            historical = []
            for date, row in hist.iterrows():
                historical.append(HistoricalOHLCV(
                    date=date.strftime('%Y-%m-%d'),
                    open=round(row['Open'], 2),
                    high=round(row['High'], 2),
                    low=round(row['Low'], 2),
                    close=round(row['Close'], 2),
                    volume=int(row['Volume']),
                ))
            
            return historical
            
        except Exception as e:
            logger.warning(f"Could not fetch historical data: {e}")
            return []
    
    def _extract_fundamental_data(self, info: dict) -> FundamentalData:
        """Extract fundamental financial data."""
        
        quarterly = None
        try:
            revenue = info.get('totalRevenue', 0) or 0
            net_income = info.get('netIncomeToCommon', 0) or 0
            
            if revenue > 0:
                quarterly = QuarterlyResults(
                    revenue=revenue,
                    revenue_growth_yoy=info.get('revenueGrowth', 0) or 0,
                    net_profit=net_income,
                    profit_growth_yoy=info.get('earningsGrowth', 0) or 0,
                    operating_margin=(info.get('operatingMargins', 0) or 0) * 100,
                    net_margin=(info.get('profitMargins', 0) or 0) * 100,
                )
        except Exception:
            pass
        
        return FundamentalData(
            market_cap=info.get('marketCap', 0) or 0,
            pe_ratio=info.get('trailingPE'),
            pb_ratio=info.get('priceToBook'),
            eps=info.get('trailingEps'),
            dividend_yield=(info.get('dividendYield', 0) or 0) * 100,
            roe=(info.get('returnOnEquity', 0) or 0) * 100 if info.get('returnOnEquity') else None,
            roce=None,
            debt_to_equity=info.get('debtToEquity', 0) / 100 if info.get('debtToEquity') else None,
            current_ratio=info.get('currentRatio'),
            book_value=info.get('bookValue'),
            face_value=None,
            industry=info.get('industry', ''),
            sector=info.get('sector', ''),
            quarterly_results=quarterly,
        )
    
    async def _extract_ownership_data(self, stock: yf.Ticker) -> OwnershipData:
        """Extract shareholding pattern."""
        try:
            loop = asyncio.get_event_loop()
            holders = await loop.run_in_executor(None, lambda: stock.major_holders)
            
            if holders is None or holders.empty:
                return OwnershipData()
            
            insider = 0.0
            institutions = 0.0
            
            for idx, row in holders.iterrows():
                value_str = str(row.iloc[0]).replace('%', '')
                try:
                    value = float(value_str)
                except ValueError:
                    continue
                    
                description = str(row.iloc[1]).lower() if len(row) > 1 else ""
                
                if 'insider' in description:
                    insider = value
                elif 'institution' in description:
                    institutions = value
            
            return OwnershipData(
                promoter_holding=insider,
                fii_holding=institutions * 0.6,
                dii_holding=institutions * 0.4,
                public_holding=max(0, 100 - insider - institutions),
                pledged_shares=0.0,
            )
            
        except Exception as e:
            logger.warning(f"Could not fetch ownership data: {e}")
            return OwnershipData()
    
    async def _extract_corporate_actions(self, stock: yf.Ticker) -> List[CorporateAction]:
        """Extract recent corporate actions."""
        actions = []
        
        try:
            loop = asyncio.get_event_loop()
            
            # Dividends
            dividends = await loop.run_in_executor(None, lambda: stock.dividends)
            if dividends is not None and not dividends.empty:
                recent_dividends = dividends.tail(5)
                for date, amount in recent_dividends.items():
                    actions.append(CorporateAction(
                        type="dividend",
                        amount=float(amount),
                        ex_date=date.strftime('%Y-%m-%d'),
                    ))
            
            # Splits
            splits = await loop.run_in_executor(None, lambda: stock.splits)
            if splits is not None and not splits.empty:
                recent_splits = splits.tail(3)
                for date, ratio in recent_splits.items():
                    if ratio != 1.0:
                        actions.append(CorporateAction(
                            type="split",
                            ratio=f"1:{int(ratio)}",
                            ex_date=date.strftime('%Y-%m-%d'),
                        ))
                        
        except Exception as e:
            logger.warning(f"Could not fetch corporate actions: {e}")
        
        return actions
    
    @with_retry_and_cache(cache_ttl=300)  # 5 minutes for market data
    async def get_market_data(self) -> MarketData:
        """Get broad market indices data with caching."""
        await self.initialize()
        
        try:
            loop = asyncio.get_event_loop()
            
            # Fetch indices in parallel
            nifty_task = loop.run_in_executor(None, yf.Ticker, "^NSEI")
            sensex_task = loop.run_in_executor(None, yf.Ticker, "^BSESN")
            vix_task = loop.run_in_executor(None, yf.Ticker, "^INDIAVIX")
            
            nifty, sensex, vix = await asyncio.gather(nifty_task, sensex_task, vix_task)
            
            # Get info
            nifty_info = await loop.run_in_executor(None, lambda: nifty.info)
            sensex_info = await loop.run_in_executor(None, lambda: sensex.info)
            vix_info = await loop.run_in_executor(None, lambda: vix.info)
            
            nifty_price = nifty_info.get('regularMarketPrice', 0) or 0
            nifty_prev = nifty_info.get('previousClose', nifty_price) or nifty_price
            nifty_change = ((nifty_price - nifty_prev) / nifty_prev * 100) if nifty_prev else 0
            
            sensex_price = sensex_info.get('regularMarketPrice', 0) or 0
            sensex_prev = sensex_info.get('previousClose', sensex_price) or sensex_price
            sensex_change = ((sensex_price - sensex_prev) / sensex_prev * 100) if sensex_prev else 0
            
            return MarketData(
                nifty_50=nifty_price,
                nifty_change_percent=round(nifty_change, 2),
                sensex=sensex_price,
                sensex_change_percent=round(sensex_change, 2),
                india_vix=vix_info.get('regularMarketPrice', 0) or 0,
                market_status="open" if nifty_info.get('marketState') == 'REGULAR' else "closed",
            )
            
        except Exception as e:
            logger.error(f"Error fetching market data: {e}")
            return MarketData()
    
    @with_retry_and_cache(cache_ttl=300)  # 5 minutes for quick price
    async def get_quick_price(self, ticker: str) -> Optional[dict]:
        """Get just the current price quickly with caching."""
        await self.initialize()
        
        try:
            loop = asyncio.get_event_loop()
            stock = await loop.run_in_executor(None, yf.Ticker, ticker)
            info = await loop.run_in_executor(None, lambda: stock.info)
            
            if not info:
                return None
            
            current_price = info.get('currentPrice') or info.get('regularMarketPrice') or info.get('previousClose', 0)
            previous_close = info.get('previousClose', current_price)
            
            change = current_price - previous_close
            change_percent = (change / previous_close * 100) if previous_close else 0
            
            return {
                'ticker': ticker,
                'name': info.get('longName', info.get('shortName', ticker)),
                'current_price': current_price,
                'change': round(change, 2),
                'change_percent': round(change_percent, 2),
                'volume': info.get('volume', 0) or 0,
                'day_high': info.get('dayHigh', current_price) or current_price,
                'day_low': info.get('dayLow', current_price) or current_price,
                'previous_close': previous_close
            }
            
        except Exception as e:
            logger.error(f"Error fetching quick price for {ticker}: {e}")
            return None