
import os
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"


def send_message(chat_id, text, keyboard=None):
    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    return requests.post(
        f"{TELEGRAM_API}/sendMessage",
        json=payload,
        timeout=15
    )


def main_menu():
    return {
        "inline_keyboard": [
            [{"text": "🛒 خرید اشتراک", "callback_data": "buy"}],
            [{"text": "💰 شارژ حساب", "callback_data": "charge"}],
            [{"text": "📦 اشتراک‌های من", "callback_data": "subscriptions"}],
            [{"text": "🎧 پشتیبانی", "callback_data": "support"}],
            [{"text": "📖 راهنمای استفاده", "callback_data": "guide"}]
        ]
    }


@app.route("/", methods=["GET"])
def home():
    return "soulnavpn is running!"


@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():

    if not WEBHOOK_SECRET or request.headers.get(
        "X-Telegram-Bot-Api-Secret-Token"
    ) != WEBHOOK_SECRET:
        return "Unauthorized", 403

    data = request.get_json(silent=True) or {}

    message = data.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")

    if chat_id and text in ["/start", "/menu"]:
        send_message(
            chat_id,
            "💜 به فروشگاه SOULNA VPN خوش آمدید!\n\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            main_menu()
        )

    callback = data.get("callback_query")

    if callback:
        callback_id = callback.get("id")
        chat_id = callback.get("message", {}).get("chat", {}).get("id")
        action = callback.get("data", "")

        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_id},
            timeout=15
        )

        if chat_id:
            if action == "charge":
                keyboard = {
                    "inline_keyboard": [
                        [{"text": "💰 100 هزار تومان", "callback_data": "amount_100000"}],
                        [{"text": "💰 200 هزار تومان", "callback_data": "amount_200000"}],
                        [{"text": "💰 500 هزار تومان", "callback_data": "amount_500000"}],
                        [{"text": "🔙 بازگشت", "callback_data": "menu"}]
                    ]
                }

                send_message(
                    chat_id,
                    "💰 مبلغ موردنظر برای شارژ حساب را انتخاب کنید:",
                    keyboard
                )

            elif action.startswith("amount_"):
                amount = action.replace("amount_", "")

                send_message(
                    chat_id,
                    f"مبلغ انتخابی شما: {amount} تومان\n\n"
                    "درگاه پرداخت هنوز متصل نشده است."
                )

            elif action == "buy":
                send_message(
                    chat_id,
                    "🛒 بخش خرید اشتراک به‌زودی فعال می‌شود."
                )

            elif action == "subscriptions":
                send_message(
                    chat_id,
                    "📦 هنوز اشتراکی برای نمایش ثبت نشده است."
                )

            elif action == "support":
                send_message(
                    chat_id,
                    "🎧 برای دریافت پشتیبانی پیام خود را ارسال کنید."
                )

            elif action == "guide":
                send_message(
                    chat_id,
                    "📖 راهنمای استفاده از SOULNA VPN به‌زودی منتشر می‌شود."
                )

            elif action == "menu":
                send_message(
                    chat_id,
                    "💜 منوی اصلی SOULNA VPN",
                    main_menu()
                )

    return "OK", 200


def setup_webhook():
    if not all([BOT_TOKEN, WEBHOOK_SECRET, RENDER_URL]):
        print("Webhook settings are missing.")
        return

    response = requests.post(
        f"{TELEGRAM_API}/setWebhook",
        json={
            "url": RENDER_URL.rstrip("/") + "/telegram-webhook",
            "secret_token": WEBHOOK_SECRET
        },
        timeout=15
    )

    print("Webhook setup:", response.text)


if __name__ == "__main__":
    setup_webhook()

    app.run(
        host="0.0.0.0",
        port=int(os.getenv("PORT", 10000))
    )
