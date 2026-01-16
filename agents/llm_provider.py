"""LLM Provider with Gemini primary and OpenRouter fallback."""

import json
from typing import Optional, Type, TypeVar
from pydantic import BaseModel
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import google.generativeai as genai
import openai

from config import settings


T = TypeVar('T', bound=BaseModel)


class LLMProvider:
    """
    LLM provider with Gemini as primary and OpenRouter as fallback.
    """
    
    def __init__(self):
        # Initialize Gemini
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.gemini_model = genai.GenerativeModel(settings.PRIMARY_LLM_MODEL)
        
        # Initialize OpenRouter client
        if settings.OPENROUTER_API_KEY:
            self.openrouter_client = openai.OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=settings.OPENROUTER_API_KEY,
            )
        else:
            self.openrouter_client = None
        
        self.default_temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        response_schema: Optional[Type[T]] = None,
    ) -> str | T:
        """
        Generate completion using Gemini with OpenRouter fallback.
        
        Args:
            prompt: User prompt
            system_prompt: System instructions
            temperature: Generation temperature
            response_schema: Pydantic model for structured output
            
        Returns:
            Generated text or parsed Pydantic model
        """
        temp = temperature if temperature is not None else self.default_temperature
        
        # Try Gemini first
        try:
            result = await self._generate_gemini(
                prompt, system_prompt, temp, response_schema
            )
            return result
        except Exception as e:
            logger.warning(f"Gemini failed: {e}, trying OpenRouter fallback")
        
        # Fallback to OpenRouter
        if self.openrouter_client:
            try:
                result = await self._generate_openrouter(
                    prompt, system_prompt, temp, response_schema
                )
                return result
            except Exception as e:
                logger.error(f"OpenRouter also failed: {e}")
                raise
        
        raise Exception("All LLM providers failed")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError)),
    )
    async def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        response_schema: Optional[Type[T]],
    ) -> str | T:
        """Generate using Gemini API."""
        
        # Build the full prompt
        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n"
        full_prompt += prompt
        
        # Add schema instructions if needed
        if response_schema:
            schema_json = response_schema.model_json_schema()
            full_prompt += f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema_json, indent=2)}"
            full_prompt += "\n\nIMPORTANT: Return ONLY the JSON object, no markdown formatting or explanation."
        
        # Generate
        generation_config = genai.GenerationConfig(
            temperature=temperature,
            max_output_tokens=self.max_tokens,
        )
        
        response = self.gemini_model.generate_content(
            full_prompt,
            generation_config=generation_config,
        )
        
        text = response.text.strip()
        
        # Parse if schema provided
        if response_schema:
            return self._parse_response(text, response_schema)
        
        return text
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        retry=retry_if_exception_type((ConnectionError, TimeoutError, openai.APIConnectionError)),
    )
    async def _generate_openrouter(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        response_schema: Optional[Type[T]],
    ) -> str | T:
        """Generate using OpenRouter API."""
        
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        user_content = prompt
        if response_schema:
            schema_json = response_schema.model_json_schema()
            user_content += f"\n\nRespond with valid JSON matching this schema:\n{json.dumps(schema_json, indent=2)}"
            user_content += "\n\nIMPORTANT: Return ONLY the JSON object, no markdown formatting or explanation."
        
        messages.append({"role": "user", "content": user_content})
        
        response = self.openrouter_client.chat.completions.create(
            model=settings.FALLBACK_LLM_MODEL,
            messages=messages,
            temperature=temperature,
            max_tokens=self.max_tokens,
        )
        
        text = response.choices[0].message.content.strip()
        
        # Parse if schema provided
        if response_schema:
            return self._parse_response(text, response_schema)
        
        return text
    
    def _parse_response(self, text: str, schema: Type[T]) -> T:
        """Parse LLM response into Pydantic model."""
        # Remove markdown code blocks if present
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()
        
        try:
            data = json.loads(text)
            return schema.model_validate(data)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}\nText: {text[:500]}")
            raise ValueError(f"Invalid JSON response: {e}")
        except Exception as e:
            logger.error(f"Failed to validate schema: {e}")
            raise ValueError(f"Schema validation failed: {e}")
    
    async def generate_simple(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
    ) -> str:
        """Simple text generation without structured output."""
        return await self.generate(prompt, system_prompt)


# Global LLM provider instance
llm = LLMProvider()
