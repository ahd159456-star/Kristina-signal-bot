import os, requests, numpy as np, cv2
from flask import Flask, request

BOT_TOKEN = os.environ["BOT_TOKEN"]
TG_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
TG_FILE = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

app = Flask(__name__)

def tg_send(chat_id: int, text: str):
    requests.post(f"{TG_API}/sendMessage", data={"chat_id": chat_id, "text": text}, timeout=15)

def tg_get_file(file_id: str):
    r = requests.post(f"{TG_API}/getFile", data={"file_id": file_id}, timeout=15)
    r.raise_for_status()
    return r.json()["result"]["file_path"]

def download_photo(file_path: str) -> bytes:
    r = requests.get(f"{TG_FILE}/{file_path}", timeout=20)
    r.raise_for_status()
    return r.content

def signal_from_image(img_bgr):
    h, w = img_bgr.shape[:2]
    roi = img_bgr[int(h*0.15):int(h*0.9), int(w*0.78):w]
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    green = cv2.inRange(hsv, (35, 60, 60), (90, 255, 255))
    red1  = cv2.inRange(hsv, (0, 60, 60),  (12, 255, 255))
    red2  = cv2.inRange(hsv, (165, 60, 60),(179, 255, 255))
    red = cv2.bitwise_or(red1, red2)

    g = int(np.sum(green > 0))
    r = int(np.sum(red > 0))

    if g > r * 1.25 and g > 1200:
        return "📈 طلوع"
    if r > g * 1.25 and r > 1200:
        return "📉 نزول"
    return "⏳ انتظار"

@app.post(f"/{BOT_TOKEN}")
def webhook():
    update = request.get_json(force=True) or {}
    msg = update.get("message") or update.get("edited_message")
    if not msg:
        return "ok"

    chat_id = msg["chat"]["id"]
    text = (msg.get("text") or "").strip().lower()

    if text in ("/start", "/help"):
        tg_send(chat_id, "ابعث سكرينشوت للشارت 1m وأنا برد طلوع/نزول للشمعة الجاي.")
        return "ok"

    photos = msg.get("photo")
    if not photos:
        tg_send(chat_id, "ابعت صورة (سكرينشوت) للشارت 1m.")
        return "ok"

    file_id = photos[-1]["file_id"]
    file_path = tg_get_file(file_id)
    img_bytes = download_photo(file_path)

    arr = np.frombuffer(img_bytes, dtype=np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        tg_send(chat_id, "ما قدرت أقرأ الصورة. جرّب تبعثها واضحة.")
        return "ok"

    sig = signal_from_image(img)
    tg_send(chat_id, f"{sig}\n⏱️ 1m للشمعة الجاي")
    return "ok"
