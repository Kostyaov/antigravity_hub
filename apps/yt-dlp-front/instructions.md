# Web-DLP Tech Spec & Instructions

*Примітка: Для загальної інструкції із запуску та архітектури дивіться `README.md`.*

## 1. Project Overview
A web-based local interface for the `yt-dlp` and `ffmpeg` utilities. The application allows users to safely download YouTube videos avoiding modern 429 rate limits, manipulate local audio/video files (audio replacement), and update the core engine.

Primary Reference: https://github.com/yt-dlp/yt-dlp
Target Environment: Web Browser (Desktop / Mobile vertical views), Localhost Backend.

## 2. Core Features (Current Stable State)
- **Minimalist Downloading:** Download video in formats from MP3 to MAX resolution. Uses the native Python `yt-dlp` module.
- **Smart Subtitles:** A single "Subtitles" checkbox intelligently fetches only original language auto-captions and English manual tracks to completely avoid YouTube API rate limits (HTTP 429) that occur on batch subtitle queries.
- **Update System:** Dedicated UI button to trigger `pip install -U yt-dlp` in the background.
- **FFMPEG Native Editor:** Scans user's `~/Downloads` for media files and executes non-blocking `ffmpeg` merging via `-c copy` without requiring terminal skills. The file lists automatically refresh the instant a new download completes.
- **Real-Time Progress:** WebSocket pushing output log strings directly to the Frontend `.console-output`.

## 3. Technical Stack
- **Backend**: Python (FastAPI). Uses `yt_dlp` native python module. 
- **Frontend**: HTML5, Vanilla CSS3 (Dark Dashboard), Vanilla JavaScript (Fetch API + WebSockets).
- **Dependencies**: `fastapi`, `uvicorn`, `yt-dlp`, `websockets`, `pydantic`. System dependencies: `ffmpeg`.

## 4. Architecture & Security
**Download Flow (`yt-dlp`):**
1. User submits URL & options.
2. FastApi (`start_download`) spawns asynchronous background task.
3. `yt_dlp_service` uses basic configuration options to target standard formats. Subtitles restricted by `['.*-orig']` regex.
4. Websocket callbacks route progress lines. Output explicitly replaces empty Exceptions with `repr(e)` to prevent silent UI freezes.
5. Once finished natively in `~/Downloads`, a UI button allows OS-native opening of the folder via Python `os.startfile` or `subprocess.run(["open", ...])`.

**Editor Flow (`ffmpeg`):**
1. Backend scans explicitly `~/Downloads` with specific multi-media extensions (mp4, mkv, mp3, etc).
2. Users select files via standard HTML `<select>` elements.
3. Async subprocess `ffmpeg_service.py` executes media copy. File paths are strictly routed relative to the Downloads system folder to prevent directory traversal exploits.

## 5. UI/UX Principles
- Single-page horizontal design that wraps to columns on mobile.
- Console window provides absolute transparency into backend python/ffmpeg processes.
- Status indications (grey defaults, green success, red errors).