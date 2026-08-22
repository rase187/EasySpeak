"""
Transcription module for EasySpeak.
Supports local (faster-whisper) and API (Groq/OpenAI) transcription.
"""

import os
import tempfile
from abc import ABC, abstractmethod
from typing import Optional

import requests
from utils.config_manager import get_config


class Transcriber(ABC):
    """Abstract base class for transcription backends."""

    @abstractmethod
    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file to text.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        pass


class LocalTranscriber(Transcriber):
    """Local transcription using faster-whisper."""

    def __init__(self, model_size: str = "base"):
        """
        Initialize local transcriber.

        Args:
            model_size: Model size (tiny, base, small, medium, large)
        """
        self.model_size = model_size
        self._model = None

    def _load_model(self) -> None:
        """Load the Whisper model."""
        if self._model is None:
            from faster_whisper import WhisperModel
            # Use CPU by default, can be changed to cuda if available
            self._model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"
            )

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file using local Whisper model.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text
        """
        self._load_model()

        # Restrict to Turkish and English only
        segments, info = self._model.transcribe(
            audio_path,
            beam_size=5,
            language=None,  # Auto-detect but will use language_probability
            condition_on_previous_text=False,
            suppress_tokens=[-1],  # Don't suppress any tokens
            without_timestamps=True
        )

        # Get detected language and filter to tr/en only
        detected_lang = info.language
        lang_prob = info.language_probability

        # If detected language is not Turkish or English, force English
        if detected_lang not in ("tr", "en"):
            print(f"Detected language '{detected_lang}' (prob: {lang_prob:.2f}) - restricting to English")
            # Re-transcribe with English forced
            segments, info = self._model.transcribe(
                audio_path,
                beam_size=5,
                language="en",
                condition_on_previous_text=False
            )

        # Combine all segments
        text = " ".join([segment.text for segment in segments])
        return text.strip()


class APITranscriber(Transcriber):
    """API-based transcription using Groq or OpenAI."""

    def __init__(self, provider: str = "groq"):
        """
        Initialize API transcriber.

        Args:
            provider: API provider (groq, openai)
        """
        self.provider = provider.lower()
        self.config = get_config()

    def _get_api_key(self) -> Optional[str]:
        """Get API key for the provider."""
        return self.config.get_api_key(self.provider)

    def _get_endpoint(self) -> str:
        """Get API endpoint for the provider."""
        if self.provider == "groq":
            return "https://api.groq.com/openai/v1/audio/transcriptions"
        elif self.provider == "openai":
            return "https://api.openai.com/v1/audio/transcriptions"
        else:
            raise ValueError(f"Unknown provider: {self.provider}")

    def transcribe(self, audio_path: str) -> str:
        """
        Transcribe audio file using API.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcribed text

        Raises:
            Exception: If API request fails
        """
        api_key = self._get_api_key()
        if not api_key:
            raise ValueError(f"No API key found for {self.provider}")

        endpoint = self._get_endpoint()

        with open(audio_path, "rb") as f:
            files = {"file": ("audio.wav", f, "audio/wav")}
            data = {
                "model": "whisper-1" if self.provider == "openai" else "whisper-large-v3",
                "response_format": "verbose_json",  # Get language info
            }
            headers = {"Authorization": f"Bearer {api_key}"}

            response = requests.post(endpoint, files=files, data=data, headers=headers)

        if response.status_code != 200:
            raise Exception(f"API error: {response.status_code} - {response.text}")

        result = response.json()
        text = result.get("text", "").strip()
        detected_lang = result.get("language", "en").lower()

        # DEBUG: Print detected language (handle encoding issues)
        try:
            print(f"[DEBUG] Groq detected language: '{detected_lang}', text: '{text[:50]}...'")
        except UnicodeEncodeError:
            print(f"[DEBUG] Groq detected language: '{detected_lang}', text: (encoding error)")

        # Restrict to Turkish and English only (same as local transcriber)
        # Groq returns full names like "turkish", "english" - convert to codes
        lang_code = "en"
        if detected_lang in ("turkish", "tr"):
            lang_code = "tr"
        elif detected_lang in ("english", "en"):
            lang_code = "en"

        if lang_code not in ("tr", "en"):
            print(f"Detected language '{detected_lang}' - restricting to English, re-transcribing...")
            # Re-transcribe with English forced
            with open(audio_path, "rb") as f:
                files = {"file": ("audio.wav", f, "audio/wav")}
                data = {
                    "model": "whisper-1" if self.provider == "openai" else "whisper-large-v3",
                    "language": "en",
                    "response_format": "json",
                }
                headers = {"Authorization": f"Bearer {api_key}"}
                response = requests.post(endpoint, files=files, data=data, headers=headers)

            if response.status_code == 200:
                result = response.json()
                text = result.get("text", "").strip()

        return text


def create_transcriber() -> Transcriber:
    """
    Create transcriber based on configuration.

    Returns:
        Transcriber instance (LocalTranscriber or APITTranscriber)
    """
    config = get_config()
    mode = config.get("transcription.mode", "local")

    if mode == "local":
        model = config.get("transcription.local_model", "base")
        return LocalTranscriber(model_size=model)
    elif mode == "api":
        provider = config.get("transcription.api_provider", "groq")
        return APITranscriber(provider=provider)
    else:
        raise ValueError(f"Unknown transcription mode: {mode}")


# Alias for backward compatibility
APITTranscriber = APITranscriber