"""
Global hotkey manager for EasySpeak.
Detects hold-to-talk, double-tap, and Esc key events.
Supports modifier+key combinations (e.g., Alt+CapsLock).
"""

import threading
import time
from enum import Enum
from typing import Callable, Optional

from pynput import keyboard


class HotkeyMode(Enum):
    """Hotkey interaction modes."""
    IDLE = "idle"
    HOLD_TO_TALK = "hold_to_talk"
    HANDS_FREE = "hands_free"


class HotkeyEvent(Enum):
    """Hotkey events."""
    PRESS = "press"
    RELEASE = "release"
    DOUBLE_TAP = "double_tap"
    ESC = "esc"


class HotkeyManager:
    """
    Manages global hotkey detection for dictation.

    Modes:
    - Hold-to-talk: Press and hold key -> record, release -> transcribe
    - Hands-free: Double-tap -> start recording, tap -> stop recording
    - Esc: Cancel recording or transcription

    Hotkey format: "alt+caps_lock", "ctrl+shift+space", etc.
    """

    def __init__(
        self,
        hotkey: str = "alt+caps_lock",
        double_tap_threshold_ms: int = 300,
        on_press: Optional[Callable] = None,
        on_release: Optional[Callable] = None,
        on_double_tap: Optional[Callable] = None,
        on_esc: Optional[Callable] = None
    ):
        """
        Initialize hotkey manager.

        Args:
            hotkey: Key combination to use as hotkey (e.g., "alt+caps_lock")
            double_tap_threshold_ms: Max time between taps for double-tap (ms)
            on_press: Callback for key press (hold-to-talk start)
            on_release: Callback for key release (hold-to-talk end)
            on_double_tap: Callback for double-tap (hands-free toggle)
            on_esc: Callback for Esc key (cancel)
        """
        self.hotkey = hotkey
        self.double_tap_threshold = double_tap_threshold_ms / 1000.0  # Convert to seconds

        self.on_press = on_press
        self.on_release = on_release
        self.on_double_tap = on_double_tap
        self.on_esc = on_esc

        self._listener: Optional[keyboard.Listener] = None
        self._running = False

        # State tracking
        self._mode = HotkeyMode.IDLE
        self._last_press_time = 0.0
        self._press_time = 0.0
        self._key_held = False
        self._hands_free_active = False
        self._lock = threading.Lock()

        # Modifier key state
        self._alt_pressed = False
        self._ctrl_pressed = False
        self._shift_pressed = False

        # Parse hotkey string to modifier requirements and target key
        self._required_modifiers, self._target_key = self._parse_hotkey(hotkey)

    def _parse_hotkey(self, hotkey_str: str) -> tuple:
        """
        Parse hotkey string like "alt+caps_lock" into (modifiers_set, target_key).

        Returns:
            tuple: (set of required modifiers, target_key)
        """
        parts = hotkey_str.lower().split('+')

        modifiers = set()
        target_key_str = parts[-1]  # Last part is the target key

        for part in parts[:-1]:
            if part in ('alt', 'option'):
                modifiers.add('alt')
            elif part in ('ctrl', 'control'):
                modifiers.add('ctrl')
            elif part in ('shift',):
                modifiers.add('shift')

        target_key = self._parse_key(target_key_str)
        return modifiers, target_key

    def _parse_key(self, key_str: str) -> keyboard.Key:
        """Parse key string to pynput Key object."""
        # Handle special keys with Key. prefix
        if key_str.startswith("Key."):
            key_name = key_str[4:]
            return getattr(keyboard.Key, key_name, keyboard.Key.caps_lock)

        # Handle bare special key names (ctrl_r, alt_l, shift_r, etc.)
        if hasattr(keyboard.Key, key_str):
            return getattr(keyboard.Key, key_str)

        # Handle regular character keys
        try:
            return keyboard.KeyCode.from_char(key_str)
        except ValueError:
            return keyboard.Key.caps_lock

    def _check_modifiers(self) -> bool:
        """Check if required modifiers are currently pressed."""
        if 'alt' in self._required_modifiers and not self._alt_pressed:
            return False
        if 'ctrl' in self._required_modifiers and not self._ctrl_pressed:
            return False
        if 'shift' in self._required_modifiers and not self._shift_pressed:
            return False
        return True

    def start(self) -> bool:
        """
        Start listening for hotkeys.

        Returns:
            True if started successfully
        """
        with self._lock:
            if self._running:
                return False

            self._running = True
            self._listener = keyboard.Listener(
                on_press=self._on_key_press,
                on_release=self._on_key_release,
                suppress=False  # Don't suppress keys, let them pass through
            )
            self._listener.start()
            return True

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        with self._lock:
            if not self._running:
                return

            self._running = False
            if self._listener:
                self._listener.stop()
                self._listener = None

    def _on_key_press(self, key: keyboard.Key) -> None:
        """Handle key press event."""
        # Track modifier keys
        if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            self._alt_pressed = True
            return
        elif key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self._ctrl_pressed = True
            return
        elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            self._shift_pressed = True
            return

        # Check for Esc key (always handled, passes through)
        if key == keyboard.Key.esc:
            if self.on_esc:
                self.on_esc()
            return

        # Check if it's our hotkey AND required modifiers are pressed
        if not self._is_target_key(key):
            return

        if not self._check_modifiers():
            return

        current_time = time.time()

        with self._lock:
            if self._mode == HotkeyMode.IDLE:
                # First press - could be hold-to-talk or first tap of double-tap
                self._key_held = True
                self._press_time = current_time
                self._last_press_time = current_time
                self._mode = HotkeyMode.HOLD_TO_TALK

                if self.on_press:
                    self.on_press()

            elif self._mode == HotkeyMode.HOLD_TO_TALK:
                # Already holding, ignore repeated press events
                pass

            elif self._mode == HotkeyMode.HANDS_FREE:
                # In hands-free mode, any press stops recording
                self._hands_free_active = False
                self._mode = HotkeyMode.IDLE

                if self.on_release:
                    self.on_release()

    def _on_key_release(self, key: keyboard.Key) -> None:
        """Handle key release event."""
        # Track modifier key releases
        if key == keyboard.Key.alt_l or key == keyboard.Key.alt_r:
            self._alt_pressed = False
            return
        elif key == keyboard.Key.ctrl_l or key == keyboard.Key.ctrl_r:
            self._ctrl_pressed = False
            return
        elif key == keyboard.Key.shift_l or key == keyboard.Key.shift_r:
            self._shift_pressed = False
            return

        if not self._is_target_key(key):
            return

        current_time = time.time()

        with self._lock:
            if self._mode == HotkeyMode.HOLD_TO_TALK:
                hold_duration = current_time - self._press_time

                # If held for longer than double-tap threshold, it's hold-to-talk
                if hold_duration > self.double_tap_threshold:
                    # Normal hold-to-talk release
                    self._key_held = False
                    self._mode = HotkeyMode.IDLE

                    if self.on_release:
                        self.on_release()
                else:
                    # Quick tap - check if it's a double-tap
                    time_since_last_press = current_time - self._last_press_time

                    if time_since_last_press <= self.double_tap_threshold:
                        # Double-tap detected - switch to hands-free mode
                        self._mode = HotkeyMode.HANDS_FREE
                        self._hands_free_active = True
                        self._key_held = False

                        if self.on_double_tap:
                            self.on_double_tap()
                    else:
                        # Single tap - wait for potential second tap
                        self._last_press_time = current_time
                        self._key_held = False
                        # Stay in HOLD_TO_TALK mode briefly to catch double-tap
                        # The mode will be reset to IDLE if no second tap comes

            elif self._mode == HotkeyMode.HANDS_FREE:
                # In hands-free mode, release doesn't do anything
                # (stop is triggered by another press)
                pass

    def _is_target_key(self, key: keyboard.Key) -> bool:
        """Check if key matches our target hotkey."""
        if isinstance(self._target_key, keyboard.Key):
            return key == self._target_key
        elif isinstance(self._target_key, keyboard.KeyCode):
            return key == self._target_key
        return False

    @property
    def is_hands_free_active(self) -> bool:
        """Check if hands-free mode is active."""
        return self._hands_free_active

    @property
    def current_mode(self) -> HotkeyMode:
        """Get current hotkey mode."""
        return self._mode


def create_hotkey_manager(
    on_press: Optional[Callable] = None,
    on_release: Optional[Callable] = None,
    on_double_tap: Optional[Callable] = None,
    on_esc: Optional[Callable] = None
) -> HotkeyManager:
    """Create hotkey manager from configuration."""
    from utils.config_manager import get_config
    config = get_config()
    hotkey = config.get("hotkey.key", "Key.caps_lock")
    threshold = config.get("hotkey.double_tap_threshold_ms", 300)
    return HotkeyManager(
        hotkey=hotkey,
        double_tap_threshold_ms=threshold,
        on_press=on_press,
        on_release=on_release,
        on_double_tap=on_double_tap,
        on_esc=on_esc
    )