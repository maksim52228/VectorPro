# main.py
import threading
import sys
import os

# Добавим текущую папку в PYTHONPATH (если нужно)
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем бота и веб-приложение
from bot import main as run_bot
from backend import app

import logging
logging.basicConfig(level=logging.INFO)

def start_flask():
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, use_reloader=False)

def start_telegram_bot():
    run_bot()

if __name__ == '__main__':
    # Запускаем Flask в основном потоке (Render ожидает, что веб-сервер будет отвечать)
    # А бота — в фоновом потоке
    bot_thread = threading.Thread(target=start_telegram_bot, daemon=True)
    bot_thread.start()

    # Запускаем Flask
    start_flask()
