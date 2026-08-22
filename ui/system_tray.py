"""
System tray for EasySpeak.
Provides menu for toggling, settings, and quit.
Catppuccin Mocha inspired theme.
"""

import os
import sys
import threading
from typing import Callable, Optional

import pystray
from PIL import Image, ImageDraw

from utils.config_manager import get_config


class SystemTray:
    """System tray icon and menu for EasySpeak."""

    # Catppuccin Mocha Color Palette
    CRUST = (0x11, 0x11, 0x1b)      # #11111b
    MANTLE = (0x18, 0x18, 0x25)     # #181825
    BASE = (0x1e, 0x1e, 0x2e)       # #1e1e2e
    SURFACE0 = (0x31, 0x32, 0x44)   # #313244
    SURFACE1 = (0x45, 0x47, 0x5a)   # #45475a
    SURFACE2 = (0x58, 0x5b, 0x70)   # #585b70

    TEXT = (0xcd, 0xd6, 0xf4)       # #cdd6f4
    SUBTEXT1 = (0xba, 0xc2, 0xde)   # #bac2de
    SUBTEXT0 = (0xa6, 0xad, 0xc8)   # #a6adc8
    OVERLAY2 = (0x93, 0x99, 0xb2)   # #9399b2
    OVERLAY1 = (0x7f, 0x84, 0x9c)   # #7f849c
    OVERLAY0 = (0x6c, 0x70, 0x86)   # #6c7086

    BLUE = (0x89, 0xb4, 0xfa)       # #89b4fa
    LAVENDER = (0xb4, 0xbe, 0xfe)   # #b4befe
    SAPPHIRE = (0x74, 0xc7, 0xec)   # #74c7ec
    SKY = (0x89, 0xdc, 0xeb)        # #89dceb
    TEAL = (0x94, 0xe2, 0xd5)       # #94e2d5
    GREEN = (0xa6, 0xe3, 0xa1)      # #a6e3a1
    YELLOW = (0xf9, 0xe2, 0xaf)     # #f9e2af
    PEACH = (0xfa, 0xb3, 0x87)      # #fab387
    MAROON = (0xeb, 0xa0, 0xac)     # #eba0ac
    RED = (0xf3, 0x8b, 0xa8)        # #f38ba8
    PINK = (0xf5, 0xc2, 0xe7)       # #f5c2e7
    FLAMINGO = (0xf2, 0xcd, 0xcd)   # #f2cdcd
    ROSEWATER = (0xf5, 0xe0, 0xdc)  # #f5e0dc
    MAUVE = (0xca, 0x9e, 0xeb)      # #ca9eeb

    # Custom recording red (user specified)
    RECORDING_RED = (0xf7, 0x76, 0x8e)  # #f7768e

    def __init__(
        self,
        on_toggle: Optional[Callable] = None,
        on_mode_change: Optional[Callable] = None,
        on_launch_toggle: Optional[Callable] = None,
        on_settings: Optional[Callable] = None,
        on_quit: Optional[Callable] = None
    ):
        """
        Initialize system tray.

        Args:
            on_toggle: Callback for enable/disable toggle
            on_mode_change: Callback for transcription mode change
            on_launch_toggle: Callback for launch at login toggle
            on_settings: Callback for opening settings
            on_quit: Callback for quit application
        """
        self.on_toggle = on_toggle
        self.on_mode_change = on_mode_change
        self.on_launch_toggle = on_launch_toggle
        self.on_settings = on_settings
        self.on_quit = on_quit

        self._icon: Optional[pystray.Icon] = None
        self._enabled = True
        self._mode = "local"  # local or api
        self._launch_at_login = False
        self._thread: Optional[threading.Thread] = None
        self._running = False

        # Load config
        config = get_config()
        self._enabled = config.get("transcription.enabled", True)
        self._mode = config.get("transcription.mode", "local")
        self._launch_at_login = config.get("launch_at_login", False)

    def _create_icon_image(self, recording: bool = False, processing: bool = False) -> Image.Image:
        """Create tray icon image - Catppuccin Mocha theme."""
        # Create a 64x64 image
        size = 64
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # Catppuccin Mocha colors
        bg_color = self.BASE + (255,)           # #1e1e2e
        border_color = self.SURFACE1 + (200,)   # #45475a
        mic_color = self.TEXT + (255,)          # #cdd6f4
        recording_color = self.RECORDING_RED + (255,)  # #f7768e
        processing_color = self.SAPPHIRE + (255,)      # #74c7ec
        disabled_overlay = (100, 100, 100, 128)

        margin = 4

        # Background circle with subtle border
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=bg_color,
            outline=border_color,
            width=2
        )

        # Microphone icon in Catppuccin Text color
        mic_x = size // 2
        mic_y = size // 2 - 4

        # Mic body
        draw.rectangle(
            [mic_x - 6, mic_y - 10, mic_x + 6, mic_y + 2],
            fill=mic_color
        )
        # Mic stand
        draw.rectangle(
            [mic_x - 10, mic_y + 2, mic_x + 10, mic_y + 4],
            fill=mic_color
        )
        # Mic base (curved)
        draw.ellipse(
            [mic_x - 12, mic_y + 4, mic_x + 12, mic_y + 12],
            fill=mic_color
        )

        # Recording indicator (single red dot at top-right)
        if recording:
            draw.ellipse(
                [size - 18, margin + 2, size - 6, margin + 14],
                fill=recording_color
            )

        # Processing indicator (sapphire dot)
        if processing:
            draw.ellipse(
                [size - 18, margin + 2, size - 6, margin + 14],
                fill=processing_color
            )

        # Disabled indicator (gray overlay)
        if not self._enabled:
            overlay = Image.new("RGBA", (size, size), disabled_overlay)
            img = Image.alpha_composite(img, overlay)

        return img

    def _update_icon(self, recording: bool = False, processing: bool = False) -> None:
        """Update tray icon."""
        if self._icon:
            self._icon.icon = self._create_icon_image(recording, processing)

    def _create_menu(self) -> pystray.Menu:
        """Create tray menu."""
        config = get_config()

        def make_toggle_callback(item):
            def callback(icon, item):
                self._enabled = not self._enabled
                config.set("transcription.enabled", self._enabled)
                config.save_config()
                self._update_icon()
                if self.on_toggle:
                    self.on_toggle(self._enabled)
            return callback

        def make_mode_callback(mode):
            def callback(icon, item):
                self._mode = mode
                config.set("transcription.mode", mode)
                config.save_config()
                if self.on_mode_change:
                    self.on_mode_change(mode)
            return callback

        def make_launch_callback(item):
            def callback(icon, item):
                self._launch_at_login = not self._launch_at_login
                config.set("launch_at_login", self._launch_at_login)
                config.save_config()
                self._update_launch_at_login()
                if self.on_launch_toggle:
                    self.on_launch_toggle(self._launch_at_login)
            return callback

        menu_items = [
            pystray.MenuItem(
                "Enabled",
                make_toggle_callback(None),
                checked=lambda item: self._enabled
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Transcription Mode",
                pystray.Menu(
                    pystray.MenuItem(
                        "Local (Whisper)",
                        make_mode_callback("local"),
                        checked=lambda item: self._mode == "local",
                        radio=True
                    ),
                    pystray.MenuItem(
                        "API (Groq/OpenAI)",
                        make_mode_callback("api"),
                        checked=lambda item: self._mode == "api",
                        radio=True
                    )
                )
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Launch at Login",
                make_launch_callback(None),
                checked=lambda item: self._launch_at_login
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                "Settings",
                lambda icon, item: self.on_settings() if self.on_settings else None
            ),
            pystray.MenuItem(
                "Quit",
                lambda icon, item: self.quit()
            )
        ]

        return pystray.Menu(*menu_items)

    def _update_launch_at_login(self) -> None:
        """Update Windows startup registry entry."""
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            app_name = "EasySpeak"
            exe_path = sys.executable
            script_path = os.path.abspath(sys.argv[0])

            # Use pythonw for no console window
            if exe_path.endswith("python.exe"):
                exe_path = exe_path.replace("python.exe", "pythonw.exe")

            command = f'"{exe_path}" "{script_path}"'

            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_ALL_ACCESS) as key:
                if self._launch_at_login:
                    winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, command)
                else:
                    try:
                        winreg.DeleteValue(key, app_name)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            print(f"Failed to update launch at login: {e}")

    def run(self) -> None:
        """Run the system tray in a separate thread."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._run_tray, daemon=True)
        self._thread.start()

    def _run_tray(self) -> None:
        """Run the tray icon loop."""
        menu = self._create_menu()
        self._icon = pystray.Icon(
            "EasySpeak",
            self._create_icon_image(),
            "EasySpeak - AI Dictation",
            menu
        )
        self._icon.run()

    def quit(self) -> None:
        """Quit the application."""
        self._running = False
        if self._icon:
            self._icon.stop()
        if self.on_quit:
            self.on_quit()

    def set_recording(self, recording: bool) -> None:
        """Update icon for recording state."""
        self._update_icon(recording=recording)

    def set_processing(self, processing: bool) -> None:
        """Update icon for processing state."""
        self._update_icon(processing=processing)

    @property
    def enabled(self) -> bool:
        """Check if dictation is enabled."""
        return self._enabled

    @property
    def mode(self) -> str:
        """Get current transcription mode."""
        return self._mode


def create_system_tray(
    on_toggle: Optional[Callable] = None,
    on_mode_change: Optional[Callable] = None,
    on_launch_toggle: Optional[Callable] = None,
    on_settings: Optional[Callable] = None,
    on_quit: Optional[Callable] = None
) -> SystemTray:
    """Create system tray from configuration."""
    return SystemTray(
        on_toggle=on_toggle,
        on_mode_change=on_mode_change,
        on_launch_toggle=on_launch_toggle,
        on_settings=on_settings,
        on_quit=on_quit
    )