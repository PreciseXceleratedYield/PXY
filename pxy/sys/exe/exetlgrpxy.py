# exetlgrpxy.py
import requests

# ---------------- TELEGRAM CONFIG ----------------
BOT_TOKEN = "7314363024:AAF-tihNsblqbhQqSaCzdRcjd-ySshpo7BY"
USER_IDS = ["-4583314804"]

def send_telegram_message(message: str):
    """Send a Telegram message to all user IDs."""
    try:
        for uid in USER_IDS:
            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            payload = {'chat_id': uid, 'text': message}
            response = requests.post(url, data=payload)
            if response.status_code != 200:
                print(f"⚠ Telegram failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Telegram error: {e}")
