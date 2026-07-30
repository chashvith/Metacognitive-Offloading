"""Groq LLM Client Module.

Provides robust integration with Groq API with:
- Groq SDK transport layer
- Automatic API key resolution from backend/config.py
- Exponential backoff retry logic
- Request timeout protection
- In-memory response caching to prevent duplicate API quota usage
- Strict JSON response extraction and cleaning
"""

import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

from groq import Groq

from config import settings

logger = logging.getLogger(__name__)


class GroqClient:
    """Production-grade client for Groq API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self.api_key = api_key if api_key is not None else settings.GROQ_API_KEY
        self.model_name = model_name or settings.GROQ_MODEL_NAME
        self.timeout = timeout or settings.GROQ_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.GROQ_MAX_RETRIES

        # In-memory response cache: hash -> (timestamp, response_dict)
        self._cache: Dict[str, tuple[float, Dict[str, Any]]] = {}
        self._cache_ttl_seconds: float = 3600.0  # 1 hour TTL

    def _compute_cache_key(self, system_instruction: str, prompt_text: str) -> str:
        """Generates a SHA-256 cache key from system instruction and prompt payload."""
        combined = f"{system_instruction}::{prompt_text}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()

    def generate_structured_json(
        self,
        system_instruction: str,
        user_prompt: str,
    ) -> Optional[Dict[str, Any]]:
        """Sends prompt to Groq and returns parsed JSON dictionary.

        Args:
            system_instruction: System prompt framing LLM as AI Programming Tutor.
            user_prompt: Detailed prompt context string.

        Returns:
            Parsed JSON dictionary or None if API call fails/times out.
        """
        if not self.api_key or self.api_key.strip() == "" or self.api_key == "your_groq_api_key_here":
            logger.warning("GroqClient: GROQ_API_KEY is not configured in backend/.env. Bypassing API call.")
            return None

        # Check Cache
        cache_key = self._compute_cache_key(system_instruction, user_prompt)
        now = time.time()
        if cache_key in self._cache:
            created_at, cached_data = self._cache[cache_key]
            if now - created_at < self._cache_ttl_seconds:
                logger.info("GroqClient: Returning cached LLM recommendation response (cache hit).")
                return cached_data

        # Attempt SDK API call with retry
        response_text = self._call_api_with_retry(system_instruction, user_prompt)
        if not response_text:
            return None

        parsed_json = self._extract_json(response_text)
        if parsed_json:
            self._cache[cache_key] = (now, parsed_json)

        return parsed_json

    def _call_api_with_retry(self, system_instruction: str, user_prompt: str) -> Optional[str]:
        """Executes SDK request with exponential backoff retries."""
        client = Groq(api_key=self.api_key, timeout=self.timeout)

        for attempt in range(1, self.max_retries + 1):
            try:
                logger.info(
                    "GroqClient: Requesting Groq API via SDK (Attempt %d/%d, model=%s)...",
                    attempt,
                    self.max_retries,
                    self.model_name,
                )
                
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_instruction},
                        {"role": "user", "content": user_prompt}
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                    max_tokens=1024,
                )
                
                response_text = response.choices[0].message.content
                if response_text:
                    return response_text

                logger.warning("GroqClient: SDK returned an empty text response.")
                return None

            except Exception as e:
                import traceback
                traceback.print_exc()

            if attempt < self.max_retries:
                sleep_time = (2 ** (attempt - 1)) * 0.5  # 0.5s, 1.0s, 2.0s
                time.sleep(sleep_time)

        logger.error("GroqClient: Exceeded max retries (%d). API call failed.", self.max_retries)
        return None

    def _extract_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        """Cleans and extracts JSON dictionary from raw model text response."""
        if not raw_text:
            return None

        cleaned = raw_text.strip()
        if cleaned.startswith("```"):
            lines = cleaned.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].startswith("```"):
                lines = lines[:-1]
            cleaned = "\n".join(lines).strip()

        try:
            parsed = json.loads(cleaned)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            import traceback
            print("\n" + "="*80)
            traceback.print_exc()
            print("="*80 + "\n")

        return None


# Global singleton client instance
groq_client = GroqClient()
