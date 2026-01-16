"""Portfolio Parser - Extract holdings from images using vision LLM."""

import base64
import json
from typing import List, Dict, Any, Optional
from io import BytesIO
from pydantic import BaseModel, Field
from loguru import logger
import openai

from config.settings import settings


class PortfolioHolding(BaseModel):
    """Single portfolio holding extracted from image."""
    ticker: str = Field(..., description="Stock ticker symbol (e.g., TCS, RELIANCE)")
    quantity: int = Field(..., description="Number of shares held", gt=0)
    avg_price: float = Field(..., description="Average buy price per share", gt=0)
    current_price: Optional[float] = Field(None, description="Current market price if visible")


class ExtractedPortfolio(BaseModel):
    """Portfolio extracted from image."""
    holdings: List[PortfolioHolding] = Field(default_factory=list)
    total_holdings: int = 0
    confidence: str = Field(default="MEDIUM", description="Extraction confidence: HIGH, MEDIUM, LOW")
    notes: List[str] = Field(default_factory=list, description="Any extraction notes or warnings")


class PortfolioImageParser:
    """Parse portfolio holdings from images using vision LLM."""
    
    def __init__(self):
        """Initialize OpenRouter client for vision."""
        if not settings.OPENROUTER_API_KEY:
            raise ValueError("OpenRouter API key required for image parsing")
        
        self.client = openai.OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=settings.OPENROUTER_API_KEY,
        )
        
        # Use a vision-capable model
        self.vision_model = "allenai/molmo-2-8b:free"  # or "anthropic/claude-3.5-sonnet"
    
    async def parse_image(self, image_data: bytes) -> ExtractedPortfolio:
        """
        Parse portfolio holdings from image.
        
        Args:
            image_data: Image bytes (PNG, JPG, etc.)
            
        Returns:
            ExtractedPortfolio with holdings and metadata
        """
        logger.info("Parsing portfolio from image")
        
        try:
            # Convert image to base64
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Detect image format
            image_format = self._detect_format(image_data)
            mime_type = f"image/{image_format}"
            
            # Build prompt
            prompt = self._build_extraction_prompt()
            
            # Call vision API
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{mime_type};base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                temperature=0.1,
                max_tokens=2000,
            )
            
            # Extract response
            content = response.choices[0].message.content
            
            # Parse JSON
            parsed = self._parse_response(content)
            
            logger.info(f"Successfully extracted {len(parsed.holdings)} holdings")
            return parsed
            
        except Exception as e:
            logger.error(f"Error parsing portfolio image: {e}")
            return ExtractedPortfolio(
                holdings=[],
                confidence="LOW",
                notes=[f"Extraction failed: {str(e)}"]
            )
    
    def _detect_format(self, image_data: bytes) -> str:
        """Detect image format from bytes."""
        # PNG
        if image_data.startswith(b'\x89PNG\r\n\x1a\n'):
            return "png"
        # JPEG
        elif image_data.startswith(b'\xff\xd8\xff'):
            return "jpeg"
        # WebP
        elif image_data[8:12] == b'WEBP':
            return "webp"
        else:
            return "jpeg"  # Default
    
    def _build_extraction_prompt(self) -> str:
        """Build prompt for vision model."""
        return """Extract portfolio holdings from this image.

Look for:
- Stock ticker symbols (e.g., TCS, RELIANCE, INFY, HDFCBANK)
- Quantity/shares held
- Average buy price or cost price
- Current market price (if shown)

Common formats:
- Broker apps (Zerodha, Groww, Upstox, Angel One)
- Excel/Google Sheets screenshots
- Portfolio tracking apps
- Handwritten notes

Important:
- For NSE stocks, ensure tickers are standard symbols (TCS not TCS.NS)
- If ticker has .NS or .BO suffix, remove it
- Ignore sections like "Watchlist", "Orders", "Positions" - focus on "Holdings" or "Portfolio"
- Skip mutual funds, ETFs unless they're equity stocks
- If current price shown but not avg price, note it

Return ONLY a valid JSON object matching this schema:
{
  "holdings": [
    {
      "ticker": "TCS",
      "quantity": 100,
      "avg_price": 3400.50,
      "current_price": 3562.00  // optional
    }
  ],
  "confidence": "HIGH",  // HIGH, MEDIUM, or LOW
  "notes": ["Any warnings or uncertainties"]
}

If you cannot extract any holdings, return:
{
  "holdings": [],
  "confidence": "LOW",
  "notes": ["Reason why extraction failed"]
}

RESPOND WITH ONLY THE JSON, NO MARKDOWN OR EXPLANATION."""
    
    def _parse_response(self, content: str) -> ExtractedPortfolio:
        """Parse LLM response into structured format."""
        # Remove markdown if present
        content = content.strip()
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            data = json.loads(content)
            
            # Validate and normalize tickers
            if "holdings" in data:
                for holding in data["holdings"]:
                    # Remove .NS or .BO suffix if present
                    ticker = holding.get("ticker", "").upper()
                    ticker = ticker.replace(".NS", "").replace(".BO", "")
                    holding["ticker"] = ticker
            
            # Parse into Pydantic model
            portfolio = ExtractedPortfolio.model_validate(data)
            portfolio.total_holdings = len(portfolio.holdings)
            
            return portfolio
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nContent: {content[:500]}")
            return ExtractedPortfolio(
                holdings=[],
                confidence="LOW",
                notes=[f"Invalid JSON response: {str(e)}"]
            )
        except Exception as e:
            logger.error(f"Failed to validate portfolio: {e}")
            return ExtractedPortfolio(
                holdings=[],
                confidence="LOW",
                notes=[f"Validation error: {str(e)}"]
            )
    
    def validate_tickers(self, holdings: List[PortfolioHolding]) -> List[str]:
        """
        Validate ticker symbols.
        
        Returns:
            List of warnings for invalid tickers
        """
        warnings = []
        
        # Common valid NSE tickers (not exhaustive)
        known_tickers = {
            "TCS", "RELIANCE", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", 
            "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "ASIANPAINT", "AXISBANK",
            "MARUTI", "TITAN", "NESTLEIND", "WIPRO", "ULTRACEMCO", "BAJFINANCE",
            "SUNPHARMA", "TECHM", "HCLTECH", "POWERGRID", "NTPC", "ONGC",
            "TATASTEEL", "TATAMOTORS", "ADANIPORTS", "COALINDIA", "GRASIM",
            "HINDALCO", "JSWSTEEL", "M&M", "DRREDDY", "CIPLA", "DIVISLAB"
        }
        
        for holding in holdings:
            ticker = holding.ticker
            
            # Check if ticker is reasonable length
            if len(ticker) < 2 or len(ticker) > 20:
                warnings.append(f"{ticker}: Unusual ticker length")
            
            # Check if alphanumeric
            if not ticker.replace("&", "").replace("-", "").isalnum():
                warnings.append(f"{ticker}: Contains special characters")
            
            # Warn if not in known list (not an error, just FYI)
            if ticker not in known_tickers and len(holdings) > 3:
                # Only warn if portfolio has multiple stocks (less likely to be typo)
                pass  # Don't add warning for every unknown ticker
        
        return warnings


