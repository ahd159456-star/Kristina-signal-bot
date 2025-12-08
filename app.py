# -*- coding: utf-8 -*-
import os
import requests
import numpy as np
import cv2
from flask import Flask, request

BOT_TOKEN = (os.environ.get("BOT_TOKEN", "") or "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN env var")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TG_FILE = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

app = Flask(__name__)


def tg_send(chat_id: int, text: str) -> None:
    try:
        requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except Exception:
        pass


def tg_get_file_path(file_id: str) -> str:
    r = requests.post(
        f"{TG_API}/getFile",
        json={"file_id": file_id},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()["result"]["file_path"]


def download_file(file_path: str) -> bytes:
    r = requests.get(f"{TG_FILE}/{file_path}", timeout=20)
    r.raise_for_status()
    return r.content


def predict_next_from_image(img_bgr: np.ndarray) -> str:
    h, w = img_bgr.shape[:2]

    # Focus on the right side where latest candles are
    y1, y2 = int(h * 0.20), int(h * 0.92)
    x1, x2 = int(w * 0.55), int(w * 0.98)

    roi = img_bgr[y1:y2, x1:x2]
    if roi.size == 0:
        return "DOWN"

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Green mask (Pocket Option green candles)
    green = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))

    # Red mask (two HSV ranges)
    red1 = cv2.inRange(hsv, (0, 50, 50), (10, 255, 255))
    red2 = cv2.inRange(hsv, (170, 50, 50), (180, 255, 255))
    red = cv2.bitwise_or(red1, red2)

    g = int(np.count_nonzero(green))
    r = int(np.count_nonzero(red))

    # Simple "next candle" heuristic:
    # - If one color dominates strongly, follow it
    # - If extremely overextended, expect small pullback
    if g >= r:
        if g > r * 3.0 and g > 2500:
            return "DOWN"
        return "UP"
    else:
        if r > g * 3.0 and r > 2500:
            return "UP"
        return "DOWN"


@app.get("/")
def home():
    return "Bot is running", 200


@app.post(f"/{BOT_TOKEN}")
def webhook():
    update = request.get_json(force=True, silent=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "ok", 200

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip().lower()

    if text in ("/start", "/help"):
        tg_send(chat_id, "Send me a Pocket Option screenshot as PHOTO (or image document).")
        return "ok", 200

    file_id = None

    # Photo
    if "photo" in msg and msg["photo"]:
        file_id = msg["photo"][-1]["file_id"]

    # Document image (sometimes screenshots come as document)
    elif "document" in msg and msg["document"]:
        doc = msg["document"]
        mime = (doc.get("mime_type") or "").lower()
        if mime.startswith("image/"):
            file_id = doc.get("file_id")

    if not file_id:
        tg_send(chat_id, "Please send the screenshot as PHOTO (or an image document).")
        return "ok", 200

    try:
        file_path = tg_get_file_path(file_id)
        content = download_file(file_path)

        arr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            tg_send(chat_id, "Could not read the image. Try sending as Photo.")
            return "ok", 200

        pred = predict_next_from_image(img)
        tg_send(chat_id, pred)
        return "ok", 200

    except Exception:
        tg_send(chat_id, "Error processing image.")
        return "ok", 200
