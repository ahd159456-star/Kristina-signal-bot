from flask import Flask, request
import os
import requests

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

@app.route("/")
def home():
    return "OK"

@app.route(f"/tg/{WEBHOOK_SECRET}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if not data:
        return "no data"

    # تأكيد استلام الرسالة
    chat_id = data["message"]["chat"]["id"]
    message = data["message"].get("text", "")

    # أوامر بسيطة
    if message == "/start":
        send_message(chat_id, "✅ البوت جاهز لاستقبال إشارات TradingView.")
    elif message == "/chatid":
        send_message(chat_id, f"📍 Chat ID: {chat_id}")
    else:
        send_message(chat_id, f"تم استلام الرسالة: {message}")

    return "ok"

def send_message(chat_id, text):
    url = f"{TELEGRAM_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    requests.post(url, json=payload)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
