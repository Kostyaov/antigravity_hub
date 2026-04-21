import os
import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from pydub import AudioSegment
from pydub.utils import which

# Load API Key from .env
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Add Homebrew bin to PATH (for ffmpeg/ffprobe)
os.environ["PATH"] += os.pathsep + "/opt/homebrew/bin"

# Initialize Gemini Client
client = genai.Client(api_key=GEMINI_API_KEY)

def process_telegram_post(text, max_chars=3000):
    """Clean and split text into logical chunks."""
    clean_text = text.replace('*', '').replace('_', '').replace('http', ' посилання ')
    
    chunks = []
    if len(clean_text) > max_chars:
        sentences = clean_text.split('. ')
        current_chunk = ""
        for sentence in sentences:
            if len(current_chunk) + len(sentence) < max_chars:
                current_chunk += sentence + ". "
            else:
                chunks.append(current_chunk.strip())
                current_chunk = sentence + ". "
        if current_chunk:
            chunks.append(current_chunk.strip())
    else:
        chunks.append(clean_text)
    
    return chunks

def synthesize_audio(chunks, max_retries=3):
    """Synthesize text to audio with error handling and progress saving."""
    # Using gemini-flash-latest for better quota and stable audio support
    MODEL_NAME = "models/gemini-flash-latest"
    combined_audio = AudioSegment.empty()
    processed_any = False

    for i, chunk in enumerate(chunks):
        success = False
        print(f"\nProcessing part {i+1} of {len(chunks)}...")

        for attempt in range(1, max_retries + 1):
            try:
                # Request audio generation with detailed config
                response = client.models.generate_content(
                    model=MODEL_NAME,
                    contents=[
                        "Озвуч цей текст українською мовою. Використовуй природний, "
                        "динамічний голос для Telegram-посту. Темп 1.1x.",
                        chunk
                    ],
                    config=types.GenerateContentConfig(
                        response_modalities=["AUDIO"]
                    )
                )
                
                # Extract audio data from response parts
                audio_data = None
                if response.candidates and response.candidates[0].content.parts:
                    for part in response.candidates[0].content.parts:
                        if part.inline_data:
                            audio_data = part.inline_data.data
                            break
                
                if not audio_data:
                    # In case of 400 or other issues that don't raise an exception but return empty candidates
                    raise ValueError(f"API response does not contain audio data. Response: {response}")

                temp_file = f"temp_{i}.raw"
                with open(temp_file, "wb") as f:
                    f.write(audio_data)
                
                # Gemini Audio output is typically raw PCM 16-bit 24kHz Mono
                new_segment = AudioSegment.from_raw(
                    temp_file, 
                    sample_width=2, 
                    frame_rate=24000, 
                    channels=1
                )
                combined_audio += new_segment
                os.remove(temp_file)
                
                success = True
                processed_any = True
                break  

            except Exception as e:
                print(f"Error on attempt {attempt}: {e}")
                if attempt < max_retries:
                    wait_time = attempt * 5  
                    print(f"Retrying in {wait_time} sec...")
                    time.sleep(wait_time)
                else:
                    print(f"!!! Failed to synthesize part {i+1} after {max_retries} attempts.")

        if not success:
            if processed_any:
                choice = input("\nDo you want to save already processed parts? (y/n): ").lower()
                if choice == 'y':
                    break 
                else:
                    print("Operation cancelled.")
                    return
            else:
                print("No parts were processed. Exiting.")
                return

    # Save final result
    if processed_any:
        output_file = "telegram_audio.ogg"
        try:
            combined_audio.export(output_file, format="opus", codec="libopus")
            print(f"\nDone! File saved: {output_file}")
        except Exception as e:
            print(f"Failed to export final audio: {e}")
            # Fallback export to wav if ogg fails
            fallback_file = "telegram_audio.wav"
            combined_audio.export(fallback_file, format="wav")
            print(f"Saved fallback wav: {fallback_file}")

# Test run
if __name__ == "__main__":
    post_text = """Американці остаточно вивели свої війська із Сирії. Останні підрозділи залишили територію цієї країни через Йорданію. Пояснення такого маршруту, наскільки я розумію, пов’язане із уникненням загрози атак іранських проксі на іракській території."""
    text_chunks = process_telegram_post(post_text)
    synthesize_audio(text_chunks)