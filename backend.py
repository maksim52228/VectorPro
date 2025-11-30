from flask import Flask, request, jsonify, send_from_directory,send_file
from flask_cors import CORS  # <-- импортируем
import os
import requests
import json
import uuid
from datetime import datetime

SUPPORT_DIR = 'support_chats'
os.makedirs(SUPPORT_DIR, exist_ok=True)
BOT_TOKEN = os.getenv('BOT_TOKEN')
YOUR_TELEGRAM_ID = os.getenv('YOUR_TELEGRAM_ID')  # ← Теперь будет строка, а не None
APP_FILE_PATH = os.getenv('APP_FILE_PATH', 'VectorPro.exe')
app = Flask(__name__)
CORS(app)
# Хранилище заказов (в реальности — лучше SQLite или PostgreSQL)
orders = {}  # {1: {'name': 'Иван', 'status': 'pending'}}

def send_telegram_message(chat_id, text, reply_markup=None):
    url = f'https://api.telegram.org/bot{BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'HTML'}
    if reply_markup:
        data['reply_markup'] = reply_markup
    requests.post(url, json=data)

# === Маршруты ===
@app.route('/support/send', methods=['POST'])
def send_support_message():
    data = request.json
    chat_id = data.get('chat_id')
    text = data.get('text', '').strip()

    if not chat_id or not text:
        return jsonify({"error": "Требуется chat_id и text"}), 400

    chat_file = f"{SUPPORT_DIR}/{chat_id}.json"
    if not os.path.exists(chat_file):
        return jsonify({"error": "Чат не найден"}), 404

    # Загружаем чат и добавляем сообщение
    with open(chat_file, "r+", encoding="utf-8") as f:
        chat = json.load(f)
        chat["messages"].append({
            "from": "user",
            "text": text,
            "timestamp": datetime.utcnow().isoformat()
        })
        f.seek(0)
        json.dump(chat, f, ensure_ascii=False, indent=2)
        f.truncate()

    # 💡 Опционально: уведомить админа в Telegram
    send_telegram_message(
        YOUR_TELEGRAM_ID,
        f"📩 Новое сообщение в чате>{chat_id}:\n\n{text}"
    )

    return jsonify({"status": "ok"})

@app.route('/')
def index():
    return send_from_directory('.', 'site2.html')  # или ваше имя файла

@app.route('/support/start', methods=['POST'])
def start_support_chat():
    data = request.json
    user_info = data.get('info', 'Аноним')
    chat_id = str(uuid.uuid4())[:8]  # Например: a1b2c3d4

    chat_data = {
        "user_info": user_info,
        "created_at": datetime.utcnow().isoformat(),
        "messages": []
    }

    with open(f"{SUPPORT_DIR}/{chat_id}.json", "w", encoding="utf-8") as f:
        json.dump(chat_data, f, ensure_ascii=False, indent=2)

    # Уведомление админу
    text = f"💬 Новый чат поддержки!\nID: <code>{chat_id}</code> \nИнфо: {user_info}"
    send_telegram_message(YOUR_TELEGRAM_ID, text)

    return jsonify({"chat_id": chat_id})
@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

@app.route('/submit-payment', methods=['POST'])
def submit_payment():
    data = request.json
    user_name = data.get('name', 'Не указано')
    order_id = len(orders) + 1
    orders[order_id] = {'name': user_name, 'status': 'pending'}

    text = f"🔔 Новая заявка!\nID: `{order_id}`\nИмя: {user_name}"
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Подтвердить", "callback_data": f"confirm_{order_id}"}],
            [{"text": "❌ Отклонить", "callback_data": f"reject_{order_id}"}]
        ]
    }
    send_telegram_message(YOUR_TELEGRAM_ID, text, keyboard)
    return jsonify({"order_id": order_id})

@app.route('/check-status/<int:order_id>')
def check_status(order_id):
    order = orders.get(order_id)
    if order:
        return jsonify({"status": order["status"]})
    return jsonify({"status": "not_found"}), 404

@app.route('/download/<int:order_id>')
def download_file(order_id):
    order = orders.get(order_id)
    if order and order["status"] == "confirmed":
        if os.path.exists(APP_FILE_PATH):
            return send_file(APP_FILE_PATH, as_attachment=True)
        else:
            return "Файл не найден", 404
    return "Доступ запрещён", 403

@app.route('/webhook', methods=['POST'])
def telegram_webhook():
    update = request.json

    # Обработка callback (как раньше)
    if 'callback_query' in update:
        query = update['callback_query']
        data = query['data']
        requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery',
                      json={'callback_query_id': query['id']})
        if data.startswith('confirm_'):
            order_id = int(data.split('_')[1])
            if order_id in orders:
                orders[order_id]['status'] = 'confirmed'
                send_telegram_message(YOUR_TELEGRAM_ID, f"✅ Заявка {order_id} подтверждена.")
        elif data.startswith('reject_'):
            order_id = int(data.split('_')[1])
            if order_id in orders:
                orders[order_id]['status'] = 'rejected'
                send_telegram_message(YOUR_TELEGRAM_ID, f"❌ Заявка {order_id} отклонена.")
        return 'OK'

    # Обработка текстовых сообщений от админа
    if 'message' in update:
        message = update['message']
        if 'text' in message and str(message['chat']['id']) == YOUR_TELEGRAM_ID:
            text = message['text'].strip()

            # Формат: "ID123 Ваш ответ пользователю"
            if ' ' in text:
                parts = text.split(' ', 1)
                potential_id = parts[0]
                reply_text = parts[1]

                # Проверим, существует ли такой чат
                chat_file = f"{SUPPORT_DIR}/{potential_id}.json"
                if os.path.exists(chat_file):
                    with open(chat_file, "r+", encoding="utf-8") as f:
                        chat = json.load(f)
                        chat["messages"].append({
                            "from": "admin",
                            "text": reply_text,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                        f.seek(0)
                        json.dump(chat, f, ensure_ascii=False, indent=2)
                        f.truncate()

                    send_telegram_message(YOUR_TELEGRAM_ID, f"✅ Ответ отправлен в чат {potential_id}.")
                else:
                    send_telegram_message(YOUR_TELEGRAM_ID, f"❌ Чат с ID {potential_id} не найден.")
            else:
                send_telegram_message(YOUR_TELEGRAM_ID, "Неверный формат. Пример:\n`a1b2c3d4 Привет!`",)

    return 'OK'

@app.route('/support/messages/<chat_id>')
def get_support_messages(chat_id):
    chat_file = f"{SUPPORT_DIR}/{chat_id}.json"
    if not os.path.exists(chat_file):
        return jsonify({"error": "Чат не найден"}), 404
    with open(chat_file, "r", encoding="utf-8") as f:
        chat = json.load(f)
    return jsonify(chat)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
