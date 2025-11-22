from flask import Flask, request, jsonify, send_from_directory,send_file
from flask_cors import CORS  # <-- импортируем
import os
from dotenv import load_dotenv
import requests

load_dotenv()

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

@app.route('/')
def index():
    return send_from_directory('.', 'site2.html')  # или ваше имя файла

@app.route('/<path:filename>')
def static_files(filename):
    return send_from_directory('.', filename)

@app.route('/submit-payment', methods=['POST'])
def submit_payment():
    data = request.json
    user_name = data.get('name', 'Не указано')
    order_id = len(orders) + 1
    orders[order_id] = {'name': user_name, 'status': 'pending'}

    text = f"🔔 Новая заявка!\nID: {order_id}\nИмя: {user_name}"
    keyboard = {
        "inline_keyboard": [
            [{"text": "✅ Подтвердить", "callback_data": f"confirm_{order_id}"}],
            [{"text": "❌ Отклонить", "callback_data": f"reject_{order_id}"}]
        ]
    }
    send_telegram_message(int(YOUR_TELEGRAM_ID), text, keyboard)
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
    if 'callback_query' in update:
        query = update['callback_query']
        data = query['data']
        requests.post(f'https://api.telegram.org/bot{BOT_TOKEN}/answerCallbackQuery',
                      json={'callback_query_id': query['id']})

        if data.startswith('confirm_'):
            order_id = int(data.split('_')[1])
            if order_id in orders:
                orders[order_id]['status'] = 'confirmed'
                send_telegram_message(int(YOUR_TELEGRAM_ID), f"✅ Заявка {order_id} подтверждена.")
        elif data.startswith('reject_'):
            order_id = int(data.split('_')[1])
            if order_id in orders:
                orders[order_id]['status'] = 'rejected'
                send_telegram_message(int(YOUR_TELEGRAM_ID), f"❌ Заявка {order_id} отклонена.")
    return 'OK'

if __name__ == '__main__':
    app.run(debug=True, port=5000)