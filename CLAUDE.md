# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Application

```bash
python main_pro_plus_v4.py
```

Requires Python 3.x with `tkinter` (stdlib). `ffmpeg.exe` and `ffprobe.exe` must be present in the project root.

## Building Windows Executable

The app has a built-in build button that runs PyInstaller. Alternatively:

```bash
pip install pyinstaller
pyinstaller --onefile main_pro_plus_v4.py
```

## Architecture Overview

This is a desktop Tkinter app for generating vocabulary learning videos (TikTok/Shorts-style).

**Core modules:**

- `main_pro_plus_v4.py` — Main entry point. Houses the primary UI, orchestrates the full video generation pipeline: word selection → TTS audio → image/subtitle overlays → FFmpeg rendering. Also contains the PyInstaller build trigger.
- `dictionary_lib.py` — All CRUD for dictionary data. Words are stored in `dictionary_data.json`, grouped by category (e.g. ACTIONS, ANIMALS). Each entry has English term, Vietnamese meaning, and an example sentence.
- `dict_manager_ui.py` — Separate Tkinter window for managing dictionary groups and entries (add/edit/delete/search).
- `ai_lookup.py` — Calls Gemini or OpenAI APIs to auto-populate word meanings and examples in a structured JSON format. Falls back to offline mode if no API key is configured.
- `migrate_dict.py` — One-time utility for migrating dictionary data from older formats to the current `dictionary_data.json` schema.

**Data flow:**
1. Words come from `dictionary_data.json` (or `data.csv` as import).
2. TTS is generated via ElevenLabs, Edge TTS, or a hybrid mode.
3. FFmpeg (local binary) renders the final video with audio, subtitles, backgrounds, and logo overlays.

**Configuration:** API keys and settings are stored in `.env` in the project root.
