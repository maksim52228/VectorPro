import os
import speech_recognition as sr
import sqlite3
from telegram import Update,InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters, CallbackContext, CommandHandler,CallbackQueryHandler
from pydub import AudioSegment

# Настройка бота
TOKEN = "7816544590:AAGrp0hyOvLcdtT-ROwjQER1ANks6jv9cyY"

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

# Добавление пользователя в базу
def add_user(user_id):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()
def ogg_to_wav(ogg_path):
    """Конвертирует .ogg в .wav (нужно для SpeechRecognition)"""
    sound = AudioSegment.from_ogg(ogg_path)
    wav_path = ogg_path.replace(".ogg", ".wav")
    sound.export(wav_path, format="wav")
    return wav_path


def transcribe_voice(file_path):
    """Распознает речь через Google Web Speech API"""
    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio = recognizer.record(source)
    try:
        text = recognizer.recognize_google(audio, language="ru-RU")  # или "en-US"
        return text
    except Exception as e:
        return f"Ошибка распознавания: {e}"
async def statistic(Update,contextTypes):
    conn = sqlite3.connect('bot_users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    await Update.message.reply_text(f"Всего пользователей: {count}")
async def start(Update,contextTypes):

    user_id = Update.effective_user.id
    add_user(user_id)
    keyboard = [
        [InlineKeyboardButton(
            "➕Добавить в группу",
            url="https://t.me/Replace_voice_to_text_bot?startgroup=new"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await Update.message.reply_text(
        "Привет! Я расшифрую тебе голосовые сообщения. Ты можешь добавить меня в группу или просто отправить голосовое сюда 😉\n\n"
        "🎤 Чтобы бот расшифровывал голосовые в чате, создайте группу и добавьте меня туда нажав на эту кнопку: ",
        reply_markup=reply_markup,

    )


async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Получаем файл голосового сообщения
        voice_file = await update.message.voice.get_file()

        # Скачиваем и конвертируем голосовое
        file_path = "voice_message.ogg"
        await voice_file.download_to_drive(file_path)
        wav_path = ogg_to_wav(file_path)

        # Распознаем текст
        text = transcribe_voice(wav_path)
        text=text[0].upper()+text[1:]
        await update.message.reply_text(f"🔊 Расшифровка:\n\n{text}")
        # Удаляем временные файлы
        os.remove(file_path)
        os.remove(wav_path)
    except Exception as e:
        print(f"Ошибка: {e}")
        await update.message.reply_text("⚠️ Произошла ошибка при обработке голосового сообщения")



def main():
    # Создаем приложение через ApplicationBuilder
    init_db()
    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(CommandHandler("statistic", statistic))

    # Запускаем бота
    application.run_polling()


if __name__ == "__main__":
    main()
