import os
import requests
from flask import Flask, request

BOT_TOKEN = (os.environ.get("BOT_TOKEN") or "").strip()
TV_SECRET = (os.environ.get("TV_SECRET") or "").strip()
CHAT_ID   = (os.environ.get("CHAT_ID") or "").strip()

if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN env var")
if not TV_SECRET:
    raise RuntimeError("Missing TV_SECRET env var")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

app = Flask(__name__)

def tg_send(text: str):
    if not CHAT_ID:
        print("CHAT_ID missing. Set it in Render Environment.")
        return
    requests.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text},
        timeout=15,
    )

@app.get("/")
def home():
    return "TV -> Telegram bridge is running", 200

@app.post(f"/tv/{TV_SECRET}")
def tv_webhook():
    if request.is_json:
        data = request.get_json(silent=True) or {}
        raw = str(data.get("signal") or data.get("action") or data.get("text") or "").strip()
    else:
        raw = (request.data or b"").decode("utf-8", errors="ignore").strip()

    s = raw.upper()

    if s in ("BUY", "CALL", "LONG", "UP"):
        tg_send("BUY")
        return "ok", 200
    if s in ("SELL", "PUT", "SHORT", "DOWN"):
        tg_send("SELL")
        return "ok", 200

    if "BUY" in s:
        tg_send("BUY")
        return "ok", 200
    if "SELL" in s:
        tg_send("SELL")
        return "ok", 200

    print("Unknown TradingView payload:", raw)
    return "bad signal", 400
