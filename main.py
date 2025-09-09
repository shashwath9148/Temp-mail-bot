import telebot
import requests
import re
import threading
import time
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")  # Read from environment (Railway/Heroku)
bot = telebot.TeleBot(BOT_TOKEN)

# User data storage: email + seen mail IDs + read mail IDs
user_data = {}

API_URL = "https://www.1secmail.com/api/v1/"

# --- Helpers ---
def generate_mail():
    url = f"{API_URL}?action=genRandomMailbox&count=1"
    return requests.get(url).json()[0]

def get_inbox(email):
    login, domain = email.split("@")
    url = f"{API_URL}?action=getMessages&login={login}&domain={domain}"
    return requests.get(url).json()

def read_mail(email, mail_id):
    login, domain = email.split("@")
    url = f"{API_URL}?action=readMessage&login={login}&domain={domain}&id={mail_id}"
    return requests.get(url).json()

def extract_otp(text):
    match = re.findall(r"\b\d{4,8}\b", text)  # 4–8 digit codes
    return match[0] if match else None

def extract_links(text):
    return re.findall(r'(https?://[^\s]+)', text)

def branding_footer():
    return "\n\n— SSYT_Elite7 | Created by Shashu ❤️"

# --- Bot Commands ---
@bot.message_handler(commands=['start'])
def start(msg):
    bot.send_message(
        msg.chat.id,
        "👋 Welcome to TEMP MAIL BOT!\n"
        "Protect your privacy & stop spam 🚀\n\n"
        "🔹 Generate Temp Mail → /getmail\n"
        "🔹 Check Inbox → /inbox\n"
        "🔹 Stats → /stats\n"
        "🔹 About → /about"
        + branding_footer()
    )

@bot.message_handler(commands=['about'])
def about(msg):
    bot.send_message(
        msg.chat.id,
        "📩 This bot gives you instant disposable emails!\n"
        "✅ Perfect for OTPs & signups\n"
        "✅ Auto-expires after some time\n"
        "✅ Secure, fast & private"
        + branding_footer()
    )

@bot.message_handler(commands=['getmail'])
def get_mail(msg):
    email = generate_mail()
    user_data[msg.chat.id] = {"email": email, "seen": set(), "read": set()}
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("📋 Copy Email", switch_inline_query=email),
        InlineKeyboardButton("📥 Check Inbox", callback_data="inbox"),
        InlineKeyboardButton("🔄 New Mail", callback_data="newmail")
    )
    bot.send_message(
        msg.chat.id,
        f"✅ Your Temp Mail:\n📧 `{email}`\n\n⚡ Auto-expires in 10 minutes."
        + branding_footer(),
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(commands=['inbox'])
def inbox(msg):
    if msg.chat.id not in user_data:
        bot.send_message(msg.chat.id, "⚠️ Generate a mailbox first using /getmail")
        return
    
    email = user_data[msg.chat.id]["email"]
    mails = get_inbox(email)
    
    if not mails:
        bot.send_message(msg.chat.id, "📭 Inbox is empty." + branding_footer())
        return

    for mail in mails:
        markup = InlineKeyboardMarkup()
        markup.add(
            InlineKeyboardButton("📜 Read Mail", callback_data=f"read_{mail['id']}"),
            InlineKeyboardButton("🗑 Delete", callback_data=f"delete_{mail['id']}")
        )
        bot.send_message(
            msg.chat.id,
            f"✉️ New Mail!\nFrom: {mail['from']}\nSubject: {mail['subject']}\nID: {mail['id']}"
            + branding_footer(),
            reply_markup=markup
        )

@bot.message_handler(commands=['stats'])
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