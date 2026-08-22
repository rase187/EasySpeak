"""
LLM processor for EasySpeak.
Cleans up transcripts using LLM API (Groq, OpenAI, or Anthropic).
"""

import os
from typing import Optional

import requests
from utils.config_manager import get_config


class LLMProcessor:
    """Processes transcripts through LLM for cleanup."""

    def __init__(self, provider: Optional[str] = None, model: Optional[str] = None):
        """
        Initialize LLM processor.

        Args:
            provider: LLM provider (groq, openai, anthropic)
            model: Model name
        """
        self.config = get_config()
        self.provider = provider or self.config.get("llm.provider", "groq")
        self.model = model or self.config.get("llm.model", "llama3-8b-8192")
        self._default_prompt = self.config.get(
            "llm.prompt",
            "You are a dictation assistant. Clean up this transcript: "
            "- Remove filler words (um, uh, like, you know) "
            "- Add proper punctuation "
            "- Fix capitalization for proper nouns "
            "- Keep the natural flow of speech "
            "- Don't change the meaning or add words"
        )

    def _get_api_key(self) -> Optional[str]:
        """Get API key for the provider."""
        return self.config.get_api_key(self.provider)

    def _get_endpoint(self) -> str:
        """Get API endpoint for the provider."""
        if self.provider == "groq":
            return "https://api.groq.com/openai/v1/chat/completions"
        elif self.provider == "openai":
            return "https://api.openai.com/v1/chat/completions"
        elif self.provider == "anthropic":
            return "https://api.anthropic.com/v1/messages"
        else:
            raise ValueError(f"Unknown LLM provider: {self.provider}")

    def process(self, text: str, custom_prompt: Optional[str] = None, language: Optional[str] = None) -> str:
        """
        Process transcript through LLM.

        Args:
            text: Raw transcript text
            custom_prompt: Optional custom prompt
            language: Language code (e.g. 'en', 'tr'). If not 'en', LLM is skipped.

        Returns:
            Cleaned text, or original text if processing fails
        """
        if not text or not text.strip():
            return text

        # Skip LLM for non-English languages - use raw transcript
        if language and language != "en":
            return text

        prompt = custom_prompt or self._default_prompt

        api_key = self._get_api_key()
        if not api_key or api_key == "test_key" or api_key == "your_groq_api_key_here" or api_key == "your_openai_api_key_here" or api_key == "your_anthropic_api_key_here":
            # Silently skip LLM if no valid API key
            return text

        try:
            if self.provider == "anthropic":
                return self._process_anthropic(text, prompt, api_key)
            else:
                return self._process_openai_compatible(text, prompt, api_key)
        except Exception as e:
            # Check for auth errors - silently skip
            if "401" in str(e) or "invalid_api_key" in str(e).lower() or "unauthorized" in str(e).lower():
                return text
            print(f"LLM processing failed: {e}")
            return text

    def _process_openai_compatible(self, text: str, prompt: str, api_key: str) -> str:
        """Process using OpenAI-compatible API (Groq, OpenAI)."""
        endpoint = self._get_endpoint()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": text}
            ],
            "temperature": 0.3,
            "max_tokens": 2000
        }

        response = requests.post(endpoint, json=data, headers=headers, timeout=30)

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    def _process_anthropic(self, text: str, prompt: str, api_key: str) -> str:
        """Process using Anthropic API."""
        endpoint = self._get_endpoint()

        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "max_tokens": 2000,
            "temperature": 0.3,
            "system": prompt,
            "messages": [
                {"role": "user", "content": text}
            ]
        }

        response = requests.post(endpoint, json=data, headers=headers, timeout=30)

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        result = response.json()
        return result["content"][0]["text"].strip()


def create_llm_processor() -> LLMProcessor:
    """Create LLM processor based on configuration."""
    config = get_config()
    provider = config.get("llm.provider", "groq")
    model = config.get("llm.model", "llama3-8b-8192")
    return LLMProcessor(provider=provider, model=model)