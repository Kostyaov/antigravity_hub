from google import genai
import os
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
for m in client.models.list():
    # Only keep models that seem related to audio/flash
    if 'flash' in m.name or 'tts' in m.name or 'audio' in m.name:
        # Check supported methods via __dict__ or just standard names
        print(f"Name: {m.name}")
        # print(f"Output Modalities: {m.output_modalities}") # Check if this exists
