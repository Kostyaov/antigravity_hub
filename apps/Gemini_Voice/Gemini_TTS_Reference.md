# Еталонний код для синтезу мови (TTS) через Google Gemini API

Цей документ містить актуальний приклад коду для генерації аудіо (Text-to-Speech) за допомогою Python SDK **google-genai** версії 3.1.

---

## 🛠️ Технічні вимоги
- **Модель**: `models/gemini-3.1-flash-tts-preview` (Стабільна версія для REST TTS).
- **Бібліотека**: `google-genai` (не плутати з `google-generativeai`).

---

## 🗣️ Бібліотека голосів (Voice Library)
В системі доступно 8 преміальних голосів:
1.  **Puck** — Чоловічий / Енергійний бадьорий.
2.  **Charon** — Чоловічий / Інформативний / Спокійний.
3.  **Fenrir** — Чоловічий / Емоційний.
4.  **Enceladus** — Чоловічий / Глибокий / Дихання.
5.  **Aoede** — Жіночий / Легкий / Спокійний.
6.  **Kore** — Жіночий / Впевнений / Твердий.
7.  **Leda** — Жіночий / Молодіжний.
8.  **Algieba** — Чоловічий / Гладкий / Приємний.

---

## 💻 Код інтеграції (Audio Steering Example)

```python
import os
from google import genai
from google.genai import types

# 1. Ініціалізація
client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

# 2. Параметри синтезу
text = "Привіт! Це демонстрація стабільної версії 4.0."
# Наш унікальний AI Steering Контекст
steering_context = "Professional news anchor. Clear articulation, fast-paced, authoritative tone."
voice = "Charon"

# 3. Виконання запиту
response = client.models.generate_content(
    model="models/gemini-3.1-flash-tts-preview",
    contents=[
        # Ми передаємо вказівку щодо стилю разом із текстом
        f"CONTEXT: {steering_context}\nTEXT: {text}"
    ],
    config=types.GenerateContentConfig(
        response_modalities=["AUDIO"],
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=voice
                )
            )
        )
    )
)

# 4. Обробка аудіо
if response.candidates and response.candidates[0].content.parts:
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    with open("output.pcm", "wb") as f:
        f.write(audio_data)
    print("PCM аудіо згенеровано успішно.")
```

---

## 💡 Важливі нотатки
- **Raw Audio**: API повертає сирі PCM байти (24kHz, 16bit, Mono). Для перетворення в MP3/OGG використовуйте **FFmpeg** або **pydub**.
- **Context Shaping**: Включення інструкцій прямо у `contents` (як у прикладі вище) — це найбільш надійний спосіб керування характером озвучки.
- **Limits**: Пам'ятайте про ліміт 10 запитів на добу для безкоштовних ключів.

---
*Документація підготовлена для Gemini TTS V4.0.*
