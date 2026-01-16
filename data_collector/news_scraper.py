"""News collector using free APIs and RSS feeds."""

import asyncio
import aiohttp
import feedparser
from datetime import datetime, timedelta
from typing import List, Optional
from loguru import logger

from .schemas import NewsArticle, NewsData
from config import settings


class NewsCollector:
    """Collect news from various free sources."""
    
    # Free RSS feeds for Indian financial news
    RSS_FEEDS = {
        "economic_times": "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms",
        "moneycontrol": "https://www.moneycontrol.com/rss/marketreports.xml",
        "livemint": "https://www.livemint.com/rss/markets",
        "business_standard": "https://www.business-standard.com/rss/markets-106.rss",
    }
    
    # GNews API endpoint (free tier: 100 requests/day)
    GNEWS_API = "https://gnews.io/api/v4/search"
    
    # NewsAPI endpoint (free tier: 100 requests/day, limited to past month)
    NEWSAPI_ENDPOINT = "https://newsapi.org/v2/everything"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """Close the session."""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_news(
        self,
        ticker: str,
        company_name: str = "",
        days: int = 7,
        max_articles: int = 20
    ) -> NewsData:
        """
        Fetch news for a stock from multiple sources.
        
        Args:
            ticker: Stock ticker
            company_name: Company name for search
            days: Number of days to look back
            max_articles: Maximum articles to return
            
        Returns:
            NewsData with aggregated news
        """
        # Extract base ticker name for search
        search_term = self._get_search_term(ticker, company_name)
        
        all_articles = []
        
        # Fetch from multiple sources in parallel
        tasks = [
            self._fetch_from_rss(search_term),
            self._fetch_from_gnews(search_term, days),
            self._fetch_from_newsapi(search_term, days),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for result in results:
            if isinstance(result, list):
                all_articles.extend(result)
            elif isinstance(result, Exception):
                logger.warning(f"News fetch error: {result}")
        
        # Deduplicate and sort by date
        unique_articles = self._deduplicate_articles(all_articles)
        sorted_articles = sorted(
            unique_articles,
            key=lambda x: x.published_at or datetime.min,
            reverse=True
        )[:max_articles]
        
        # Analyze sentiment
        sentiment_stats = self._analyze_sentiment(sorted_articles)
        
        return NewsData(
            ticker=ticker,
            articles=sorted_articles,
            total_count=len(sorted_articles),
            positive_count=sentiment_stats['positive'],
            negative_count=sentiment_stats['negative'],
            neutral_count=sentiment_stats['neutral'],
            overall_sentiment=sentiment_stats['overall'],
            fetched_at=datetime.now(),
        )
    
    def _get_search_term(self, ticker: str, company_name: str) -> str:
        """Get search term from ticker or company name."""
        # Remove exchange suffix
        base_ticker = ticker.replace('.NS', '').replace('.BO', '')
        
        # Common ticker to name mappings
        ticker_names = {
            'RELIANCE': 'Reliance Industries',
            'TCS': 'Tata Consultancy Services',
            'INFY': 'Infosys',
            'HDFCBANK': 'HDFC Bank',
            'ICICIBANK': 'ICICI Bank',
            'HINDUNILVR': 'Hindustan Unilever',
            'BHARTIARTL': 'Bharti Airtel',
            'SBIN': 'State Bank of India',
            'KOTAKBANK': 'Kotak Mahindra Bank',
            'WIPRO': 'Wipro',
            'TATAMOTORS': 'Tata Motors',
            'TATASTEEL': 'Tata Steel',
            'MARUTI': 'Maruti Suzuki',
        }
        
        if company_name:
            return company_name
        
        return ticker_names.get(base_ticker, base_ticker)
    
    async def _fetch_from_rss(self, search_term: str) -> List[NewsArticle]:
        """Fetch news from RSS feeds."""
        articles = []
        search_lower = search_term.lower()
        
        for source_name, feed_url in self.RSS_FEEDS.items():
            try:
                feed = feedparser.parse(feed_url)
                
                for entry in feed.entries[:20]:
                    # Check if article is relevant
                    title = entry.get('title', '')
                    summary = entry.get('summary', '')
                    
                    if search_lower in title.lower() or search_lower in summary.lower():
                        published = None
                        if 'published_parsed' in entry and entry.published_parsed:
                            published = datetime(*entry.published_parsed[:6])
                        
                        articles.append(NewsArticle(
                            title=title,
                            source=source_name.replace('_', ' ').title(),
                            url=entry.get('link', ''),
                            published_at=published,
                            description=summary[:300] if summary else None,
                            sentiment=self._simple_sentiment(title + ' ' + summary),
                            relevance="high" if search_lower in title.lower() else "medium",
                        ))
                        
            except Exception as e:
                logger.warning(f"Error fetching RSS from {source_name}: {e}")
        
        return articles
    
    async def _fetch_from_gnews(
        self,
        search_term: str,
        days: int
    ) -> List[NewsArticle]:
        """Fetch news from GNews API."""
        if not settings.GNEWS_API_KEY:
            return []
        
        try:
            session = await self._get_session()
            
            params = {
                'q': f'"{search_term}" stock OR share',
                'lang': 'en',
                'country': 'in',
                'max': 10,
                'token': settings.GNEWS_API_KEY,
            }
            
            async with session.get(self.GNEWS_API, params=params) as response:
                if response.status != 200:
                    logger.warning(f"GNews API returned {response.status}")
                    return []
                
                data = await response.json()
                articles = []
                
                for article in data.get('articles', []):
                    published = None
                    if article.get('publishedAt'):
                        try:
                            published = datetime.fromisoformat(
                                article['publishedAt'].replace('Z', '+00:00')
                            )
                        except ValueError:
                            pass
                    
                    articles.append(NewsArticle(
                        title=article.get('title', ''),
                        source=article.get('source', {}).get('name', 'GNews'),
                        url=article.get('url', ''),
                        published_at=published,
                        description=article.get('description'),
                        sentiment=self._simple_sentiment(
                            article.get('title', '') + ' ' + article.get('description', '')
                        ),
                        relevance="high",
                    ))
                
                return articles
                
        except Exception as e:
            logger.warning(f"Error fetching from GNews: {e}")
            return []
    
    async def _fetch_from_newsapi(
        self,
        search_term: str,
        days: int
    ) -> List[NewsArticle]:
        """Fetch news from NewsAPI."""
        if not settings.NEWSAPI_KEY:
            return []
        
        try:
            session = await self._get_session()
            
            from_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            params = {
                'q': f'"{search_term}"',
                'from': from_date,
                'language': 'en',
                'sortBy': 'relevancy',
                'pageSize': 10,
                'apiKey': settings.NEWSAPI_KEY,
            }
            
            async with session.get(self.NEWSAPI_ENDPOINT, params=params) as response:
                if response.status != 200:
                    logger.warning(f"NewsAPI returned {response.status}")
                    return []
                
                data = await response.json()
                articles = []
                
                for article in data.get('articles', []):
                    published = None
                    if article.get('publishedAt'):
                        try:
                            published = datetime.fromisoformat(
                                article['publishedAt'].replace('Z', '+00:00')
                            )
                        except ValueError:
                            pass
                    
                    articles.append(NewsArticle(
                        title=article.get('title', ''),
                        source=article.get('source', {}).get('name', 'NewsAPI'),
                        url=article.get('url', ''),
                        published_at=published,
                        description=article.get('description'),
                        sentiment=self._simple_sentiment(
                            article.get('title', '') + ' ' + (article.get('description') or '')
                        ),
                        relevance="medium",
                    ))
                
                return articles
                
        except Exception as e:
            logger.warning(f"Error fetching from NewsAPI: {e}")
            return []
    
    def _simple_sentiment(self, text: str) -> str:
        """
        Simple keyword-based sentiment analysis.
        
        For production, consider using FinBERT or similar.
        """
        text = text.lower()
        
        positive_words = [
            'surge', 'soar', 'gain', 'rise', 'jump', 'rally', 'bullish',
            'growth', 'profit', 'beat', 'exceed', 'strong', 'upgrade',
            'outperform', 'buy', 'positive', 'record', 'high', 'boom',
            'expansion', 'success', 'milestone', 'breakthrough', 'win',
        ]
        
        negative_words = [
            'fall', 'drop', 'decline', 'plunge', 'crash', 'bearish',
            'loss', 'miss', 'below', 'weak', 'downgrade', 'underperform',
            'sell', 'negative', 'low', 'concern', 'risk', 'warning',
            'cut', 'reduce', 'layoff', 'struggle', 'fail', 'fraud',
        ]
        
        positive_count = sum(1 for word in positive_words if word in text)
        negative_count = sum(1 for word in negative_words if word in text)
        
        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        else:
            return "neutral"
    
    def _deduplicate_articles(self, articles: List[NewsArticle]) -> List[NewsArticle]:
        """Remove duplicate articles based on title similarity."""
        seen_titles = set()
        unique = []
        
        for article in articles:
            # Normalize title for comparison
            normalized = article.title.lower()[:50]
            
            if normalized not in seen_titles:
                seen_titles.add(normalized)
                unique.append(article)
        
        return unique
    
    def _analyze_sentiment(self, articles: List[NewsArticle]) -> dict:
        """Analyze overall sentiment from articles."""
        positive = sum(1 for a in articles if a.sentiment == "positive")
        negative = sum(1 for a in articles if a.sentiment == "negative")
        neutral = len(articles) - positive - negative
        
        if positive > negative * 1.5:
            overall = "positive"
        elif negative > positive * 1.5:
            overall = "negative"
        else:
            overall = "neutral"
        
        return {
            'positive': positive,
            'negative': negative,
            'neutral': neutral,
            'overall': overall,
        }
