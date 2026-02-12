"""
OpenRouter API Client
Generic client for making API calls to OpenRouter.
"""

import logging
import os
import time
from typing import Optional

import requests

logger = logging.getLogger(__name__)

OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"


class OpenRouterClient:
    """Client for OpenRouter API."""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the OpenRouter client.
        
        Args:
            api_key: OpenRouter API key. If not provided, reads from OPENROUTER_API_KEY env var.
        """
        self.api_key = api_key or os.environ.get("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")
        
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/faithfulness-benchmark",
        }
    
    def chat_completion(
        self,
        model: str,
        messages: list[dict],
        max_tokens: int = 4096,
        temperature: float = 0.3,
        max_retries: int = 5,
        base_delay: float = 10.0,
    ) -> str:
        """
        Make a chat completion request to OpenRouter.
        
        Args:
            model: Model identifier (e.g., "openai/gpt-oss-120b:free")
            messages: List of message dicts with 'role' and 'content'
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            max_retries: Number of retry attempts on failure
            base_delay: Base delay between retries (exponential backoff)
            
        Returns:
            The model's response text
        """
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        for attempt in range(max_retries):
            try:
                # Exponential backoff delay on retries: 10s, 20s, 40s, 80s...
                if attempt > 0:
                    wait_time = base_delay * (2 ** (attempt - 1))
                    logger.info(f"Waiting {wait_time}s before retry (attempt {attempt + 1})...")
                    time.sleep(wait_time)
                
                logger.info(f"Calling {model} (attempt {attempt + 1}/{max_retries})")
                
                response = requests.post(
                    OPENROUTER_API_URL,
                    headers=self.headers,
                    json=payload,
                    timeout=180,  # Longer timeout for free models
                )
                
                if response.status_code == 429:
                    # Rate limited - will retry with exponential backoff
                    logger.warning(f"Rate limited (429). Will retry with backoff...")
                    continue
                
                if response.status_code == 404:
                    # Model not found - log and raise immediately
                    logger.error(f"Model not found (404): {model}")
                    raise ValueError(f"Model not found: {model}")
                
                response.raise_for_status()
                
                result = response.json()
                
                # Check for error in response body
                if "error" in result:
                    error_msg = result.get("error", {}).get("message", str(result["error"]))
                    logger.error(f"API error: {error_msg}")
                    continue
                
                content = result["choices"][0]["message"]["content"]
                logger.info(f"Received response: {len(content)} characters")
                return content
                
            except requests.exceptions.Timeout:
                logger.warning(f"Request timed out (attempt {attempt + 1})")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"Request failed: {e}")
                if attempt >= max_retries - 1:
                    raise
        
        raise RuntimeError(f"Failed to get response from {model} after {max_retries} attempts")
