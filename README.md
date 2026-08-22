# EasySpeak - System-wide AI Dictation for Windows

A lightweight, privacy-first dictation tool for Windows 10/11. Press a hotkey, speak, and have your words transcribed and inserted at your cursor — powered by local Whisper or cloud APIs, with optional LLM cleanup.

## Features

- **Global hotkey** — Hold to talk, release to transcribe (default: **F9**)
- **Auto-stop** — Recording auto-stops after 5 minutes (configurable)
- **Esc to cancel** — Drop recording or kill transcription instantly
- **Local or cloud transcription** — faster-whisper (offline) or Groq/OpenAI Whisper API
- **Smart language handling** — Auto-detects Turkish/English, restricts to these languages
- **LLM cleanup** — Remove filler words, fix punctuation, proper casing (English only)
- **Clipboard integration** — Text pasted at cursor, also left on clipboard (with auto-restore)
- **Floating pill indicator** — Tiny Catppuccin-themed overlay shows recording state with audio level pulse animation
- **System tray** — Enable/disable, switch modes, microphone selection, launch at login
- **No accounts, no telemetry** — Works fully offline with local model or API

## Quick Start

### 1. Install Python 3.10+
Download from [python.org](https://www.python.org/downloads/) — check "Add Python to PATH" during install.

### 2. Clone and install dependencies
```bash
git clone https://github.com/rase187/EasySpeak.git
cd EasySpeak
pip install -r requirements.txt
```

### 3. Configure (optional)
```bash
copy .env.example .env
# Edit .env with your API keys if using cloud transcription/LLM
```

### 4. Run
```bash
python main.py
```

### 5. Grant Windows Permissions (Required)

**Microphone Access:**
1. Settings → Privacy & security → Microphone
2. Turn on "Microphone access" and "Let apps access your microphone"
3. Ensure "EasySpeak" or "Python" is allowed

**Input Monitoring (for global hotkeys):**
1. Settings → Privacy & security → Input monitoring (or "Other devices" in Win10)
2. Allow "Python" or "EasySpeak" to monitor input

**Run at startup (optional):**
- Enable "Launch at Login" from system tray menu (enabled by default in config)
- Or add a shortcut to `shell:startup` folder

## Usage

| Action | Key |
|--------|-----|
| Hold-to-talk | Hold **F9** (or configured key) |
| Cancel | Press **Esc** |

The floating pill shows:
- 🔴 **Recording...** — Recording active (with pulse animation matching audio level)
- ⏳ **Transcribing...** — Processing audio

## Configuration

Edit `config.json`:

```json
{
  "hotkey": {
    "key": "f9"
  },
  "transcription": {
    "enabled": true,
    "mode": "api",
    "local_model": "base",
    "api_provider": "groq"
  },
  "llm": {
    "enabled": true,
    "provider": "groq",
    "model": "llama-3.1-8b-instant",
    "prompt": "You are a dictation assistant. Clean up this transcript: - Remove filler words (um, uh, like, you know) - Add proper punctuation - Fix capitalization for proper nouns - Keep the natural flow of speech - Don't change the meaning or add words"
  },
  "clipboard": {
    "restore_previous": true,
    "restore_delay_seconds": 2.0
  },
  "audio": {
    "input_device": null,
    "gain": 20.0
  },
  "auto_stop_minutes": 5,
  "launch_at_login": true
}
```

### Hotkey Options
Use any pynput key name:
- `Key.caps_lock`, `Key.ctrl`, `Key.alt`, `Key.shift`
- `Key.f1` through `Key.f12` (e.g., `f9`, `f10`)
- Regular keys: `"a"`, `" "` (space), etc.
- Modifier combinations: `"alt+caps_lock"`, `"ctrl+shift+space"`

The hotkey uses **hold-to-talk**: press and hold to record, release to transcribe.

### Transcription Modes
- **local** — Uses faster-whisper (downloads model on first run, works offline)
- **api** — Uses Groq or OpenAI Whisper API (requires API key in `.env`, faster)

### Local Models (faster-whisper)
| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 39 MB | Fastest | Lower |
| base | 74 MB | Fast | Good |
| small | 244 MB | Medium | Better |
| medium | 769 MB | Slower | Best |
| large | 1.5 GB | Slowest | Best |

### LLM Providers (for transcript cleanup)
- **Groq** (free, fast) — `GROQ_API_KEY` — models: `llama-3.1-8b-instant`, `llama-3.3-70b-versatile`, etc.
- **OpenAI** — `OPENAI_API_KEY` — models: `gpt-4o-mini`, `gpt-4o`, etc.
- **Anthropic** — `ANTHROPIC_API_KEY` — models: `claude-3-5-haiku-latest`, etc.

> **Note:** LLM cleanup only runs for English transcripts. Turkish (and other non-English) transcripts are used as-is.

## Language Support

- **Turkish (tr)** and **English (en)** — fully supported
- Other languages: Transcriber falls back to English
- Language is auto-detected from audio

## Building Standalone Executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name EasySpeak \
  --add-data "config.json;." \
  --add-data ".env;." \
  --add-data "assets/logo_16.png;assets" \
  --add-data "assets/logo_32.png;assets" \
  --add-data "assets/logo_64.png;assets" \
  --hidden-import=faster_whisper \
  --hidden-import=ctranslate2 \
  main.py
```

Output: `dist/EasySpeak.exe`

## Troubleshooting

### Hotkey not working
- Run as Administrator (required for global hotkeys on some systems)
- Check Input Monitoring permission
- Try a different hotkey in config.json (e.g., `f10`, `alt+caps_lock`)

### No microphone input
- Check Microphone privacy settings
- Verify correct input device in Windows Sound settings
- Test with Voice Recorder app
- Adjust `audio.gain` in config.json (default: 20.0) if input is too quiet

### Transcription slow/failed
- Local: First run downloads model (~150 MB for base)
- API: Check API key in `.env` and internet connection
- Reduce model size in config for speed

### Text not inserting
- Ensure target app accepts paste (Ctrl+V)
- Some apps block simulated input — try clicking target field first
- Check clipboard access isn't blocked by security software

### Pill not showing
- Run `python -c "from PyQt6.QtWidgets import QApplication; print('Qt OK')"` to verify Qt
- Try `pip install --upgrade PyQt6`

## Architecture

```
main.py                 # Application entry point
core/
  audio_recorder.py     # Microphone recording (sounddevice, software gain)
  hotkey_manager.py     # Global hotkeys (pynput) — hold-to-talk, Esc
  transcriber.py        # Whisper local/API — tr/en language restriction
  llm_processor.py      # LLM text cleanup (English only)
  text_inserter.py      # Clipboard + keystrokes (with auto-restore)
ui/
  floating_pill.py      # Overlay indicator (PyQt6, Catppuccin Mocha theme, audio pulse)
  system_tray.py        # Tray icon/menu (pystray, Catppuccin theme, mic selector)
utils/
  config_manager.py     # JSON + .env config management
assets/
  logo.svg              # App logo (animated)
  logo_*.png            # App icons (16, 24, 32, 48, 64, 128, 256)
  logo.gif              # Animated logo for README
  favicon.ico           # Multi-size favicon
```

## Privacy

- **No telemetry** — Nothing leaves your machine unless you use cloud APIs
- **No accounts** — No sign-up, no tracking
- **Local-first** — Works 100% offline with local Whisper
- **Open source** — Audit the code yourself

## Requirements

- Windows 10/11
- Python 3.10+
- Microphone
- ~2 GB RAM for local model (base)
- Internet for cloud APIs (optional)

## License

MIT License — Free for personal and commercial use.

## Credits

- [faster-whisper](https://github.com/guillaumekln/faster-whisper) — Local Whisper inference
- [Groq](https://groq.com) — Fast Whisper API
- [pynput](https://github.com/moses-palmer/pynput) — Global hotkeys
- [pystray](https://github.com/moses-palmer/pystray) — System tray
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) — Floating UI
- [sounddevice](https://python-sounddevice.readthedocs.io/) — Audio recording
- [Catppuccin](https://github.com/catppuccin/catppuccin) — Color palette

---

**Made for power users who want Wispr Flow on Windows — free, local.**
