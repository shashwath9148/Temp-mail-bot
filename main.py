import telebot
import requests
import random
import string

# -----------------------------
# CONFIG
# -----------------------------
BOT_TOKEN = "YOUR_BOT_TOKEN"  # Replace with your Telegram bot token
bot = telebot.TeleBot(BOT_TOKEN)

API_1SECMAIL = "https://www.1secmail.com/api/v1/"
API_MAILTM = "https://api.mail.tm"

# -----------------------------
# EMAIL FUNCTIONS
# -----------------------------
def generate_random_email():
    """Generate a random email with 1secmail fallback to mail.tm"""
    # 1secmail
    try:
        resp = requests.get(f"{API_1SECMAIL}?action=genRandomMailbox&count=1", timeout=5).json()
        if resp and isinstance(resp, list):
            return resp[0]
    except Exception:
        pass

    # mail.tm fallback
    try:
        domains = requests.get(f"{API_MAILTM}/domains").json().get("hydra:member", [])
        domain = random.choice(domains)["domain"]
        local = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        return f"{local}@{domain}"
    except Exception:
        return None

def get_inbox(email):
    """Fetch inbox messages for an email"""
    login, domain = email.split("@")

    # 1secmail
    try:
        resp = requests.get(f"{API_1SECMAIL}?action=getMessages&login={login}&domain={domain}", timeout=5).json()
        if isinstance(resp, list):
            return resp
    except Exception:
        pass

    # mail.tm fallback
    try:
        payload = {"address": email, "password": "TempPass123!"}
        requests.post(f"{API_MAILTM}/accounts", json=payload)
        token_resp = requests.post(f"{API_MAILTM}/token", json=payload).json()
        token = token_resp.get("token")
        if not token:
            return []
        headers = {"Authorization": f"Bearer {token}"}
        inbox_resp = requests.get(f"{API_MAILTM}/messages", headers=headers).json()
        return inbox_resp.get("hydra:member", [])
    except Exception:
        return []

def read_email(email, mail_id):
    """Read a specific email by ID"""
    login, domain = email.split("@")

    # 1secmail
    try:
        resp = requests.get(f"{API_1SECMAIL}?action=readMessage&login={login}&domain={domain}&id={mail_id}", timeout=5).json()
        if resp:
            return resp
    except Exception:
        pass

    # mail.tm fallback
    try:
        payload = {"address": email, "password": "TempPass123!"}
        token_resp = requests.post(f"{API_MAILTM}/token", json=payload).json()
        token = token_resp.get("token")
        if not token:
            return None
        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(f"{API_MAILTM}/messages/{mail_id}", headers=headers).json()
        return resp
    except Exception:
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
        reply += f"- ID: {mail['id']}, From: {mail['from']}, Subject: {mail['subject']}\n"
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

    reply = f"📧 From: {mail.get('from')}\nSubject: {mail.get('subject')}\n\n{mail.get('textBody')}"
    bot.reply_to(message, reply)

# -----------------------------
# RUN BOT
# -----------------------------
bot.infinity_polling()@bot.message_handler(commands=['stats'])
def stats(msg):
    if msg.chat.id not in user_data:
        bot.send_message(msg.chat.id, "⚠️ Generate a mailbox first using /getmail")
        return
    
    data = user_data[msg.chat.id]
    email = data["email"]
    mails = get_inbox(email)

    total = len(mails)
    unread = sum(1 for mail in mails if mail["id"] not in data["read"])
    
    bot.send_message(
        msg.chat.id,
        f"📊 Stats for `{email}`\n\n"
        f"📩 Total Mails: {total}\n"
        f"📬 Unread: {unread}"
        + branding_footer(),
        parse_mode="Markdown"
    )

# --- Callbacks ---
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    chat_id = call.message.chat.id
    
    if call.data == "inbox":
        inbox(call.message)
    
    elif call.data == "newmail":
        get_mail(call.message)

    elif call.data.startswith("read_"):
        mail_id = int(call.data.split("_")[1])
        email = user_data[chat_id]["email"]
        mail = read_mail(email, mail_id)
        
        # mark as read
        user_data[chat_id]["read"].add(mail_id)
        
        text = f"📜 Mail #{mail['id']}\nFrom: {mail['from']}\nSubject: {mail['subject']}\n\n{mail['textBody'] or 'No body'}"
        
        otp = extract_otp(mail['textBody'] or "")
        if otp:
            text += f"\n\n🔑 OTP Detected: *{otp}*"
        
        links = extract_links(mail['textBody'] or "")
        markup = InlineKeyboardMarkup()
        for link in links:
            markup.add(InlineKeyboardButton("🌐 Open Link", url=link))
        markup.add(InlineKeyboardButton("📂 Download", url=f"https://www.1secmail.com/mailbox/?id={mail['id']}"))
        
        bot.send_message(chat_id, text + branding_footer(), reply_markup=markup, parse_mode="Markdown")

    elif call.data.startswith("delete_"):
        bot.send_message(chat_id, "🗑 Mail deleted (simulation)." + branding_footer())

# --- Auto Notification Worker ---
def check_new_mails():
    while True:
        for chat_id, data in list(user_data.items()):
            email = data["email"]
            seen = data["seen"]
            try:
                mails = get_inbox(email)
                for mail in mails:
                    if mail['id'] not in seen:
                        seen.add(mail['id'])
                        markup = InlineKeyboardMarkup()
                        markup.add(
                            InlineKeyboardButton("📜 Read Mail", callback_data=f"read_{mail['id']}")
                        )
                        bot.send_message(
                            chat_id,
                            f"🚨 New Mail Received!\nFrom: {mail['from']}\nSubject: {mail['subject']}"
                            + branding_footer(),
                            reply_markup=markup
                        )
            except Exception as e:
                print("Error checking mail:", e)
        time.sleep(10)  # check every 10s

# Run mail checker in background
threading.Thread(target=check_new_mails, daemon=True).start()

# --- Run Bot ---
print("🤖 Temp Mail Bot is running with auto notifications + stats...")
bot.polling(none_stop=True)
