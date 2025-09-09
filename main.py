import telebot
import requests
import random
import string
from telebot import types
from flask import Flask, request
import os
import time

# -----------------------------
# CONFIG
# -----------------------------
BOT_TOKEN = os.environ.get("BOT_TOKEN")  # Set in Render Environment Variables
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # e.g., https://temp-mail-bot-1aqf.onrender.com
bot = telebot.TeleBot(BOT_TOKEN)

API_1SECMAIL = "https://www.1secmail.com/api/v1/"

OWNER_LINK = "https://t.me/shashu9148"
BRAND = "🛡️ *Created & Secured by S H Λ S H U*"

# Store last 5 emails per user
user_emails = {}

# -----------------------------
# EMAIL GENERATOR
# -----------------------------
def generate_random_email():
    try:
        resp = requests.get(f"{API_1SECMAIL}?action=genRandomMailbox&count=1", timeout=5).json()
        if resp and isinstance(resp, list):
            return resp[0]
    except:
        pass
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
    except:
        return []

def fetch_message_content(email, message_id):
    try:
        login, domain = email.split("@")
        resp = requests.get(f"{API_1SECMAIL}?action=readMessage&login={login}&domain={domain}&id={message_id}", timeout=5).json()
        return resp
    except:
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
        "⚡ Stay safe, private, and hassle-free.\n\n"
        f"{BRAND}"
    )

    bot.send_message(message.chat.id, welcome_text, reply_markup=markup, parse_mode="MarkdownV2")

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id

    # ----------------- Generate / Refresh Email -----------------
    if call.data == "gen_email":
        email = generate_random_email()
        if not email:
            bot.answer_callback_query(call.id, "❌ Failed to generate email!")
            return

        # Save last emails per user
        if chat_id not in user_emails:
            user_emails[chat_id] = []
        user_emails[chat_id].append(email)
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
            text=f"📬 *Your Temporary Email:*\n`{email}`\n\n✨ Tap buttons below to copy, refresh, or open inbox.\n\n{BRAND}",
            reply_markup=markup,
            parse_mode="MarkdownV2"
        )

    # ----------------- Copy Email -----------------
    elif call.data.startswith("copy_"):
        email = call.data.replace("copy_", "")
        bot.answer_callback_query(call.id, text=f"📋 Email copied:\n{email}", show_alert=True)

    # ----------------- Inbox -----------------
    elif call.data == "inbox":
        bot.answer_callback_query(call.id)
        emails = user_emails.get(chat_id, [])
        if not emails:
            bot.send_message(chat_id, "📭 You have no generated emails yet. Tap *Generate Email* first.\n\n" + BRAND, parse_mode="MarkdownV2")
            return

        markup = types.InlineKeyboardMarkup()
        for email in emails:
            markup.add(types.InlineKeyboardButton(email, callback_data=f"view_{email}"))
        bot.send_message(chat_id, "📭 *Your Email Inbox:* Tap an email to view messages.\n\n" + BRAND, reply_markup=markup, parse_mode="MarkdownV2")

    # ----------------- View Email -----------------
    elif call.data.startswith("view_"):
        email = call.data.replace("view_", "")
        bot.answer_callback_query(call.id)
        messages = fetch_messages(email)
        if not messages:
            bot.send_message(chat_id, f"📪 *No messages found* for `{email}` yet.\n\n{BRAND}", parse_mode="MarkdownV2")
            return

        markup = types.InlineKeyboardMarkup()
        for msg in messages[-5:][::-1]:
            msg_preview = msg['from'][:20] + ("..." if len(msg['from'])>20 else "")
            markup.add(types.InlineKeyboardButton(f"📩 {msg_preview}", callback_data=f"read_{email}_{msg['id']}"))

        bot.send_message(chat_id, f"📬 *Messages for:* `{email}`\n\nTap to read:", reply_markup=markup, parse_mode="MarkdownV2")

    # ----------------- Read Message -----------------
    elif call.data.startswith("read_"):
        parts = call.data.split("_")
        email = parts[1]
        msg_id = parts[2]
        content = fetch_message_content(email, msg_id)
        if not content:
            bot.send_message(chat_id, f"❌ Failed to fetch message content for `{email}`.", parse_mode="MarkdownV2")
            return

        text = f"📧 *From:* {content.get('from','Unknown')}\n"
        text += f"📝 *Subject:* {content.get('subject','No Subject')}\n"
        text += f"📅 *Date:* {content.get('date','Unknown')}\n\n"
        text += f"{content.get('textBody','[No Body]')}\n\n{BRAND}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Inbox", callback_data="inbox"))

        bot.send_message(chat_id, text, parse_mode="MarkdownV2", reply_markup=markup)

    # ----------------- Help -----------------
    elif call.data == "help":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📧 Generate Email", callback_data="gen_email"),
            types.InlineKeyboardButton("👑 Owner", url=OWNER_LINK)
        )
        help_text = (
            "ℹ️ *Help Menu*\n\n"
            "📧 *Generate Email* → Create a new temporary email instantly.\n"
            "📥 *Inbox* → View emails you’ve generated.\n"
            "📩 Tap a message → Read full content inline.\n"
            "📋 *Copy Email* → Copy to clipboard.\n"
            "👑 *Owner* → Contact the creator for support."
        )
        bot.send_message(chat_id, f"{help_text}\n\n{BRAND}", reply_markup=markup, parse_mode="MarkdownV2")

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
# RUN FLASK
# -----------------------------
if __name__ == "__main__":
    print("🚀 Starting Temp Mail Bot Premium...")
    time.sleep(2)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))        for email in emails:
            markup.add(types.InlineKeyboardButton(email, callback_data=f"view_{email}"))
        bot.send_message(chat_id, "📭 *Your Email Inbox:* Tap an email to view messages.\n\n" + BRAND, reply_markup=markup, parse_mode="MarkdownV2")

    # ----------------- View Email -----------------
    elif call.data.startswith("view_"):
        email = call.data.replace("view_", "")
        bot.answer_callback_query(call.id)
        messages = fetch_messages(email)
        if not messages:
            bot.send_message(chat_id, f"📪 *No messages found* for `{email}` yet.\n\n{BRAND}", parse_mode="MarkdownV2")
            return

        markup = types.InlineKeyboardMarkup()
        for msg in messages[-5:][::-1]:
            msg_preview = msg['from'][:20] + ("..." if len(msg['from'])>20 else "")
            markup.add(types.InlineKeyboardButton(f"📩 {msg_preview}", callback_data=f"read_{email}_{msg['id']}"))

        bot.send_message(chat_id, f"📬 *Messages for:* `{email}`\n\nTap to read:", reply_markup=markup, parse_mode="MarkdownV2")

    # ----------------- Read Message -----------------
    elif call.data.startswith("read_"):
        parts = call.data.split("_")
        email = parts[1]
        msg_id = parts[2]
        content = fetch_message_content(email, msg_id)
        if not content:
            bot.send_message(chat_id, f"❌ Failed to fetch message content for `{email}`.", parse_mode="MarkdownV2")
            return

        text = f"📧 *From:* {content.get('from','Unknown')}\n"
        text += f"📝 *Subject:* {content.get('subject','No Subject')}\n"
        text += f"📅 *Date:* {content.get('date','Unknown')}\n\n"
        text += f"{content.get('textBody','[No Body]')}\n\n{BRAND}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Inbox", callback_data="inbox"))

        bot.send_message(chat_id, text, parse_mode="MarkdownV2", reply_markup=markup)

    # ----------------- Help -----------------
    elif call.data == "help":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📧 Generate Email", callback_data="gen_email"),
            types.InlineKeyboardButton("👑 Owner", url=OWNER_LINK)
        )
        help_text = (
            "ℹ️ *Help Menu*\n\n"
            "📧 *Generate Email* → Create a new temporary email instantly.\n"
            "📥 *Inbox* → View emails you’ve generated.\n"
            "📩 Tap a message → Read full content inline.\n"
            "📋 *Copy Email* → Copy to clipboard.\n"
            "👑 *Owner* → Contact the creator for support."
        )
        bot.send_message(chat_id, f"{help_text}\n\n{BRAND}", reply_markup=markup, parse_mode="MarkdownV2")

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
# RUN FLASK
# -----------------------------
if __name__ == "__main__":
    print("🚀 Starting Temp Mail Bot Premium...")
    time.sleep(2)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))            parse_mode="MarkdownV2"
        )

    # ----------------- Copy Email -----------------
    elif call.data.startswith("copy_"):
        email = call.data.replace("copy_", "")
        bot.answer_callback_query(call.id, text=f"📋 Email copied:\n{email}", show_alert=True)

    # ----------------- Inbox -----------------
    elif call.data == "inbox":
        bot.answer_callback_query(call.id)
        emails = user_emails.get(chat_id, [])
        if not emails:
            bot.send_message(chat_id, "📭 You have no generated emails yet. Tap *Generate Email* first.\n\n" + BRAND, parse_mode="MarkdownV2")
            return

        markup = types.InlineKeyboardMarkup()
        for email in emails:
            markup.add(types.InlineKeyboardButton(email, callback_data=f"view_{email}"))
        bot.send_message(chat_id, "📭 *Your Email Inbox:* Tap an email to view messages.\n\n" + BRAND, reply_markup=markup, parse_mode="MarkdownV2")

    # ----------------- View Email -----------------
    elif call.data.startswith("view_"):
        email = call.data.replace("view_", "")
        bot.answer_callback_query(call.id)
        messages = fetch_messages(email)
        if not messages:
            bot.send_message(chat_id, f"📪 *No messages found* for `{email}` yet.\n\n{BRAND}", parse_mode="MarkdownV2")
            return

        markup = types.InlineKeyboardMarkup()
        for msg in messages[-5:][::-1]:
            msg_preview = msg['from'][:20] + ("..." if len(msg['from'])>20 else "")
            markup.add(types.InlineKeyboardButton(f"📩 {msg_preview}", callback_data=f"read_{email}_{msg['id']}"))

        bot.send_message(chat_id, f"📬 *Messages for:* `{email}`\n\nTap to read:", reply_markup=markup, parse_mode="MarkdownV2")

    # ----------------- Read Message -----------------
    elif call.data.startswith("read_"):
        parts = call.data.split("_")
        email = parts[1]
        msg_id = parts[2]
        content = fetch_message_content(email, msg_id)
        if not content:
            bot.send_message(chat_id, f"❌ Failed to fetch message content for `{email}`.", parse_mode="MarkdownV2")
            return

        text = f"📧 *From:* {content.get('from','Unknown')}\n"
        text += f"📝 *Subject:* {content.get('subject','No Subject')}\n"
        text += f"📅 *Date:* {content.get('date','Unknown')}\n\n"
        text += f"{content.get('textBody','[No Body]')}\n\n{BRAND}"

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("⬅️ Back to Inbox", callback_data="inbox"))

        bot.send_message(chat_id, text, parse_mode="MarkdownV2", reply_markup=markup)

    # ----------------- Help -----------------
    elif call.data == "help":
        bot.answer_callback_query(call.id)
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("📧 Generate Email", callback_data="gen_email"),
            types.InlineKeyboardButton("👑 Owner", url=OWNER_LINK)
        )
        help_text = (
            "ℹ️ *Help Menu*\n\n"
            "📧 *Generate Email* → Create a new temporary email instantly.\n"
            "📥 *Inbox* → View emails you’ve generated.\n"
            "📩 Tap a message → Read full content inline.\n"
            "📋 *Copy Email* → Copy to clipboard.\n"
            "👑 *Owner* → Contact the creator for support."
        )
        bot.send_message(chat_id, f"{help_text}\n\n{BRAND}", reply_markup=markup, parse_mode="MarkdownV2")

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
# RUN FLASK
# -----------------------------
if __name__ == "__main__":
    print("🚀 Starting Temp Mail Bot Premium...")
    time.sleep(2)
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
    # 1secmail
    try:
        resp = requests.get(
            f"{APIS['1secmail']}?action=readMessage&login={login}&domain={domain}&id={mail_id}",
            timeout=5
        ).json()
        if resp:
            return resp
    except:
        pass

    # mail.tm
    try:
        payload = {"address": email, "password": "TempPass123!"}
        token_resp = requests.post(f"{APIS['mailtm']}/token", json=payload).json()
        token = token_resp.get("token")
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            resp = requests.get(f"{APIS['mailtm']}/messages/{mail_id}", headers=headers).json()
            return resp
    except:
        pass

    # GuerrillaMail
    try:
        r = requests.get(f"{APIS['guerrilla']}?f=fetch_email&email_id={mail_id}", timeout=5).json()
        if r:
            return r
    except:
        pass

    return None

