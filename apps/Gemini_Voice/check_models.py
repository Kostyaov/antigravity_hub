from google import genai
import os
from dotenv import load_dotenv
load_dotenv()
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
for m in client.models.list():
    if 'flash' in m.name or '2.5' in m.name:
        print(f"{m.name}: {m.supported_generation_methods}")
