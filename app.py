import os
import requests
import numpy as np
import cv2
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TG_FILE = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

app = Flask(__name__)

@app.get("/")
def home():
    return "Bot is running", 200


def tg_send(chat_id: int, text: str):
    requests.post(
        f"{TG_API}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=10,
    )


def tg_get_file(file_id: str) -> str:
    r = requests.post(f"{TG_API}/getFile", json={"file_id": file_id}, timeout=10)
    r.raise_for_status()
    return r.json()["result"]["file_path"]


def download_photo(file_path: str) -> bytes:
    r = requests.get(f"{TG_FILE}/{file_path}", timeout=20)
    r.raise_for_status()
    return r.content


def signal_from_image(img_bgr):
    h, w = img_bgr.shape[:2]
    roi = img_bgr[int(h * 0.20) : int(h * 0.90), int(w * 0.10) : int(w * 0.90)]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    green = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))

    red1 = cv2.inRange(hsv, (0, 50, 50), (10, 255, 255))
    red2 = cv2.inRange(hsv, (170, 50, 50), (180, 255, 255))
    red = cv2.bitwise_or(red1, red2)

    g = int(np.sum(green > 0))
    r = int(np.sum(red > 0))
    print("GREEN", g, "RED", r)

    if g > r * 1.2 and g > 300:
        return "UP"
    if r > g * 1.2 and r > 300:
        return "DOWN"
    return "WAIT"


@app.post(f"/{BOT_TOKEN}")
def webhook():
    update = request.get_json(force=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "ok"

    chat_id = msg["chat"]["id"]

    if "photo" in msg:
        file_id = msg["photo"][-1]["file_id"]
        file_path = tg_get_file(file_id)
        content = download_photo(file_path)

        arr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)

        if img is None:
            tg_send(chat_id, "Could not read image")
            return "ok"

        sig = signal_from_image(img)
        tg_send(chat_id, f"Signal: {sig}")
        return "ok"

    text = (msg.get("text") or "").strip().lower()
    if text in ("/start", "/help"):
        tg_send(chat_id, "Send a screenshot as a photo. I will reply with UP/DOWN/WAIT.")
    else:
        tg_send(chat_id, "Send a screenshot as a photo.")
    return "ok"