# -----------------------------
# TELEGRAM COMMANDS
# -----------------------------
@bot.message_handler(commands=["start", "email"])
def send_random_email(message):
    email = generate_random_email()
    if not email:
        bot.reply_to(message, "❌ Could not generate email at the moment. Try again.")
        return
    bot.reply_to(message, f"📧 Your random email:\n`{email}`", parse_mode="Markdown")


@bot.message_handler(commands=["inbox"])
def check_inbox(message):
    try:
        parts = message.text.split()
        email = parts[1]
    except IndexError:
        bot.reply_to(message, "Usage: /inbox your_email@example.com")
        return

    inbox = get_inbox(email)
    if not inbox:
        bot.reply_to(message, "📭 No messages found or API unavailable.")
        return

    reply = "📬 Inbox:\n"
    for mail in inbox:
        if isinstance(mail, dict):
            reply += f"- ID: {mail.get('id', '?')}, From: {mail.get('from', '?')}, Subject: {mail.get('subject', '?')}\n"
    bot.reply_to(message, reply)


@bot.message_handler(commands=["read"])
def read_mail(message):
    try:
        _, email, mail_id = message.text.split()
        mail_id = int(mail_id)
    except ValueError:
        bot.reply_to(message, "Usage: /read your_email@example.com mail_id")
        return

    mail = read_email(email, mail_id)
    if not mail:
        bot.reply_to(message, "❌ Could not read the email.")
        return

    reply = f"📧 From: {mail.get('from')}\nSubject: {mail.get('subject')}\n\n{mail.get('textBody') or mail.get('mail_body', '')}"
    bot.reply_to(message, reply)

# -----------------------------
# RUN BOT
# -----------------------------
bot.infinity_polling()
