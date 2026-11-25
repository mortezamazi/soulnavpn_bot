
import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")


@app.route("/", methods=["GET"])
def home():
    return "soulnavpn is running!"


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():
    if request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    ) != WEBHOOK_SECRET:
        return "Unauthorized", 403

    data = request.get_json(silent=True) or {}
    message = data.get("message", {})
    text = message.get("text", "")
    chat_id = message.get("chat", {}).get("id")

    if chat_id and text == "/start":
        requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": "به soulnavpn خوش آمدی! 💜\n\nبه‌زودی امکانات جدید در دسترس خواهند بود."
            },
            timeout=15
        )

    return "OK", 200


def setup_webhook():
    if not all([BOT_TOKEN, WEBHOOK_SECRET, RENDER_URL]):
        print("Webhook settings are missing.")
        return

    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
        json={
            "url": RENDER_URL.rstrip("/") + "/telegram-webhook",
            "secret_token": WEBHOOK_SECRET
        },
        timeout=15
    )

    print("Webhook setup:", response.text)


if __name__ == "__main__":
    setup_webhook()
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
