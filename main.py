
import os
import sqlite3
import requests
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
RENDER_URL = os.getenv("RENDER_EXTERNAL_URL")

TELEGRAM_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
DB_NAME = "soulnavpn.db"


# =========================
# DATABASE
# =========================

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as db:

        db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                balance INTEGER DEFAULT 0
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                status TEXT DEFAULT 'pending'
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                service_name TEXT,
                volume TEXT,
                expire_date TEXT,
                status TEXT DEFAULT 'inactive'
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS support_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                message TEXT
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS user_states (
                user_id INTEGER PRIMARY KEY,
                state TEXT
            )
        """)


# =========================
# TELEGRAM FUNCTIONS
# =========================

def send_message(chat_id, text, keyboard=None):

    payload = {
        "chat_id": chat_id,
        "text": text
    }

    if keyboard:
        payload["reply_markup"] = keyboard

    try:
        response = requests.post(
            f"{TELEGRAM_API}/sendMessage",
            json=payload,
            timeout=15
        )

        response.raise_for_status()
        return response.json()

    except requests.RequestException as error:
        print("Telegram error:", error)
        return None


def answer_callback(callback_id):

    try:
        requests.post(
            f"{TELEGRAM_API}/answerCallbackQuery",
            json={"callback_query_id": callback_id},
            timeout=15
        )

    except requests.RequestException as error:
        print("Callback error:", error)


# =========================
# MAIN MENU
# =========================

def main_menu():

    return {
        "inline_keyboard": [

            [
                {
                    "text": "🛒 خرید اشتراک",
                    "callback_data": "buy"
                },
                {
                    "text": "💰 افزایش شارژ",
                    "callback_data": "charge"
                }
            ],

            [
                {
                    "text": "🔄 تمدید سرویس",
                    "callback_data": "renew"
                },
                {
                    "text": "📦 اشتراک‌های من",
                    "callback_data": "subscriptions"
                }
            ],

            [
                {
                    "text": "📖 راهنما",
                    "callback_data": "guide"
                },
                {
                    "text": "🎧 پشتیبانی",
                    "callback_data": "support"
                }
            ]

        ]
    }


def back_menu():

    return {
        "inline_keyboard": [
            [
                {
                    "text": "🔙 بازگشت به منوی اصلی",
                    "callback_data": "menu"
                }
            ]
        ]
    }


# =========================
# USER MANAGEMENT
# =========================

def register_user(user_id, username):

    with get_db() as db:

        db.execute("""
            INSERT INTO users (user_id, username)
            VALUES (?, ?)

            ON CONFLICT(user_id)
            DO UPDATE SET username = excluded.username

        """, (user_id, username))


def get_balance(user_id):

    with get_db() as db:

        user = db.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user_id,)
        ).fetchone()

        return user["balance"] if user else 0


# =========================
# HOME
# =========================

@app.route("/", methods=["GET"])
def home():

    return "SOULNA VPN is running!"


# =========================
# WEBHOOK
# =========================

@app.route("/telegram-webhook", methods=["POST"])
def telegram_webhook():

    if (
        not WEBHOOK_SECRET
        or request.headers.get(
            "X-Telegram-Bot-Api-Secret-Token"
        ) != WEBHOOK_SECRET
    ):

        return "Unauthorized", 403

    data = request.get_json(silent=True) or {}

    # =====================
    # NORMAL MESSAGES
    # =====================

    message = data.get("message", {})

    if message:

        chat_id = message.get("chat", {}).get("id")

        user = message.get("from", {})

        user_id = user.get("id")

        username = user.get("username", "")

        text = message.get("text", "")

        if chat_id and user_id:

            register_user(user_id, username)

            if text in ["/start", "/menu"]:

                with get_db() as db:

                    db.execute(
                        "DELETE FROM user_states WHERE user_id = ?",
                        (user_id,)
                    )

                send_message(
                    chat_id,

                    "💜 به فروشگاه SOULNA VPN خوش آمدید!\n\n"
                    "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",

                    main_menu()
                )

            else:

                with get_db() as db:

                    state = db.execute(
                        "SELECT state FROM user_states WHERE user_id = ?",
                        (user_id,)
                    ).fetchone()

                if state and state["state"] == "waiting_support":

                    with get_db() as db:

                        db.execute("""
                            INSERT INTO support_messages
                            (user_id, message)
                            VALUES (?, ?)
                        """, (user_id, text))

                        db.execute(
                            "DELETE FROM user_states WHERE user_id = ?",
                            (user_id,)
                        )

                    send_message(
                        chat_id,

                        "✅ پیام شما ثبت شد.\n"
                        "پشتیبانی در اولین فرصت پاسخ خواهد داد.",

                        back_menu()
                    )

    # =====================
    # CALLBACK BUTTONS
    # =====================

    callback = data.get("callback_query")

    if callback:

        callback_id = callback.get("id")

        chat_id = callback.get(
            "message", {}
        ).get("chat", {}).get("id")

        user = callback.get("from", {})

        user_id = user.get("id")

        action = callback.get("data", "")

        answer_callback(callback_id)

        if chat_id and user_id:

            register_user(
                user_id,
                user.get("username", "")
            )

            # MAIN MENU

            if action == "menu":

                send_message(
                    chat_id,
                    "💜 منوی اصلی SOULNA VPN",
                    main_menu()
                )

            # BUY

            elif action == "buy":

                send_message(
                    chat_id,

                    "🛒 خرید اشتراک\n\n"
                    "لیست سرویس‌ها به‌زودی در این قسمت قرار می‌گیرد.",

                    back_menu()
                )

            # CHARGE

            elif action == "charge":

                keyboard = {
                    "inline_keyboard": [

                        [{
                            "text": "💰 ۱۰۰ هزار تومان",
                            "callback_data": "amount_100000"
                        }],

                        [{
                            "text": "💰 ۲۰۰ هزار تومان",
                            "callback_data": "amount_200000"
                        }],

                        [{
                            "text": "💰 ۵۰۰ هزار تومان",
                            "callback_data": "amount_500000"
                        }],

                        [{
                            "text": "🔙 بازگشت",
                            "callback_data": "menu"
                        }]

                    ]
                }

                send_message(
                    chat_id,

                    "💰 مبلغ موردنظر برای افزایش شارژ را انتخاب کنید:",

                    keyboard
                )

            # CHARGE AMOUNT

            elif action.startswith("amount_"):

                try:

                    amount = int(
                        action.replace("amount_", "")
                    )

                    if amount not in [
                        100000,
                        200000,
                        500000
                    ]:

                        raise ValueError

                    with get_db() as db:

                        db.execute("""
                            INSERT INTO payments
                            (user_id, amount, status)
                            VALUES (?, ?, 'pending')
                        """, (user_id, amount))

                    send_message(
                        chat_id,

                        f"💰 مبلغ درخواست: {amount:,} تومان\n\n"
                        "درخواست شارژ شما ثبت شد.\n"
                        "درگاه پرداخت هنوز متصل نشده است.",

                        back_menu()
                    )

                except ValueError:

                    send_message(
                        chat_id,
                        "مبلغ انتخابی معتبر نیست.",
                        back_menu()
                    )

            # RENEW

            elif action == "renew":

                send_message(
                    chat_id,

                    "🔄 تمدید سرویس\n\n"
                    "ابتدا باید اشتراک فعال شما ثبت شود.",

                    back_menu()
                )

            # SUBSCRIPTIONS

            elif action == "subscriptions":

                with get_db() as db:

                    subscriptions = db.execute("""
                        SELECT * FROM subscriptions
                        WHERE user_id = ?
                    """, (user_id,)).fetchall()

                if subscriptions:

                    result = "📦 اشتراک‌های شما:\n\n"

                    for sub in subscriptions:

                        result += (
                            f"نام سرویس: {sub['service_name']}\n"
                            f"حجم: {sub['volume']}\n"
                            f"انقضا: {sub['expire_date']}\n"
                            f"وضعیت: {sub['status']}\n\n"
                        )

                else:

                    result = (
                        "📦 هنوز اشتراکی برای شما ثبت نشده است."
                    )

                result += (
                    f"\n💰 موجودی کیف پول: "
                    f"{get_balance(user_id):,} تومان"
                )

                send_message(
                    chat_id,
                    result,
                    back_menu()
                )

            # GUIDE

            elif action == "guide":

                send_message(
                    chat_id,

                    "📖 راهنمای استفاده از SOULNA VPN\n\n"

                    "۱. از قسمت خرید اشتراک، سرویس موردنظر را انتخاب کنید.\n"

                    "۲. پس از تکمیل خرید، اطلاعات سرویس را دریافت می‌کنید.\n"

                    "۳. کانفیگ را در برنامه سازگار وارد کنید.\n\n"

                    "راهنمای کامل به‌زودی اضافه می‌شود.",

                    back_menu()
                )

            # SUPPORT

            elif action == "support":

                with get_db() as db:

                    db.execute("""
                        INSERT INTO user_states (user_id, state)

                        VALUES (?, 'waiting_support')

                        ON CONFLICT(user_id)
                        DO UPDATE SET state = 'waiting_support'

                    """, (user_id,))

                send_message(
                    chat_id,

                    "🎧 لطفاً پیام خود را برای پشتیبانی ارسال کنید:",

                    back_menu()
                )

    return "OK", 200


# =========================
# SET WEBHOOK
# =========================

def setup_webhook():

    if not all([
        BOT_TOKEN,
        WEBHOOK_SECRET,
        RENDER_URL
    ]):

        print("Webhook settings are missing.")
        return

    try:

        response = requests.post(
            f"{TELEGRAM_API}/setWebhook",

            json={
                "url": RENDER_URL.rstrip("/")
                + "/telegram-webhook",

                "secret_token": WEBHOOK_SECRET
            },

            timeout=15
        )

        print("Webhook setup:", response.text)

    except requests.RequestException as error:

        print("Webhook error:", error)


# =========================
# START APPLICATION
# =========================

if __name__ == "__main__":

    if not BOT_TOKEN:

        raise RuntimeError("BOT_TOKEN is missing")

    init_db()

    setup_webhook()

    app.run(
        host="0.0.0.0",

        port=int(os.getenv("PORT", 10000))
    )
