from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import asyncio
import os
import sys
import subprocess

from yt_dlp_service import YTDLPService
from ffmpeg_service import FFMPEGService

app = FastAPI(title="Web-DLP")

# Шлях до системної папки завантажень користувача macOS
USER_DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

# Переконатись, що директорії для фронтенду існують
os.makedirs("static", exist_ok=True)
os.makedirs("templates", exist_ok=True)

# Монтування статичних файлів
app.mount("/static", StaticFiles(directory="static"), name="static")

# Налаштування шаблонів
templates = Jinja2Templates(directory="templates")

# Ініціалізація сервісу YT-DLP із системною папкою
ytdlp_service = YTDLPService(download_dir=USER_DOWNLOADS_DIR)
ffmpeg_service = FFMPEGService(download_dir=USER_DOWNLOADS_DIR)

# Активні WebSocket підключення
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass # Коректна обробка відключених клієнтів

manager = ConnectionManager()
ytdlp_service.set_broadcast_callback(manager.broadcast)
ffmpeg_service.set_broadcast_callback(manager.broadcast)

class DownloadRequest(BaseModel):
    url: str
    format: str = "1080"
    include_audio: bool = True
    include_subtitles: bool = False

class FFMPEGCutRequest(BaseModel):
    file_path: str
    start_time: str
    stop_time: str

class FFMPEGReplaceRequest(BaseModel):
    video_path: str
    audio_path: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/download")
async def start_download(req: DownloadRequest):
    # Запуск завантаження у фоновому завданні, щоб не блокувати відповідь API
    asyncio.create_task(ytdlp_service.download_video(
        url=req.url, 
        format_name=req.format, 
        include_audio=req.include_audio,
        include_subtitles=req.include_subtitles
    ))
    return {"message": "Download started", "url": req.url}

@app.post("/api/update")
async def update_ytdlp():
    asyncio.create_task(ytdlp_service.update_ytdlp())
    return {"message": "Update started"}

@app.get("/api/files/{filename}")
async def get_file(filename: str):
    file_path = os.path.join(USER_DOWNLOADS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=filename)
    return {"error": "File not found"}

@app.get("/api/files_list")
async def list_files():
    files = []
    if os.path.exists(USER_DOWNLOADS_DIR):
        for f in os.listdir(USER_DOWNLOADS_DIR):
            if os.path.isfile(os.path.join(USER_DOWNLOADS_DIR, f)) and not f.startswith('.'):
                # Відфільтровуємо лише медіа файли для зручності
                if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mp3', '.m4a', '.wav')):
                    files.append(f)
    # Сортування за датою зміни (найновіші зверху)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(USER_DOWNLOADS_DIR, x)), reverse=True)
    return {"files": files}

@app.post("/api/ffmpeg/cut")
async def ffmpeg_cut(req: FFMPEGCutRequest):
    asyncio.create_task(ffmpeg_service.cut_media(req.file_path, req.start_time, req.stop_time))
    return {"message": "Started", "task": "cut"}

@app.post("/api/ffmpeg/replace")
async def ffmpeg_replace(req: FFMPEGReplaceRequest):
    asyncio.create_task(ffmpeg_service.replace_audio(req.video_path, req.audio_path))
    return {"message": "Started", "task": "replace"}

@app.get("/api/open_folder")
async def open_folder():
    try:
        if os.name == 'nt':
            os.startfile(USER_DOWNLOADS_DIR)
        elif sys.platform == 'darwin':
            subprocess.run(["open", USER_DOWNLOADS_DIR], check=True)
        else:
            subprocess.run(["xdg-open", USER_DOWNLOADS_DIR], check=True)
        return {"message": "Folder opened"}
    except Exception as e:
        return {"error": str(e)}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Підтримка з'єднання, прослуховування повідомлень клієнта, якщо потрібно
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
