import os
import uuid
import time
import asyncio
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

# CRITICAL: Configure PATH before importing pydub
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import google.genai
from google.genai import types
import edge_tts
import subprocess

# Initialization
BASE_DIR = Path(__file__).parent.resolve()
# ROOT_DIR: we assume we are in apps/Gemini_Voice/
ROOT_DIR = BASE_DIR.parent.parent
GLOBAL_STATIC_DIR = ROOT_DIR / "static"
AUDIO_DIR = GLOBAL_STATIC_DIR / "audio"
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

print(f"[*] Gemini Voice active. ROOT: {ROOT_DIR}")

# Load environment variables (from local .env if present)
env_path = BASE_DIR / ".env"
load_dotenv(dotenv_path=env_path)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Initialize Gemini Client if key exists
try:
    client = google.genai.Client(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
except Exception as e:
    print(f"[!] Gemini Client Init Error: {e}")
    client = None

if not client:
    print("[!] Warning: GEMINI_API_KEY not found in .env or initialization failed")

# Setup Router
router = APIRouter(prefix="/api/tts", tags=["TTS"])

class TTSRequest(BaseModel):
    text: str
    model: str  # "gemini-3.1", "gemini-2.5", "gtts" (edge-tts)
    voice: str  # "male", "female" or specific gemini voice
    context: Optional[str] = None

@router.post("/synthesize")
async def synthesize_api(req: TTSRequest):
    if not client and req.model != "gtts":
         raise HTTPException(status_code=500, detail="GEMINI_API_KEY not configured")

    try:
        print(f"\n" + "="*40)
        print(f"🎙 НОВИЙ ЗАПИТ НА ОЗВУЧКУ (Orchestrator)")
        print(f"➤ Обрана модель: {req.model}")
        print(f"➤ Обраний голос: {req.voice}")
        print(f"➤ Контекст стилю: {req.context if req.context else 'Немає'}")
        print(f"➤ Довжина тексту: {len(req.text)} символів")
        print("="*40)

        working_text = req.text
        filename = f"audio_{uuid.uuid4().hex}.ogg"
        output_path = AUDIO_DIR / filename
        
        if req.model == "gtts": 
            success = await synthesize_edge_tts(working_text, req.voice, output_path)
        else:
            model_id = "models/gemini-3.1-flash-tts-preview"
            success = await synthesize_gemini(working_text, model_id, req.voice, output_path, req.context)

        if not success:
            raise HTTPException(status_code=500, detail="Synthesis failed")

        return {
            "success": True, 
            "audio_url": f"/static/audio/{filename}",
            "text": working_text
        }

    except Exception as e:
        print(f"Server Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def synthesize_edge_tts(text: str, voice: str, output_path: Path) -> bool:
    try:
        voice_id = "uk-UA-OstapNeural" if voice == "male" else "uk-UA-PolinaNeural"
        print(f"⚙️ [Edge TTS] Запуск генерації...")
        communicate = edge_tts.Communicate(text, voice_id)
        temp_mp3 = output_path.with_suffix(".mp3")
        await communicate.save(str(temp_mp3))
        
        # Виклик ffmpeg напряму
        subprocess.run(
            ["ffmpeg", "-y", "-i", str(temp_mp3), "-c:a", "libopus", str(output_path)],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        
        os.remove(temp_mp3)
        return True
    except Exception as e:
        print(f"Edge TTS error: {e}")
        return False

async def synthesize_gemini(text: str, model_id: str, voice: str, output_path: Path, style_context: Optional[str] = None) -> bool:
    try:
        chunks = split_text(text)
        gemini_voice = voice
        gender = "чоловічий" if voice in ["Puck", "Charon", "Fenrir", "Enceladus", "Algieba"] else "жіночий"
        
        print(f"⚙️ [Gemini TTS] Запуск генерації...")
        instructions = f"Озвуч цей текст українською мовою. Використовуй {gender}, природний голос. Темп 1.1x."
        if style_context:
            instructions = f"Style/Context: {style_context}. {instructions}"
        
        temp_filename = f"temp_{uuid.uuid4().hex}.raw"
        with open(temp_filename, "wb") as f_out:
            for i, chunk in enumerate(chunks):
                print(f"  -> Gemini Chunk {i+1}/{len(chunks)} REQUEST...")
                try:
                    response = client.models.generate_content(
                        model=model_id,
                        contents=f"{instructions}\n\n{chunk}",
                        config=types.GenerateContentConfig(
                            response_modalities=["AUDIO"],
                            speech_config=types.SpeechConfig(
                                voice_config=types.VoiceConfig(
                                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                                        voice_name=gemini_voice
                                    )
                                )
                            )
                        )
                    )
                    
                    found_audio = False
                    if response.candidates and response.candidates[0].content.parts:
                        for part in response.candidates[0].content.parts:
                            if part.inline_data:
                                f_out.write(part.inline_data.data)
                                print(f"  -> Gemini Chunk {i+1} SUCCESS ({len(part.inline_data.data)} bytes)")
                                found_audio = True
                                break
                    if not found_audio:
                        print(f"  -> Gemini Chunk {i+1} FAILED (No inline_data parsed)")
                except Exception as chunk_e:
                    with open("scratch/gemini_error.log", "w") as ef:
                        ef.write(str(chunk_e))
                        import traceback
                        ef.write("\n" + traceback.format_exc())
                    print(f"  -> Gemini Chunk {i+1} EXCEPTION: {chunk_e}")
                    raise chunk_e
                            
        # Конвертація з RAW (24000Hz, s16le) в OPUS
        print(f"  -> FFmpeg Encoding...")
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", 
                    "-f", "s16le", "-ar", "24000", "-ac", "1", 
                    "-i", temp_filename, 
                    "-c:a", "libopus", 
                    str(output_path)
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                check=True
            )
        except subprocess.CalledProcessError as sub_e:
            with open("scratch/gemini_error.log", "w") as ef:
                ef.write(f"FFmpeg Error: {sub_e.stderr.decode()}")
            raise sub_e
        os.remove(temp_filename)
        return True
    except Exception as e:
        with open("scratch/gemini_error_main.log", "w") as ef:
            ef.write(str(e))
            import traceback
            ef.write("\n" + traceback.format_exc())
        print(f"Gemini Synthesis error: {e}")
        return False

def split_text(text: str, max_chars: int = 1500) -> list:
    sentences = text.split('. ')
    chunks = []
    current = ""
    for s in sentences:
        if len(current) + len(s) < max_chars:
            current += s + ". "
        else:
            chunks.append(current.strip())
            current = s + ". "
    if current: chunks.append(current.strip())
    return chunks
