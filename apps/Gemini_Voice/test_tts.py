import os
import traceback
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

try:
    print("Starting request...")
    response = client.models.generate_content(
        model="models/gemini-3.1-flash-tts-preview",
        contents="Озвуч цей текст українською мовою. Використовуй чоловічий, природний голос. Темп 1.1x.\n\nПРИВІТ!",
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name="Charon"
                    )
                )
            )
        )
    )
    print("Success!")
    parts = response.candidates[0].content.parts if response.candidates else []
    print(f"Has parts: {bool(parts)}")
except Exception as e:
    print(f"Error: {e}")
    traceback.print_exc()
