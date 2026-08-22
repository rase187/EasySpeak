"""
Floating pill UI for EasySpeak.
Shows recording status as a small overlay window.
Catppuccin Mocha inspired theme.
"""

import sys
from typing import Optional

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, QMetaObject, Q_ARG, pyqtSlot
from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QFont, QFontMetrics
from PyQt6.QtWidgets import QApplication, QWidget


class FloatingPill(QWidget):
    """Floating pill indicator showing recording status."""

    # Pill states
    IDLE = "idle"
    RECORDING = "recording"
    HANDS_FREE = "hands_free"
    TRANSCRIBING = "transcribing"

    # Catppuccin Mocha Color Palette (tokens)
    # Base colors
    CRUST = QColor(0x11, 0x11, 0x1b)      # #11111b
    MANTLE = QColor(0x18, 0x18, 0x25)     # #181825
    BASE = QColor(0x1e, 0x1e, 0x2e)       # #1e1e2e
    SURFACE0 = QColor(0x31, 0x32, 0x44)   # #313244
    SURFACE1 = QColor(0x45, 0x47, 0x5a)   # #45475a
    SURFACE2 = QColor(0x58, 0x5b, 0x70)   # #585b70

    # Text colors
    TEXT = QColor(0xcd, 0xd6, 0xf4)       # #cdd6f4
    SUBTEXT1 = QColor(0xba, 0xc2, 0xde)   # #bac2de
    SUBTEXT0 = QColor(0xa6, 0xad, 0xc8)   # #a6adc8
    OVERLAY2 = QColor(0x93, 0x99, 0xb2)   # #9399b2
    OVERLAY1 = QColor(0x7f, 0x84, 0x9c)   # #7f849c
    OVERLAY0 = QColor(0x6c, 0x70, 0x86)   # #6c7086

    # Accent colors (Catppuccin Mocha)
    BLUE = QColor(0x89, 0xb4, 0xfa)       # #89b4fa
    LAVENDER = QColor(0xb4, 0xbe, 0xfe)   # #b4befe
    SAPPHIRE = QColor(0x74, 0xc7, 0xec)   # #74c7ec
    SKY = QColor(0x89, 0xdc, 0xeb)        # #89dceb
    TEAL = QColor(0x94, 0xe2, 0xd5)       # #94e2d5
    GREEN = QColor(0xa6, 0xe3, 0xa1)      # #a6e3a1
    YELLOW = QColor(0xf9, 0xe2, 0xaf)     # #f9e2af
    PEACH = QColor(0xfa, 0xb3, 0x87)      # #fab387
    MAROON = QColor(0xeb, 0xa0, 0xac)     # #eba0ac
    RED = QColor(0xf3, 0x8b, 0xa8)        # #f38ba8 (Catppuccin red)
    PINK = QColor(0xf5, 0xc2, 0xe7)       # #f5c2e7
    FLAMINGO = QColor(0xf2, 0xcd, 0xcd)   # #f2cdcd
    ROSEWATER = QColor(0xf5, 0xe0, 0xdc)  # #f5e0dc
    MAUVE = QColor(0xca, 0x9e, 0xeb)      # #ca9eeb (Catppuccin Mauve)

    # Custom recording red (user specified)
    RECORDING_RED = QColor(0xf7, 0x76, 0x8e)  # #f7768e

    def __init__(self):
        """Initialize the floating pill."""
        super().__init__()

        # Window setup
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool |
            Qt.WindowType.WindowTransparentForInput
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)

        # State
        self._state = self.IDLE
        self._text = ""
        self._visible = False

        # Appearance - Catppuccin Mocha theme
        self._padding_x = 16
        self._padding_y = 10
        self._radius = 10
        self._dot_size = 8
        self._gap = 8  # gap between dot and text

        # Background - Catppuccin Base with slight transparency
        self._bg_color = QColor(self.BASE.red(), self.BASE.green(), self.BASE.blue(), 240)

        # Border - subtle Catppuccin Surface1
        self._border_color = QColor(self.SURFACE1.red(), self.SURFACE1.green(), self.SURFACE1.blue(), 180)

        # Text color - Catppuccin Text
        self._text_color = self.TEXT

        # State accent colors
        self._recording_color = self.RECORDING_RED      # User's custom red
        self._hands_free_color = self.MAUVE             # Catppuccin Mauve
        self._transcribing_color = self.SAPPHIRE        # Catppuccin Sapphire

        # Font - JetBrains Mono
        self._font = QFont("JetBrains Mono", 10)
        self._font.setWeight(QFont.Weight.Medium)

        # Auto-hide timer
        self._hide_timer = QTimer()
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self._hide_pill_now)

        # Initialize UI
        self._update_text()
        self._update_size()
        self.hide()

    def _update_text(self) -> None:
        """Update display text based on state."""
        if self._state == self.RECORDING:
            self._text = "Recording..."
        elif self._state == self.HANDS_FREE:
            self._text = "Hands-Free"
        elif self._state == self.TRANSCRIBING:
            self._text = "Transcribing..."
        else:
            self._text = ""

    def _update_size(self) -> None:
        """Update widget size based on text."""
        metrics = QFontMetrics(self._font)
        text_width = metrics.horizontalAdvance(self._text)
        text_height = metrics.height()

        # Width = padding_left + dot + gap + text + padding_right
        width = self._padding_x + self._dot_size + self._gap + text_width + self._padding_x
        height = max(text_height, self._dot_size) + self._padding_y * 2

        self.setFixedSize(width, height)

    def show_pill(self, state: str) -> None:
        """
        Show the pill with given state.

        Args:
            state: One of IDLE, RECORDING, HANDS_FREE, TRANSCRIBING
        """
        self._state = state
        self._update_text()
        self._update_size()
        self._position_pill()
        self.show()
        self._visible = True
        self.raise_()

        # Cancel any pending hide
        self._hide_timer.stop()

    @pyqtSlot(int)
    def hide_pill(self, delay: int = 500) -> None:
        """
        Hide the pill after optional delay.

        Args:
            delay: Delay in milliseconds before hiding
        """
        if delay > 0:
            self._hide_timer.start(delay)
        else:
            self._hide_timer.stop()
            self.hide()
            self._visible = False

    @pyqtSlot()
    def _hide_pill_now(self) -> None:
        """Slot for timer timeout - hides immediately."""
        self._hide_timer.stop()
        self.hide()
        self._visible = False

    def _position_pill(self) -> None:
        """Position pill at screen center-bottom (consistent position)."""
        try:
            screen = QApplication.primaryScreen()
            if screen:
                geometry = screen.availableGeometry()
                # Center-bottom of primary screen
                x = (geometry.width() - self.width()) // 2
                y = geometry.height() - self.height() - 80
                self.move(x, y)
            else:
                self.move(100, 100)
        except Exception:
            self.move(100, 100)

    def paintEvent(self, event) -> None:
        """Paint the pill - Catppuccin Mocha style."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Determine accent color based on state
        if self._state == self.RECORDING:
            accent = self._recording_color
        elif self._state == self.HANDS_FREE:
            accent = self._hands_free_color
        elif self._state == self.TRANSCRIBING:
            accent = self._transcribing_color
        else:
            accent = self._text_color

        rect = self.rect()

        # Draw background rounded rect (Catppuccin Base)
        painter.setBrush(QBrush(self._bg_color))
        painter.setPen(QPen(self._border_color, 1))
        painter.drawRoundedRect(rect.adjusted(0, 0, -1, -1), self._radius, self._radius)

        # Draw single red dot for recording, colored dot for other states
        # Center vertically
        dot_y = (self.height() - self._dot_size) // 2
        dot_x = self._padding_x
        dot_rect = QRect(dot_x, dot_y, self._dot_size, self._dot_size)

        # Draw dot with glow effect for recording
        if self._state == self.RECORDING:
            # Outer glow
            glow_rect = QRect(dot_x - 2, dot_y - 2, self._dot_size + 4, self._dot_size + 4)
            glow_color = QColor(accent.red(), accent.green(), accent.blue(), 60)
            painter.setBrush(QBrush(glow_color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(glow_rect)

        # Main dot
        painter.setBrush(QBrush(accent))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(dot_rect)

        # Draw text - properly vertically centered using font metrics
        painter.setFont(self._font)
        painter.setPen(QPen(self._text_color))
        text_x = self._padding_x + self._dot_size + self._gap
        text_width = self.width() - text_x - self._padding_x

        # Calculate proper vertical centering using font metrics
        metrics = QFontMetrics(self._font)
        # Use boundingRect for exact text dimensions
        text_bounds = metrics.boundingRect(self._text)
        text_height = text_bounds.height()
        # Center text vertically in the widget
        text_y = (self.height() - text_height) // 2 + metrics.ascent()

        # Draw text at calculated position
        painter.drawText(text_x, text_y, self._text)

    def set_state(self, state: str) -> None:
        """Update pill state without showing/hiding."""
        if state != self._state:
            self._state = state
            self._update_text()
            self._update_size()
            self._position_pill()
            self.update()


class PillManager:
    """Manages the floating pill lifecycle."""

    def __init__(self):
        """Initialize pill manager."""
        self._app: Optional[QApplication] = None
        self._pill: Optional[FloatingPill] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initialize Qt application and pill."""
        if self._initialized:
            return

        # Create QApplication if needed
        if QApplication.instance() is None:
            self._app = QApplication(sys.argv)
            self._app.setQuitOnLastWindowClosed(False)
        else:
            self._app = QApplication.instance()

        self._pill = FloatingPill()
        self._initialized = True

    def show_recording(self) -> None:
        """Show pill in recording state."""
        self._ensure_initialized()
        self._pill.show_pill(FloatingPill.RECORDING)

    def show_hands_free(self) -> None:
        """Show pill in hands-free state."""
        self._ensure_initialized()
        self._pill.show_pill(FloatingPill.HANDS_FREE)

    def show_transcribing(self) -> None:
        """Show pill in transcribing state."""
        self._ensure_initialized()
        self._pill.show_pill(FloatingPill.TRANSCRIBING)

    def hide(self, delay: int = 500) -> None:
        """Hide the pill."""
        if self._pill:
            self._pill.hide_pill(delay)

    def process_events(self) -> None:
        """Process Qt events (call periodically from main thread)."""
        if self._app:
            self._app.processEvents()

    def _invoke_in_main_thread(self, func, *args) -> None:
        """Invoke a function in the main Qt thread."""
        if self._app and self._pill:
            QMetaObject.invokeMethod(
                self._pill, func, Qt.ConnectionType.QueuedConnection,
                *[Q_ARG(type(arg), arg) for arg in args]
            )

    def hide_threadsafe(self) -> None:
        """Thread-safe hide pill."""
        if self._pill:
            self._invoke_in_main_thread("hide_pill", 0)

    def _ensure_initialized(self) -> None:
        """Ensure pill is initialized."""
        if not self._initialized:
            self.initialize()


# Global pill manager instance
_pill_manager: Optional[PillManager] = None


def get_pill_manager() -> PillManager:
    """Get global pill manager instance."""
    global _pill_manager
    if _pill_manager is None:
        _pill_manager = PillManager()
    return _pill_manager