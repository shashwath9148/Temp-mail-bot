import telebot
import requests
import random
import string
from telebot import types
from flask import Flask, request
import time
import os
import re
import logging

# -----------------------------
# LOGGING
# -----------------------------
logging.basicConfig(level=logging.INFO)

# -----------------------------
# CONFIG
# -----------------------------
BOT_TOKEN = "8245435693:AAHtqJCSCphtU5mGkosOQ7XgD_eSIsP3HyQ"  # Your bot token
WEBHOOK_URL = "https://temp-mail-bot-1aqf.onrender.com"        # Your Render app URL
bot = telebot.TeleBot(BOT_TOKEN, parse_mode="MarkdownV2")

API_1SECMAIL = "https://www.1secmail.com/api/v1/"

OWNER_LINK = "https://t.me/shashu9148"
BRAND = "🛡️ *Created & Secured by S H Λ S H U*"

# Store last 5 emails per user
user_emails = {}

# -----------------------------
# HELPER: ESCAPE MARKDOWNV2
# -----------------------------
def escape_md(text):
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

# -----------------------------
# EMAIL GENERATOR
# -----------------------------
def generate_random_email():
    try:
        resp = requests.get(f"{API_1SECMAIL}?action=genRandomMailbox&count=1", timeout=5).json()
        if resp and isinstance(resp, list):
            return resp[0]
    except Exception as e:
        logging.error(f"Error generating email: {e}")
    local = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"{local}@1secmail.com"

# -----------------------------
# FETCH EMAILS
# -----------------------------
def fetch_messages(email):
    try:
        login, domain = email.split("@")
        resp = requests.get(f"{API_1SECMAIL}?action=getMessages&login={login}&domain={domain}", timeout=5).json()
        return resp if isinstance(resp, list) else []
    except Exception as e:
        logging.error(f"Error fetching messages for {email}: {e}")
        return []

def fetch_message_content(email, message_id):
    try:
        login, domain = email.split("@")
        resp = requests.get(f"{API_1SECMAIL}?action=readMessage&login={login}&domain={domain}&id={message_id}", timeout=5).json()
        return resp
    except Exception as e:
        logging.error(f"Error fetching message content for {email} id {message_id}: {e}")
        return None

# -----------------------------
# TELEGRAM HANDLERS
# -----------------------------
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📧 Generate Email", callback_data="gen_email"),
        types.InlineKeyboardButton("📥 Inbox", callback_data="inbox"),
        types.InlineKeyboardButton("ℹ️ Help", callback_data="help"),
        types.InlineKeyboardButton("👑 Owner", url=OWNER_LINK)
    )

    welcome_text = (
        "👋 *Hello, Explorer!*\n\n"
        "Welcome to **Temp Mail Bot Premium** – your ultimate shield against spam!\n\n"
        "🛡️ Generate disposable emails instantly.\n"
        "⚡ Stay safe, private, and hassle\\-free.\n\n"
        f"{BRAND}"
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id

    if call.data == "gen_email":
        email = generate_random_email()
        if not email:
            bot.answer_callback_query(call.id, "❌ Failed to generate email!")
            return

        user_emails.setdefault(chat_id, []).append(email)
        if len(user_emails[chat_id]) > 5:
            user_emails[chat_id].pop(0)

        bot.answer_callback_query(call.id, "✅ Email generated!")

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📧 New Email", callback_data="gen_email"),
            types.InlineKeyboardButton("📋 Copy Email", callback_data=f"copy_{email}"),
            types.InlineKeyboardButton("📥 Inbox", callback_data="inbox")
        )

        bot.edit_message_text(
            chat_id=chat_id,
            message_id=call.message.message_id,
            text=f"📬 *Your Temporary Email:*\n`{escape_md(email)}`\n\n✨ Tap buttons below to copy, refresh, or open inbox.\n\n{BRAND}",
            reply_markup=markup
        )

    elif call.data.startswith("copy_"):
        email = call.data.replace("copy_", "")
        bot.answer_callback_query(call.id, text=f"📋 Email copied:\n{escape_md(email)}", show_alert=True)

    elif call.data == "inbox":
        bot.answer_callback_query(call.id)
        emails = user_emails.get(chat_id, [])
        if not emails:
            bot.send_message(chat_id, "📭 No emails yet. Tap Generate Email first.\n\n" + BRAND)
            return

        markup = types.InlineKeyboardMarkup()
        for email in emails:
            markup.add(types.InlineKeyboardButton(escape_md(email), callback_data=f"view_{email}"))
        bot.send_message(chat_id, "📭 *Your Inbox:* Tap an email to view messages.\n\n" + BRAND, reply_markup=markup)

    elif call.data.startswith("view_"):
        email = call.data.replace("view_", "")
        bot.answer_callback_query(call.id)
        messages = fetch_messages(email)
        if not messages:
            bot.send_message(chat_id, f"📪 No messages for `{escape_md(email)}` yet.\n\n{BRAND}")
            return

        markup = types.InlineKeyboardMarkup()
        for msg in messages[-5:][::-1]:
            preview = f"{escape_md(msg['from'])} | {escape_md(msg.get('subject','No Subject'))[:25]}"
            markup.add(types.InlineKeyboardButton(f"📩 {preview}", callback_data=f"read_{email}_{msg['id']}"))

        bot.send_message(chat_id, f"📬 *Messages for:* `{escape_md(email)}`\n\nTap to read:", reply_markup=markup)

    elif call.data.startswith("read_"):
        try:
            parts = call.data.split("_")
            email = parts[1]
            msg_id = parts[2]
        except:
            bot.answer_callback_query(call.id, "❌ Invalid message ID")
            return

        content = fetch_message_content(email, msg_id)
        if not content:
            bot.send_message(chat_id, f"❌ Failed to fetch message content for `{escape_md(email)}`.")
            return

        text = f"📧 *From:* {escape_md(content.get('from','Unknown'))}\n"
        text += f"📝 *Subject:* {escape_md(content.get('subject','No Subject'))}\n"
        text += f"📅 *Date:* {escape_md(content.get('date','Unknown'))}\n\n"
        text += f"{escape_md(content.get('textBody','[No Body]'))}\n\n{BRAND}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Inbox", callback_data="inbox"))

        bot.send_message(chat_id, text, reply_markup=markup)

    elif call.data == "help":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📧 Generate Email", callback_data="gen_email"),
            types.InlineKeyboardButton("👑 Owner", url=OWNER_LINK)
        )
        help_text = (
            "ℹ️ *Help Menu*\n\n"
            "📧 Generate Email → Get a new temp email.\n"
            "📥 Inbox → View generated emails.\n"
            "📩 Tap a message → Read it inline.\n"
            "📋 Copy Email → Quick copy.\n"
            "👑 Owner → Contact the creator."
        )
        bot.send_message(chat_id, f"{help_text}\n\n{BRAND}", reply_markup=markup)

# -----------------------------
# FLASK WEBHOOK SERVER
# -----------------------------
app = Flask(__name__)

@app.route(f"/{BOT_TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return "!", 200

@app.route("/", methods=["GET"])
def index():
    return "🚀 Temp Mail Bot Premium is running!", 200

# -----------------------------
# AUTO-SET WEBHOOK
# -----------------------------
bot.remove_webhook()
bot.set_webhook(url=f"{WEBHOOK_URL}/{BOT_TOKEN}")

# -----------------------------
# LOCAL DEV SERVER
# -----------------------------
if __name__ == "__main__":
    print("🚀 Starting Temp Mail Bot Premium (DEV MODE)...")
    time.sleep(2)
    app.run(debug=True)
