# EasySpeak - System-wide AI Dictation for Windows

A lightweight, privacy-first dictation tool for Windows 10/11. Press a hotkey, speak, and have your words transcribed and inserted at your cursor — powered by local Whisper or cloud APIs, with optional LLM cleanup.


## Features

- **Global hotkey** — Hold to talk, release to transcribe (Caps Lock by default)
- **Hands-free mode** — Double-tap hotkey to start/stop without holding
- **Auto-stop** — Hands-free sessions auto-stop after 5 minutes
- **Esc to cancel** — Drop recording or kill transcription instantly
- **Local or cloud transcription** — faster-whisper (offline) or Groq/OpenAI Whisper API
- **LLM cleanup** — Remove filler words, fix punctuation, proper casing
- **Clipboard integration** — Text pasted at cursor, also left on clipboard
- **Floating pill indicator** — Tiny overlay shows recording state
- **System tray** — Enable/disable, switch modes, launch at login
- **No accounts, no telemetry** — Works fully offline with local model

## Quick Start

### 1. Install Python 3.10+
Download from [python.org](https://www.python.org/downloads/) — check "Add Python to PATH" during install.

### 2. Clone and install dependencies
```bash
git clone https://github.com/yourusername/EasySpeak.git
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
- Enable "Launch at Login" from system tray menu
- Or add a shortcut to `shell:startup` folder

## Usage

| Action | Key |
|--------|-----|
| Hold-to-talk | Hold **Caps Lock** (or configured key) |
| Hands-free start | Double-tap **Caps Lock** |
| Hands-free stop | Tap **Caps Lock** once |
| Cancel | Press **Esc** |

The floating pill shows:
- 🔴 **Recording...** — Hold-to-talk active
- 🎤 **Hands-Free Mode** — Hands-free recording
- ⏳ **Transcribing...** — Processing audio

## Configuration

Edit `config.json`:

```json
{
  "hotkey": {
    "key": "Key.caps_lock",
    "double_tap_threshold_ms": 300
  },
  "transcription": {
    "mode": "local",
    "local_model": "base",
    "api_provider": "groq"
  },
  "llm": {
    "enabled": true,
    "provider": "groq",
    "model": "llama3-8b-8192",
    "prompt": "You are a dictation assistant..."
  },
  "clipboard": {
    "restore_previous": true,
    "restore_delay_seconds": 2.0
  },
  "auto_stop_minutes": 5,
  "launch_at_login": false
}
```

### Hotkey Options
Use any pynput key name:
- `Key.caps_lock`, `Key.ctrl`, `Key.alt`, `Key.shift`
- `Key.f1` through `Key.f12`
- Regular keys: `"a"`, `" "` (space), etc.

### Transcription Modes
- **local** — Uses faster-whisper (downloads model on first run)
- **api** — Uses Groq or OpenAI Whisper API (requires API key in `.env`)

### Local Models
| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| tiny | 39 MB | Fastest | Lower |
| base | 74 MB | Fast | Good |
| small | 244 MB | Medium | Better |
| medium | 769 MB | Slower | Best |
| large | 1.5 GB | Slowest | Best |

### LLM Providers
- **Groq** (free, fast) — `GROQ_API_KEY`
- **OpenAI** — `OPENAI_API_KEY`
- **Anthropic** — `ANTHROPIC_API_KEY`

## Building Standalone Executable

```bash
pip install pyinstaller
pyinstaller --noconfirm --onefile --windowed --name EasySpeak \
  --add-data "config.json;." \
  --add-data ".env;." \
  --hidden-import=faster_whisper \
  --hidden-import=ctranslate2 \
  main.py
```

Output: `dist/EasySpeak.exe`

## Troubleshooting

### Hotkey not working
- Run as Administrator (required for global hotkeys on some systems)
- Check Input Monitoring permission
- Try a different hotkey in config.json

### No microphone input
- Check Microphone privacy settings
- Verify correct input device in Windows Sound settings
- Test with Voice Recorder app

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
  audio_recorder.py     # Microphone recording (sounddevice)
  hotkey_manager.py     # Global hotkeys (pynput)
  transcriber.py        # Whisper local/API
  llm_processor.py      # LLM text cleanup
  text_inserter.py      # Clipboard + keystrokes
ui/
  floating_pill.py      # Overlay indicator (PyQt6)
  system_tray.py        # Tray icon/menu (pystray)
utils/
  config_manager.py     # JSON + .env config
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

---

**Made for power users who want Wispr Flow on Windows — free, local, and hackable.**
