import requests
import time
import json
import os
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
TELEGRAM_API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
CALENDAR_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"

# Emoji for impact
impact_emojis = {
    "High": "🔴",
    "Medium": "🟡",
    "Low": "⚪️"
}

# Load posted event IDs
POSTED_FILE = "posted.json"
if os.path.exists(POSTED_FILE):
    with open(POSTED_FILE, "r") as f:
        posted_ids = set(json.load(f))
else:
    posted_ids = set()

def fetch_events():
    try:
        response = requests.get(CALENDAR_URL)
        return response.json()
    except Exception as e:
        print("Error fetching calendar:", e)
        return []

def format_event(event):
    timestamp = event["timestamp"]
    dt = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M UTC")
    emoji = impact_emojis.get(event["impact"], "⚪️")

    message = (
        f"{emoji} <b>{event['title']}</b>\n"
        f"🕒 <b>Time:</b> {dt}\n"
        f"💱 <b>Currency:</b> {event['currency']}\n"
        f"📊 <b>Impact:</b> {event['impact']}\n"
        f"📈 <b>Actual:</b> {event.get('actual', 'N/A')}\n"
        f"📉 <b>Forecast:</b> {event.get('forecast', 'N/A')}\n"
        f"📊 <b>Previous:</b> {event.get('previous', 'N/A')}"
    )
    return message

def send_to_telegram(message):
    payload = {
        "chat_id": CHANNEL_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        r = requests.post(TELEGRAM_API_URL, data=payload)
        return r.status_code == 200
    except Exception as e:
        print("Error sending message:", e)
        return False

def save_posted():
    with open(POSTED_FILE, "w") as f:
        json.dump(list(posted_ids), f)

def main():
    print("Bot started...")
    while True:
        events = fetch_events()
        now = time.time()

        for event in events:
            event_id = str(event["id"])
            event_time = event["timestamp"]

            # Skip old events or already posted
            if event_time < now or event_id in posted_ids:
                continue

            message = format_event(event)
            sent = send_to_telegram(message)

            if sent:
                print(f"✅ Sent: {event['title']}")
                posted_ids.add(event_id)
                save_posted()
            else:
                print(f"❌ Failed to send: {event['title']}")

        time.sleep(600)  # Check every 10 minutes

if __name__ == "__main__":
    main()
