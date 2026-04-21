import os
import uuid
import time
import asyncio
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from google import genai
from google.genai import types
import edge_tts
from pydub import AudioSegment

# Load environment variables
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure environment
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

# Initialize App
app = FastAPI(title="Gemini TTS Web Assistant")

# Setup directories
BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
AUDIO_DIR = STATIC_DIR / "audio"
TEMPLATES_DIR = BASE_DIR / "templates"

STATIC_DIR.mkdir(exist_ok=True)
AUDIO_DIR.mkdir(exist_ok=True)
TEMPLATES_DIR.mkdir(exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

class TTSRequest(BaseModel):
    text: str
    model: str  # "gemini-3.1", "gemini-2.5", "gtts" (now edge-tts)
    voice: str  # "male", "female"
    context: Optional[str] = None  # New field for style steering

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = TEMPLATES_DIR / "index.html"
    if not index_path.exists():
        return "<h1>Index.html not found</h1>"
    return index_path.read_text()

@app.post("/synthesize")
async def synthesize_api(req: TTSRequest):
    try:
        print(f"\n" + "="*40)
        print(f"🎙 НОВИЙ ЗАПИТ НА ОЗВУЧКУ")
        print(f"➤ Обрана модель: {req.model}")
        print(f"➤ Обраний голос: {req.voice}")
        print(f"➤ Контекст стилю: {req.context if req.context else 'Немає'}")
        print(f"➤ Довжина тексту: {len(req.text)} символів")
        print("="*40)

        # 1. Synthesis
        working_text = req.text

        # 2. Synthesis
        filename = f"audio_{uuid.uuid4().hex}.ogg"
        output_path = AUDIO_DIR / filename
        
        if req.model == "gtts": # Edge TTS (formerly gTTS key)
            success = await synthesize_edge_tts(working_text, req.voice, output_path)
        else:
            # Note: "models/gemini-2.5-flash-native-audio-latest" is not supported for generic generateContent (only Bidi API).
            # The ONLY model that officially supports text-to-AUDIO via generateContent in the current SDK is 3.1-flash-tts-preview.
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
    """Synthesizes text using high-quality Edge TTS (Ostap/Polina)."""
    try:
        # Map voice names
        voice_id = "uk-UA-OstapNeural" if voice == "male" else "uk-UA-PolinaNeural"
        print(f"⚙️ [Edge TTS] Запуск генерації...")
        print(f"   ↳ Системний ідентифікатор голосу: {voice_id}")
        
        communicate = edge_tts.Communicate(text, voice_id)
        
        temp_mp3 = output_path.with_suffix(".mp3")
        await communicate.save(str(temp_mp3))
        
        audio = AudioSegment.from_file(str(temp_mp3))
        audio.export(str(output_path), format="opus", codec="libopus")
        os.remove(temp_mp3)
        return True
    except Exception as e:
        print(f"Edge TTS error: {e}")
        return False

async def synthesize_gemini(text: str, model_id: str, voice: str, output_path: Path, style_context: Optional[str] = None) -> bool:
    """Synthesizes text using Gemini Native Audio (fix for 400 error)."""
    try:
        chunks = split_text(text)
        combined_audio = AudioSegment.empty()

        # The UI now sends the exact voice name (e.g. Charon, Puck, Aoede)
        gemini_voice = voice
        
        # Determine gender dynamically for prompt shaping
        gender = "чоловічий" if voice in ["Puck", "Charon", "Fenrir", "Enceladus", "Algieba"] else "жіночий"
        
        print(f"⚙️ [Gemini TTS] Запуск генерації...")
        print(f"   ↳ Модель API: {model_id}")
        print(f"   ↳ Цільовий голос (voice_name): {gemini_voice}")
        print(f"   ↳ Системний промпт (гендер): {gender}")
        if style_context:
            print(f"   ↳ Контекст стилю: {style_context}")
        
        # Build prompt instructions
        instructions = f"Озвуч цей текст українською мовою. Використовуй {gender}, природний голос. Темп 1.1x."
        if style_context:
            instructions = f"Style/Context: {style_context}. {instructions}"
        
        for chunk in chunks:
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
            
            audio_data = None
            if response.candidates and response.candidates[0].content.parts:
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        audio_data = part.inline_data.data
                        break
            
            if not audio_data:
                return False

            temp_filename = f"temp_{uuid.uuid4().hex}.raw"
            with open(temp_filename, "wb") as f:
                f.write(audio_data)
            
            chunk_audio = AudioSegment.from_raw(temp_filename, sample_width=2, frame_rate=24000, channels=1)
            combined_audio += chunk_audio
            os.remove(temp_filename)

        combined_audio.export(str(output_path), format="opus", codec="libopus")
        return True
    except Exception as e:
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
    if current:
        chunks.append(current.strip())
    return chunks

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
