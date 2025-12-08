import os
import requests
import numpy as np
import cv2
from flask import Flask, request

BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Missing BOT_TOKEN env var")

TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TG_FILE = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

app = Flask(__name__)

def tg_send(chat_id: int, text: str):
    try:
        requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": chat_id, "text": text},
            timeout=15,
        )
    except Exception as e:
        print("tg_send error:", e)

def tg_get_file(file_id: str) -> str:
    r = requests.post(f"{TG_API}/getFile", json={"file_id": file_id}, timeout=15)
    r.raise_for_status()
    return r.json()["result"]["file_path"]

def download_file(file_path: str) -> bytes:
    r = requests.get(f"{TG_FILE}/{file_path}", timeout=20)
    r.raise_for_status()
    return r.content

def detect_signal_from_image(img_bgr: np.ndarray):
    # ROI: adjust if needed (this tries to focus on the right side of the chart)
    h, w = img_bgr.shape[:2]
    y1, y2 = int(h * 0.20), int(h * 0.92)
    x1, x2 = int(w * 0.55), int(w * 0.98)
    roi = img_bgr[y1:y2, x1:x2]

    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # Green range
    green = cv2.inRange(hsv, (35, 40, 40), (85, 255, 255))

    # Red range (two parts in HSV)
    red1 = cv2.inRange(hsv, (0, 50, 50), (10, 255, 255))
    red2 = cv2.inRange(hsv, (170, 50, 50), (180, 255, 255))
    red = cv2.bitwise_or(red1, red2)

    g = int(np.count_nonzero(green))
    r = int(np.count_nonzero(red))

    # Decide based on dominance + minimum pixels
    if g > r * 1.2 and g > 300:
        return "UP", g, r
    if r > g * 1.2 and r > 300:
        return "DOWN", g, r
    return "WAIT", g, r

@app.get("/")
def home():
    return "Bot is running", 200

@app.post(f"/{BOT_TOKEN}")
def webhook():
    update = request.get_json(force=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "ok", 200

    chat_id = msg["chat"]["id"]

    text = (msg.get("text") or "").strip().lower()
    if text in ("/start", "/help"):
        tg_send(
            chat_id,
            "Send me a Pocket Option screenshot (as Photo). I will detect: UP / DOWN / WAIT.",
        )
        return "ok", 200

    file_id = None

    # Photo message
    if "photo" in msg and msg["photo"]:
        file_id = msg["photo"][-1]["file_id"]

    # Sometimes screenshots come as a document (image)
    elif "document" in msg and msg["document"]:
        doc = msg["document"]
        mime = (doc.get("mime_type") or "").lower()
        if mime.startswith("image/"):
            file_id = doc["file_id"]

    if not file_id:
        tg_send(chat_id, "Please send a screenshot as PHOTO (or image document).")
        return "ok", 200

    try:
        file_path = tg_get_file(file_id)
        content = download_file(file_path)

        arr = np.frombuffer(content, np.uint8)
        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        if img is None:
            tg_send(chat_id, "Could not read the image. Try sending as Photo.")
            return "ok", 200

        signal, g, r = detect_signal_from_image(img)
        tg_send(chat_id, f"Signal: {signal}\nGreen={g} Red={r}")

    except Exception as e:
        print("process error:", e)
        tg_send(chat_id, f"Error: {type(e).__name__}")

    return "ok", 200
