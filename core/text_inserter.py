"""
Text inserter for EasySpeak.
Handles clipboard operations and simulated keystrokes for text insertion.
"""

import time
import threading
from typing import Optional

import pyautogui
import pyperclip


class TextInserter:
    """Inserts text at current cursor position using clipboard and keystrokes."""

    def __init__(
        self,
        restore_previous: bool = True,
        restore_delay: float = 2.0
    ):
        """
        Initialize the text inserter.

        Args:
            restore_previous: Whether to restore previous clipboard content
            restore_delay: Delay in seconds before restoring clipboard
        """
        self.restore_previous = restore_previous
        self.restore_delay = restore_delay
        self._previous_clipboard: Optional[str] = None
        self._restore_timer: Optional[threading.Timer] = None

    def insert_text(self, text: str) -> bool:
        """
        Insert text at current cursor position.

        Args:
            text: Text to insert

        Returns:
            True if successful, False otherwise
        """
        if not text:
            return False

        # Save previous clipboard if needed
        if self.restore_previous:
            self._save_clipboard()

        # Copy new text to clipboard
        try:
            pyperclip.copy(text)
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")
            return False

        # Small delay to ensure clipboard is set
        time.sleep(0.05)

        # Simulate Ctrl+V (paste)
        try:
            pyautogui.hotkey("ctrl", "v")
        except Exception as e:
            print(f"Failed to simulate paste: {e}")
            return False

        # Schedule clipboard restoration
        if self.restore_previous and self._previous_clipboard is not None:
            self._schedule_restore()

        return True

    def _save_clipboard(self) -> None:
        """Save current clipboard content."""
        try:
            self._previous_clipboard = pyperclip.paste()
        except Exception:
            self._previous_clipboard = None

    def _schedule_restore(self) -> None:
        """Schedule clipboard restoration after delay."""
        if self._restore_timer:
            self._restore_timer.cancel()

        self._restore_timer = threading.Timer(
            self.restore_delay,
            self._restore_clipboard
        )
        self._restore_timer.daemon = True
        self._restore_timer.start()

    def _restore_clipboard(self) -> None:
        """Restore previous clipboard content."""
        if self._previous_clipboard is not None:
            try:
                pyperclip.copy(self._previous_clipboard)
            except Exception as e:
                print(f"Failed to restore clipboard: {e}")

    def cancel_restore(self) -> None:
        """Cancel scheduled clipboard restoration."""
        if self._restore_timer:
            self._restore_timer.cancel()
            self._restore_timer = None


def create_text_inserter() -> TextInserter:
    """Create text inserter based on configuration."""
    from utils.config_manager import get_config
    config = get_config()
    restore = config.get("clipboard.restore_previous", True)
    delay = config.get("clipboard.restore_delay_seconds", 2.0)
    return TextInserter(restore_previous=restore, restore_delay=delay)