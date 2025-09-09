import os
import telebot
import requests
import random
import string

# -----------------------------
# CONFIG
# -----------------------------
BOT_TOKEN = os.getenv("TELEGRAM_TOKEN") or "8462384824:AAEfU5ENC6VZCTnL7t26yBGDv09UZqt1CdE"
bot = telebot.TeleBot(BOT_TOKEN)

APIS = {
    "1secmail": "https://www.1secmail.com/api/v1/",
    "mailtm": "https://api.mail.tm",
    "guerrilla": "https://api.guerrillamail.com/ajax.php",
    "moakt": "https://api.moakt.com",
    "tempmaildev": "https://api.tempmail.lol"
}

# -----------------------------
# EMAIL FUNCTIONS
# -----------------------------
def generate_random_email():
    """Try multiple APIs until one works"""
    # 1secmail
    try:
        r = requests.get(f"{APIS['1secmail']}?action=genRandomMailbox&count=1", timeout=5).json()
        if r and isinstance(r, list):
            return r[0]
    except:
        pass

    # mail.tm
    try:
        domains = requests.get(f"{APIS['mailtm']}/domains", timeout=5).json().get("hydra:member", [])
        if domains:
            local = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
            return f"{local}@{random.choice(domains)['domain']}"
    except:
        pass

    # GuerrillaMail
    try:
        r = requests.get(f"{APIS['guerrilla']}?f=get_email_address", timeout=5).json()
        if "email_addr" in r:
            return r["email_addr"]
    except:
        pass

    # Moakt
    try:
        r = requests.get(f"{APIS['moakt']}/inbox", timeout=5).json()
        if "email" in r:
            return r["email"]
    except:
        pass

    # TempMail.dev
    try:
        r = requests.get(f"{APIS['tempmaildev']}/generate", timeout=5).json()
        if "address" in r:
            return r["address"]
    except:
        pass

    return None


def get_inbox(email):
    """Fetch inbox messages from available APIs"""
    login, domain = email.split("@")

    # 1secmail
    try:
        resp = requests.get(f"{APIS['1secmail']}?action=getMessages&login={login}&domain={domain}", timeout=5).json()
        if isinstance(resp, list):
            return resp
    except:
        pass

    # mail.tm
    try:
        payload = {"address": email, "password": "TempPass123!"}
        requests.post(f"{APIS['mailtm']}/accounts", json=payload)
        token_resp = requests.post(f"{APIS['mailtm']}/token", json=payload).json()
        token = token_resp.get("token")
        if token:
            headers = {"Authorization": f"Bearer {token}"}
            inbox_resp = requests.get(f"{APIS['mailtm']}/messages", headers=headers).json()
            return inbox_resp.get("hydra:member", [])
    except:
        pass

    # GuerrillaMail (sid_token)
    try:
        r = requests.get(f"{APIS['guerrilla']}?f=get_email_address", timeout=5).json()
        sid = r.get("sid_token")
        if sid:
            inbox = requests.get(f"{APIS['guerrilla']}?f=get_mail_list&sid_token={sid}", timeout=5).json()
            return inbox.get("list", [])
    except:
        pass

    return []


def read_email(email, mail_id):
    """Read a specific email by ID"""
    login, domain = email.split("@")

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
