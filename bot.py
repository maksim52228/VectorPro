# bot_webhook.py
import os
import asyncio
from flask import Flask, request
import sqlite3
from pydub import AudioSegment
import speech_recognition as sr
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# === Конфигурация ===
TOKEN = os.getenv("BOT_TOKEN", "7816544590:AAGrp0hyOvLcdtT-ROwjQER1ANks6jv9cyY")
PORT = int(os.getenv("PORT", 10000))  # Render требует порт 10000 по умолчанию

# === База данных (без изменений) ===
def init_db():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

# === Обработка аудио (без изменений) ===
def ogg_to_wav(ogg_path):
    sound = AudioSegment.from_ogg(ogg_path)
    wav_path = ogg_path.replace(".ogg", ".wav")
    sound.export(wav_path, format="wav")
    return wav_path

def transcribe_voice(file_path):
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")
        return text
    except Exception as e:
        return f"Ошибка распознавания: {e}"

# === Обработчики (почти без изменений) ===
async def start(update, context):
    user_id = update.effective_user.id
    add_user(user_id)
    keyboard = [[InlineKeyboardButton(
        "➕Добавить в группу",
        url="https://t.me/Replace_voice_to_text_bot?startgroup=new"
    )]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Я расшифрую тебе голосовые сообщения. Ты можешь добавить меня в группу или просто отправить голосовое сюда 😉\n\n"
        "🎤 Чтобы бот расшифровывал голосовые в чате, создайте группу и добавьте меня туда нажав на эту кнопку: ",
        reply_markup=reply_markup,
    )

async def handle_voice(update, context):
    try:
        voice_file = await update.message.voice.get_file()
        file_path = "voice_message.ogg"
        await voice_file.download_to_drive(file_path)
        wav_path = ogg_to_wav(file_path)
        text = transcribe_voice(wav_path)
        text = text[0].upper() + text[1:]
        await update.message.reply_text(f"🔊 Расшифровка:\n\n{text}")
        # Безопасное удаление
        for f in [file_path, wav_path]:
            if os.path.exists(f):
                os.remove(f)
    except Exception as e:
        await update.message.reply_text("⚠️ Произошла ошибка при обработке голосового сообщения")

async def statistic(update, context):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    await update.message.reply_text(f"Всего пользователей: {count}")

# === Инициализация Telegram-приложения ===
application = Application.builder().token(TOKEN).build()
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.VOICE, handle_voice))
application.add_handler(CommandHandler("statistic", statistic))

# Инициализируем один раз при старте
asyncio.run(application.initialize())

# === Flask: минимальный сервер для webhook ===
app = Flask(__name__)

@app.route('/telegram-webhook', methods=['POST'])
def telegram_webhook():
    json_str = request.get_data().decode('utf-8')
    update = Update.de_json(json_str, application.bot)
    asyncio.run(application.process_update(update))
    return 'OK', 200

@app.route('/health')
def health():
    return 'OK', 200

# Инициализация БД при запуске
init_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=PORT)
