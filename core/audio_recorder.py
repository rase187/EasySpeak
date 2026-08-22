"""
Audio recorder for EasySpeak.
Records microphone input using sounddevice.
"""

import os
import tempfile
import threading
import wave
from typing import Optional

import numpy as np
import sounddevice as sd


class AudioRecorder:
    """Records audio from microphone and saves as WAV file."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        dtype: str = "int16",
        gain: float = 10.0,
        device: Optional[int] = None
    ):
        """
        Initialize the audio recorder.

        Args:
            sample_rate: Sample rate in Hz (16000 for Whisper)
            channels: Number of channels (1 for mono)
            dtype: Data type for recording
            gain: Software gain multiplier for low microphone input
            device: Input device index (None = system default)
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.dtype = dtype
        self.gain = gain
        self.device = device

        self._recording = False
        self._audio_data: list = []
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()
        self._temp_file: Optional[str] = None

    def _audio_callback(self, indata: np.ndarray, frames: int, time, status) -> None:
        """Callback for audio stream."""
        if status:
            print(f"Audio callback status: {status}")
        with self._lock:
            if self._recording:
                # Apply software gain to boost low microphone input
                if self.gain != 1.0:
                    boosted = (indata.astype(np.float32) * self.gain).clip(-32768, 32767).astype(np.int16)
                    self._audio_data.append(boosted)
                else:
                    self._audio_data.append(indata.copy())

    def start_recording(self, device: Optional[int] = None) -> bool:
        """
        Start recording audio.

        Args:
            device: Input device index (overrides instance device if provided)

        Returns:
            True if recording started successfully, False otherwise
        """
        with self._lock:
            if self._recording:
                return False

            self._audio_data = []
            self._recording = True

            # Use provided device, fallback to instance device, then system default
            use_device = device if device is not None else self.device

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=self.dtype,
                    callback=self._audio_callback,
                    device=use_device
                )
                self._stream.start()
                return True
            except Exception as e:
                print(f"Failed to start recording: {e}")
                self._recording = False
                return False

    def stop_recording(self) -> Optional[str]:
        """
        Stop recording and save to a temporary WAV file.

        Returns:
            Path to the saved WAV file, or None if not recording
        """
        with self._lock:
            if not self._recording:
                return None

            self._recording = False

            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            if not self._audio_data:
                return None

            # Concatenate all audio chunks
            audio_data = np.concatenate(self._audio_data, axis=0)

            # Save to temporary file
            self._temp_file = self._save_wav(audio_data)
            return self._temp_file

    def cancel_recording(self) -> None:
        """Cancel current recording and discard audio data."""
        with self._lock:
            if not self._recording:
                return

            self._recording = False

            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None

            self._audio_data = []

            if self._temp_file and os.path.exists(self._temp_file):
                try:
                    os.remove(self._temp_file)
                except OSError:
                    pass
                self._temp_file = None

    def _save_wav(self, audio_data: np.ndarray) -> str:
        """
        Save audio data to a temporary WAV file.

        Args:
            audio_data: Audio data as numpy array

        Returns:
            Path to the saved WAV file
        """
        # Create temp file
        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        # Ensure correct format for WAV
        if self.dtype == "int16":
            audio_data = audio_data.astype(np.int16)
        elif self.dtype == "float32":
            audio_data = (audio_data * 32767).astype(np.int16)

        with wave.open(temp_path, "wb") as wf:
            wf.setnchannels(self.channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(self.sample_rate)
            wf.writeframes(audio_data.tobytes())

        return temp_path

    @property
    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self._recording

    def get_audio_level(self) -> float:
        """
        Get current audio level (RMS) for visual feedback.

        Returns:
            RMS level (0.0 to 1.0)
        """
        with self._lock:
            if not self._audio_data:
                return 0.0

            # Get last chunk
            last_chunk = self._audio_data[-1]
            if len(last_chunk) == 0:
                return 0.0

            # Calculate RMS
            rms = np.sqrt(np.mean(last_chunk.astype(np.float32) ** 2))
            # Normalize for int16
            if self.dtype == "int16":
                rms = rms / 32768.0

            return min(rms, 1.0)