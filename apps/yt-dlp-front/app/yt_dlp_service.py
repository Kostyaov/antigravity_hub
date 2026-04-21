import yt_dlp
import asyncio
import os
import sys

class YTDLPService:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self.broadcast_callback = None
        
    def set_broadcast_callback(self, callback):
        self.broadcast_callback = callback

    async def _send_update(self, msg_type: str, data: dict):
        if self.broadcast_callback:
            await self.broadcast_callback({"type": msg_type, "data": data})

    class MyLogger:
        def __init__(self, service_instance, loop):
            self.service_instance = service_instance
            self.loop = loop

        def debug(self, msg):
            if msg.startswith('[debug] '):
                pass # Ігнорувати відлагоджувальні повідомлення для чистішого UI
            else:
                self.info(msg)

        def info(self, msg):
            # Спроба надіслати лог на фронтенд безпечно через asyncio
            try:
                asyncio.run_coroutine_threadsafe(
                    self.service_instance._send_update("log", {"message": msg}),
                    self.loop
                )
            except Exception:
                pass # Немає запущеного циклу подій

        def warning(self, msg):
            self.info(f"WARNING: {msg}")

        def error(self, msg):
            self.info(f"ERROR: {msg}")

    async def download_video(self, url: str, format_name: str = "1080", include_audio: bool = True, include_subtitles: bool = False):
        await self._send_update("log", {"message": f"Starting download for {url} (Format: {format_name}, Audio: {include_audio}, Subtitles: {include_subtitles})..."})
        
        loop = asyncio.get_running_loop()
        
        def progress_hook(d):
            if d['status'] == 'downloading':
                try:
                    percent_str = d.get('_percent_str', '').strip()
                    speed_str = d.get('_speed_str', '').strip()
                    eta_str = d.get('_eta_str', '').strip()
                    
                    # Відправка прогресу на фронтенд
                    asyncio.run_coroutine_threadsafe(
                        self._send_update("progress", {
                            "percent": percent_str,
                            "speed": speed_str,
                            "eta": eta_str,
                            "filename": d.get('filename', '')
                        }), loop
                    )
                except Exception:
                    pass
            elif d['status'] == 'finished':
                try:
                    # Видалення повного шляху для безпеки та чистоти логів
                    filename = os.path.basename(d['filename'])
                    asyncio.run_coroutine_threadsafe(
                        self._send_update("finished", {
                            "filename": filename,
                            "message": "Download completed! Processing..."
                        }), loop
                    )
                except Exception:
                    pass

        # Вибір формату на основі переданих параметрів
        postprocessors = []
        if format_name == "mp3":
            format_spec = "bestaudio/best"
            postprocessors = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]
        elif format_name == "original_audio":
            format_spec = "bestaudio/best"
        else:
            heights = {
                "480": 480,
                "720": 720,
                "1080": 1080,
                "2k": 1440,
                "MAX": 4320
            }
            h = heights.get(format_name, 1080)
            
            if include_audio:
                format_spec = f"bestvideo[height<={h}]+bestaudio/best[height<={h}]/best"
            else:
                format_spec = f"bestvideo[height<={h}]/bestvideo/best[height<={h}][vcodec!=none][acodec=none]/best[vcodec!=none][acodec=none]"

        ydl_opts = {
            'format': format_spec,
            'outtmpl': os.path.join(self.download_dir, '%(title)s.%(ext)s'),
            'logger': self.MyLogger(self, loop),
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4', # Надати перевагу mp4 контейнеру
            'noplaylist': True, # Завантажувати лише одне відео (без плейлистів)
            'postprocessors': postprocessors,
            'overwrites': True, # Завжди перезаписувати файл, якщо він існує
        }

        # Підтримка субтитрів
        if include_subtitles:
            ydl_opts['writesubtitles'] = True
            ydl_opts['writeautomaticsub'] = True
            # Обираємо лише оригінальні автогенеровані (*-orig),
            # щоб уникнути запитів на автопереклад для не-англійських відео, які блокує YouTube (429)
            ydl_opts['subtitleslangs'] = ['.*-orig']
        
        # Запуск yt-dlp в окремому потоці, щоб не блокувати цикл подій asyncio
        def run_ytdlp():
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])
            except Exception as e:
                # Логування помилки та повідомлення про помилку
                 asyncio.run_coroutine_threadsafe(
                    self._send_update("error", {"message": f"Error during download: {repr(e)}"}),
                    loop
                 )

        await asyncio.to_thread(run_ytdlp)

    async def update_ytdlp(self):
        await self._send_update("log", {"message": "Starting yt-dlp update..."})
        try:
             # Запуск команди оновлення через subprocess. 
             # Оскільки модуль встановлено через pip, використовуємо pip для оновлення
             process = await asyncio.create_subprocess_shell(
                 f"{sys.executable} -m pip install -U yt-dlp",
                 stdout=asyncio.subprocess.PIPE,
                 stderr=asyncio.subprocess.PIPE
             )
             
             stdout, stderr = await process.communicate()
             
             if stdout:
                  await self._send_update("log", {"message": stdout.decode()})
             if stderr:
                  await self._send_update("log", {"message": stderr.decode()})
                  
             await self._send_update("log", {"message": "Update process finished."})
             
        except Exception as e:
            await self._send_update("log", {"message": f"Update failed: {str(e)}"})
