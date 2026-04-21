#!/usr/bin/env bash

# =============================================
#   Web-DLP • Покращений запуск на macOS
# =============================================

# Переходимо в папку зі скриптом
cd "$(dirname "$0")" || exit

echo -e "\n========================================="
echo "      Діагностика Web-DLP сервера"
echo "=========================================\n"

# 1. Спроба звільнити порт 8080
echo "Перевірка порту 8080..."
PORT=8080
PID=$(lsof -t -i:$PORT)
if [ -n "$PID" ]; then
    echo "Знайдено процес $PID на порту $PORT. Спробую завершити його..."
    kill -9 $PID 2>/dev/null
    sleep 1
fi

# 2. Перевірка віртуального оточення
if [ ! -d "./venv" ]; then
    echo "ЕРОР: Папка 'venv' не знайдена в $(pwd)"
    echo "Спробуй виконати команди: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    echo -e "\nНатисни Enter для виходу..."
    read -r
    exit 1
fi

echo "Активую venv..."
source ./venv/bin/activate

# Перевірка, чи ми в venv
echo "Використовую Python: $(which python)"

# 3. Перевірка залежностей
echo "Перевірка FastAPI..."
if ! python -c "import fastapi" 2>/dev/null; then
    echo "ЕРОР: FastAPI не встановлено у venv."
    echo "Виконай: pip install fastapi uvicorn yt-dlp jinja2 websockets pydantic"
    echo -e "\nНатисни Enter для виходу..."
    read -r
    exit 1
fi

# 4. Запуск сервера
if [ ! -d "app" ]; then
    echo "ЕРОР: Папка 'app' не знайдена."
    echo -e "\nНатисни Enter для виходу..."
    read -r
    exit 1
fi

cd app || exit
echo "Запускаю uvicorn на http://localhost:8080..."
python -m uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Якщо uvicorn завершився
EXIT_CODE=$?
echo -e "\nСервер зупинено з кодом: $EXIT_CODE"
echo "Натисни Enter для завершення..."
read -r