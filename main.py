"""
EasySpeak - System-wide AI Dictation Tool for Windows
Main entry point.
"""

import os
import sys
import threading
import time
import traceback
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from core.audio_recorder import AudioRecorder
from core.hotkey_manager import HotkeyManager, HotkeyMode
from core.llm_processor import create_llm_processor
from core.text_inserter import create_text_inserter
from core.transcriber import create_transcriber
from ui.floating_pill import get_pill_manager
from ui.system_tray import create_system_tray
from utils.config_manager import get_config


class EasySpeakApp:
    """Main application class for EasySpeak."""

    def __init__(self):
        """Initialize the application."""
        self.config = get_config()

        # Core components
        self.audio_recorder = AudioRecorder(gain=self.config.get("audio.gain", 20.0))
        self.transcriber = create_transcriber()
        self.llm_processor = create_llm_processor()
        self.text_inserter = create_text_inserter()

        # UI components
        self.pill_manager = get_pill_manager()
        self.system_tray = create_system_tray(
            on_toggle=self._on_toggle,
            on_mode_change=self._on_mode_change,
            on_launch_toggle=self._on_launch_toggle,
            on_settings=self._on_settings,
            on_quit=self._on_quit
        )

        # Hotkey manager
        from core.hotkey_manager import create_hotkey_manager
        self.hotkey_manager = create_hotkey_manager(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
            on_double_tap=self._on_hotkey_double_tap,
            on_esc=self._on_hotkey_esc
        )

        # State
        self._running = False
        self._recording = False
        self._processing = False
        self._hands_free = False
        self._auto_stop_timer: threading.Timer = None
        self._lock = threading.Lock()

        # Auto-stop time (5 minutes default)
        self._auto_stop_seconds = self.config.get("auto_stop_minutes", 5) * 60

    def _on_toggle(self, enabled: bool) -> None:
        """Handle enable/disable toggle."""
        if not enabled:
            self._cancel_all()
        print(f"Dictation {'enabled' if enabled else 'disabled'}")

    def _on_mode_change(self, mode: str) -> None:
        """Handle transcription mode change."""
        print(f"Transcription mode changed to: {mode}")
        # Recreate transcriber
        self.transcriber = create_transcriber()

    def _on_launch_toggle(self, enabled: bool) -> None:
        """Handle launch at login toggle."""
        print(f"Launch at login {'enabled' if enabled else 'disabled'}")

    def _on_settings(self) -> None:
        """Handle settings request."""
        # Open config file in default editor
        config_path = Path(__file__).parent / "config.json"
        os.startfile(str(config_path))

    def _on_quit(self) -> None:
        """Handle quit request."""
        self.stop()

    def _on_hotkey_press(self) -> None:
        """Handle hotkey press (hold-to-talk start)."""
        if not self.system_tray.enabled:
            return

        with self._lock:
            if self._recording or self._processing:
                return

            if self.hotkey_manager.current_mode == HotkeyMode.HOLD_TO_TALK:
                self._start_recording()

    def _on_hotkey_release(self) -> None:
        """Handle hotkey release (hold-to-talk end)."""
        if not self.system_tray.enabled:
            return

        with self._lock:
            if self._recording and not self._hands_free:
                self._stop_recording()

    def _on_hotkey_double_tap(self) -> None:
        """Handle double-tap (hands-free toggle)."""
        if not self.system_tray.enabled:
            return

        with self._lock:
            if self._recording or self._processing:
                return

            self._hands_free = not self._hands_free

            if self._hands_free:
                self._start_recording(hands_free=True)
            else:
                self._stop_recording()

    def _on_hotkey_esc(self) -> None:
        """Handle Esc key (cancel)."""
        with self._lock:
            if self._recording:
                self._cancel_recording()
            elif self._processing:
                self._cancel_processing()

    def _start_recording(self, hands_free: bool = False) -> None:
        """Start audio recording."""
        if self._recording:
            return

        self._recording = True
        self._hands_free = hands_free
        self._processing = False

        # Update UI
        if hands_free:
            self.pill_manager.show_hands_free()
        else:
            self.pill_manager.show_recording()

        self.system_tray.set_recording(True)

        # Start audio recording
        success = self.audio_recorder.start_recording()
        if not success:
            print("Failed to start recording")
            self._recording = False
            self.pill_manager.hide()
            self.system_tray.set_recording(False)
            return

        # Start auto-stop timer for hands-free mode
        if hands_free:
            self._start_auto_stop_timer()

        print("Recording started" + (" (hands-free)" if hands_free else ""))

    def _stop_recording(self) -> None:
        """Stop recording and start transcription."""
        if not self._recording:
            return

        self._recording = False
        self._cancel_auto_stop_timer()

        # Update UI
        self.pill_manager.show_transcribing()
        self.system_tray.set_recording(False)
        self.system_tray.set_processing(True)
        self._processing = True

        # Get audio file
        audio_path = self.audio_recorder.stop_recording()

        if audio_path:
            # Process in background thread
            threading.Thread(
                target=self._process_audio,
                args=(audio_path,),
                daemon=True
            ).start()
        else:
            print("No audio recorded")
            self._finish_processing()

    def _cancel_recording(self) -> None:
        """Cancel current recording."""
        if not self._recording:
            return

        print("Recording cancelled")
        self._recording = False
        self._cancel_auto_stop_timer()
        self.audio_recorder.cancel_recording()
        self._finish_processing()

    def _cancel_processing(self) -> None:
        """Cancel current transcription/processing."""
        if not self._processing:
            return

        print("Processing cancelled")
        self._finish_processing()

    def _process_audio(self, audio_path: str) -> None:
        """
        Process audio: transcribe -> LLM cleanup -> insert text.

        Args:
            audio_path: Path to recorded audio file
        """
        try:
            # Transcribe
            print("Transcribing...")
            transcript = self.transcriber.transcribe(audio_path)

            if not transcript or not transcript.strip():
                print("Empty transcript")
                self._finish_processing()
                return

            print(f"Transcript: {transcript}")

            # Detect language for LLM decision
            # If transcript contains non-ASCII chars likely Turkish, skip LLM
            language = "en"  # default to English
            if any(ord(c) > 127 for c in transcript):
                # Likely contains non-English characters - check if Turkish-like
                turkish_chars = sum(1 for c in transcript if c in 'ğüşıöçĞÜŞİÖÇ')
                if turkish_chars > 0:
                    language = "tr"

            # LLM cleanup - skip for non-English languages
            if self.config.get("llm.enabled", True) and language == "en":
                print("Processing with LLM...")
                transcript = self.llm_processor.process(transcript, language=language)
                print(f"Cleaned: {transcript}")
            else:
                print(f"Skipping LLM (language: {language})")

            # Insert text
            print("Inserting text...")
            self.text_inserter.insert_text(transcript)

        except Exception as e:
            print(f"Processing error: {e}")
            traceback.print_exc()
        finally:
            # Clean up temp file
            try:
                if audio_path and os.path.exists(audio_path):
                    os.remove(audio_path)
            except Exception:
                pass

            self._finish_processing()

    def _finish_processing(self) -> None:
        """Finish processing and update UI."""
        self._processing = False
        self._hands_free = False

        # Update UI - thread-safe
        self.pill_manager.hide_threadsafe()
        self.system_tray.set_processing(False)
        self.system_tray.set_recording(False)

    def _start_auto_stop_timer(self) -> None:
        """Start auto-stop timer for hands-free mode."""
        self._cancel_auto_stop_timer()
        self._auto_stop_timer = threading.Timer(
            self._auto_stop_seconds,
            self._auto_stop
        )
        self._auto_stop_timer.daemon = True
        self._auto_stop_timer.start()

    def _cancel_auto_stop_timer(self) -> None:
        """Cancel auto-stop timer."""
        if self._auto_stop_timer:
            self._auto_stop_timer.cancel()
            self._auto_stop_timer = None

    def _auto_stop(self) -> None:
        """Auto-stop after timeout."""
        with self._lock:
            if self._recording and self._hands_free:
                print("Auto-stop after timeout")
                self._stop_recording()

    def _cancel_all(self) -> None:
        """Cancel all operations."""
        with self._lock:
            if self._recording:
                self._cancel_recording()
            elif self._processing:
                self._cancel_processing()

    def start(self) -> bool:
        """
        Start the application.

        Returns:
            True if started successfully
        """
        if self._running:
            return False

        print("Starting EasySpeak...")

        # Initialize UI
        self.pill_manager.initialize()

        # Start hotkey listener
        if not self.hotkey_manager.start():
            print("Failed to start hotkey listener")
            return False

        # Start system tray
        self.system_tray.run()

        self._running = True
        print("EasySpeak started")
        print(f"Hotkey: {self.config.get('hotkey.key')}")
        print(f"Mode: {self.config.get('transcription.mode')}")
        print("Press hotkey to start recording, double-tap for hands-free")
        print("Esc to cancel")

        return True

    def stop(self) -> None:
        """Stop the application."""
        if not self._running:
            return

        print("Stopping EasySpeak...")
        self._running = False

        # Cancel any ongoing operations
        self._cancel_all()

        # Stop components
        self.hotkey_manager.stop()
        self.system_tray.quit()

        print("EasySpeak stopped")

    def run(self) -> int:
        """
        Run the main event loop.

        Returns:
            Exit code
        """
        if not self.start():
            return 1

        import signal

        def signal_handler(sig, frame):
            print("\nInterrupted")
            self.stop()
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        try:
            # Main loop - process Qt events
            while self._running:
                self.pill_manager.process_events()
                time.sleep(0.016)  # ~60 FPS
        except KeyboardInterrupt:
            print("\nInterrupted")
        finally:
            self.stop()

        return 0


def main():
    """Main entry point."""
    app = EasySpeakApp()
    return app.run()


if __name__ == "__main__":
    sys.exit(main())