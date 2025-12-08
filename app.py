from flask import Flask, request
import requests
import os

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN env var")

def send_message(chat_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=15)

@app.post(f"/{BOT_TOKEN}")
def webhook():
    update = request.get_json(force=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "ok", 200

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip().lower()

    if text in ("/start", "/help"):
        send_message(chat_id, "Send me a screenshot as PHOTO and I will reply ✅")
        return "ok", 200

    if "photo" in msg and msg["photo"]:
        send_message(chat_id, "Photo received ✅ (analysis will be added next)")
        return "ok", 200

    send_message(chat_id, "Message received ✅")
    return "ok", 200

@app.get("/")
def home():
    return "Bot is running!", 200