# Example usage functions
async def parse_portfolio_from_telegram(file_data: bytes) -> ExtractedPortfolio:
    """
    Helper function to parse portfolio from Telegram photo.
    
    Args:
        file_data: Photo file bytes from Telegram
        
    Returns:
        ExtractedPortfolio
    """
    parser = PortfolioImageParser()
    return await parser.parse_image(file_data)


def format_extraction_result(portfolio: ExtractedPortfolio) -> str:
    """Format extraction result for display in Telegram."""
    
    if not portfolio.holdings:
        msg = "❌ Could not extract portfolio from image.\n\n"
        if portfolio.notes:
            msg += "Reasons:\n"
            for note in portfolio.notes:
                msg += f"• {note}\n"
        msg += "\nTry:\n"
        msg += "• Taking a clearer screenshot\n"
        msg += "• Ensuring holdings section is visible\n"
        msg += "• Manually adding stocks with /portfolio add"
        return msg
    
    confidence_emoji = {
        "HIGH": "🟢",
        "MEDIUM": "🟡",
        "LOW": "🟠",
    }
    
    msg = f"📊 Extracted {len(portfolio.holdings)} stocks\n"
    msg += f"{confidence_emoji.get(portfolio.confidence, '⚪')} Confidence: {portfolio.confidence}\n\n"
    
    msg += "*Holdings Found:*\n"
    for holding in portfolio.holdings:
        msg += f"• {holding.ticker}: {holding.quantity} shares @ ₹{holding.avg_price:.2f}\n"
    
    if portfolio.notes:
        msg += "\n⚠️ *Notes:*\n"
        for note in portfolio.notes:
            msg += f"• {note}\n"
    
    msg += "\nReview and confirm to add to your portfolio."
    
    return msg
