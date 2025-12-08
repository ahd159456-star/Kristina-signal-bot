# -*- coding: utf-8 -*-
import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN env var")
if not WEBHOOK_SECRET:
    raise RuntimeError("Missing WEBHOOK_SECRET env var")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

def tg_send(chat_id: int, text: str):
    try:
        requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except Exception as e:
        print("tg_send error:", e)

@app.get("/")
def home():
    return "OK", 200

# Telegram webhook (to capture chat_id once)
@app.post(f"/tg/{BOT_TOKEN}")
def tg_webhook():
    update = request.get_json(force=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "ok", 200

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip()

    if text in ("/start", "/help"):
        tg_send(chat_id, "ارسل /chatid عشان أعطيك Chat ID، وبعدين TradingView هو اللي ببعت إشارات.")
        return "ok", 200

    if text == "/chatid":
        tg_send(chat_id, f"CHAT_ID={chat_id}")
        return "ok", 200

    tg_send(chat_id, "جاهز. إشارات TradingView لازم تجي من Webhook.")
    return "ok", 200

# TradingView webhook
@app.post("/tv")
def tv_webhook():
    data = request.get_json(force=True) or {}

    # security
    if data.get("secret") != WEBHOOK_SECRET:
        return {"ok": False, "error": "bad secret"}, 403

    action = (data.get("action") or "").upper().strip()   # BUY / SELL / WAIT
    symbol = (data.get("symbol") or "").upper().strip()
    tf = (data.get("tf") or "").strip()
    chat_id = data.get("chat_id")

    if not chat_id:
        return {"ok": False, "error": "missing chat_id"}, 400

    if action not in ("BUY", "SELL", "WAIT"):
        return {"ok": False, "error": "bad action"}, 400

    msg = f"{action}\n{symbol}  TF:{tf}"
    tg_send(int(chat_id), msg)
    return {"ok": True}, 200
