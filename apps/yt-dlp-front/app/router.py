import os
import sys
import asyncio
import subprocess
from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from pydantic import BaseModel

# Add local path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from yt_dlp_service import YTDLPService
from ffmpeg_service import FFMPEGService

router = APIRouter(prefix="/api/dlp", tags=["DLP"])

USER_DOWNLOADS_DIR = os.path.expanduser("~/Downloads")

class DLPConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass

manager = DLPConnectionManager()

ytdlp_service = YTDLPService(download_dir=USER_DOWNLOADS_DIR)
ffmpeg_service = FFMPEGService(download_dir=USER_DOWNLOADS_DIR)

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


@router.post("/download")
async def start_download(req: DownloadRequest):
    asyncio.create_task(ytdlp_service.download_video(
        url=req.url, 
        format_name=req.format, 
        include_audio=req.include_audio,
        include_subtitles=req.include_subtitles
    ))
    return {"message": "Download started", "url": req.url}

@router.post("/update")
async def update_ytdlp():
    asyncio.create_task(ytdlp_service.update_ytdlp())
    return {"message": "Update started"}

@router.get("/files/{filename}")
async def get_file(filename: str):
    file_path = os.path.join(USER_DOWNLOADS_DIR, filename)
    if os.path.exists(file_path):
        return FileResponse(path=file_path, filename=filename)
    return {"error": "File not found"}

@router.get("/files_list")
async def list_files():
    files = []
    if os.path.exists(USER_DOWNLOADS_DIR):
        for f in os.listdir(USER_DOWNLOADS_DIR):
            if os.path.isfile(os.path.join(USER_DOWNLOADS_DIR, f)) and not f.startswith('.'):
                if f.lower().endswith(('.mp4', '.mkv', '.avi', '.webm', '.mp3', '.m4a', '.wav')):
                    files.append(f)
    files.sort(key=lambda x: os.path.getmtime(os.path.join(USER_DOWNLOADS_DIR, x)), reverse=True)
    return {"files": files}

@router.post("/ffmpeg/cut")
async def ffmpeg_cut(req: FFMPEGCutRequest):
    asyncio.create_task(ffmpeg_service.cut_media(req.file_path, req.start_time, req.stop_time))
    return {"message": "Started", "task": "cut"}

@router.post("/ffmpeg/replace")
async def ffmpeg_replace(req: FFMPEGReplaceRequest):
    asyncio.create_task(ffmpeg_service.replace_audio(req.video_path, req.audio_path))
    return {"message": "Started", "task": "replace"}

@router.get("/open_folder")
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

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)
