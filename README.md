Folder structure for Render deployment:

TempMailBot/ ├── main.py  # Full bot code provided earlier ├── requirements.txt └── README.md  # Deployment instructions


---

README.md content:

Temp Mail Bot Premium

🚀 Telegram Temp Mail Bot – Generate disposable emails & read inbox messages instantly.

Features

Generate temporary email addresses.

Read inbox messages inline.

Copy email with one tap.

Inbox previews (Sender + Subject).

Fully production-ready for Render with Gunicorn.


Deployment

1. Upload this project to Render.


2. Install dependencies from requirements.txt.


3. Set Start Command in Render:



gunicorn main:app --bind 0.0.0.0:$PORT

4. Set your environment variables (optional):

BOT_TOKEN → Your Telegram Bot Token

WEBHOOK_URL → Your Render app URL




Usage

/start → Show main menu.

Generate email, check inbox, read messages inline.


Created & Secured by S H Λ S H U


---

Steps to create ZIP:

1. Create folder TempMailBot


2. Save main.py, requirements.txt, and README.md inside.


3. Zip the folder:

On Windows: Right-click folder → Send to → Compressed (zipped) folder

On Linux/Mac: zip -r TempMailBot.zip TempMailBot/




Now TempMailBot.zip is ready to upload to Render.

