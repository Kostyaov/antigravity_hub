import asyncio
import os
import re

class FFMPEGService:
    def __init__(self, download_dir: str):
        self.download_dir = download_dir
        self.broadcast_callback = None

    def set_broadcast_callback(self, callback):
        self.broadcast_callback = callback

    async def _send_update(self, msg_type: str, data: dict):
        if self.broadcast_callback:
            await self.broadcast_callback({"type": msg_type, "data": data})

    async def _run_command(self, cmd: list[str], output_filename: str):
        await self._send_update("log", {"message": f"Running FFMPEG command: {' '.join(cmd)}"})
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        
        async def read_stream(stream):
            while True:
                line = await stream.readline()
                if not line:
                    break
                
                # Читаємо вивід FFMPEG, але не виводимо прогресбар,
                # бо злиття відбувається майже миттєво і не має ETA
                pass

        # Читаємо stdout та stderr конкурентно
        await asyncio.gather(
            read_stream(process.stdout),
            read_stream(process.stderr)
        )
        
        await process.wait()
        
        if process.returncode == 0:
            await self._send_update("finished", {
                "message": f"FFMPEG process completed successfully! Saved as {output_filename}",
                "filename": output_filename
            })
        else:
            await self._send_update("log", {"message": f"FFMPEG process failed with code {process.returncode}"})


    async def cut_media(self, input_path: str, start: str, stop: str):
        # Якщо передано просто ім'я файлу, шукаємо у папці завантажень
        if not os.path.isabs(input_path):
            input_path = os.path.join(self.download_dir, input_path)
            
        if not os.path.exists(input_path):
            await self._send_update("log", {"message": f"Error: File not found: {input_path}"})
            return

        filename, ext = os.path.splitext(os.path.basename(input_path))
        output_filename = f"{filename}_cut{ext}"
        output_path = os.path.join(self.download_dir, output_filename)
        
        # ffmpeg -i input.mp4 -ss 00:00:10 -to 00:00:20 -c copy output.mp4
        cmd = [
            'ffmpeg', '-y', 
            '-i', input_path,
            '-ss', start,
            '-to', stop,
            '-c', 'copy',
            output_path
        ]
        
        await self._run_command(cmd, output_filename)


    async def replace_audio(self, video_path: str, audio_path: str):
        if not os.path.isabs(video_path):
            video_path = os.path.join(self.download_dir, video_path)
        if not os.path.isabs(audio_path):
            audio_path = os.path.join(self.download_dir, audio_path)
            
        if not os.path.exists(video_path):
            await self._send_update("log", {"message": f"Error: Video file not found: {video_path}"})
            return
            
        if not os.path.exists(audio_path):
            await self._send_update("log", {"message": f"Error: Audio file not found: {audio_path}"})
            return

        filename, ext = os.path.splitext(os.path.basename(video_path))
        output_filename = f"{filename}_merged{ext}"
        output_path = os.path.join(self.download_dir, output_filename)
        
        # ffmpeg -i video.mp4 -i audio.mp3 -c:v copy -map 0:v:0 -map 1:a:0 output.mp4
        cmd = [
            'ffmpeg', '-y',
            '-i', video_path,
            '-i', audio_path,
            '-c:v', 'copy',
            '-c:a', 'aac', # перекодовуємо аудіо в aac для сумісності з mp4
            '-map', '0:v:0',
            '-map', '1:a:0',
            '-shortest', # Обрізаємо по найкоротшому стріму
            output_path
        ]
        
        await self._run_command(cmd, output_filename)
