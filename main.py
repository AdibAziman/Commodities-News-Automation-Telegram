import requests
import json
import os
import pytz
from datetime import datetime, timedelta
from flask import Flask
import time
import threading
import html

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # Example: "@yourchannel"
DATA_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"
TIMEZONE = pytz.timezone("Asia/Kuala_Lumpur")

app = Flask(__name__)

POSTED_FILE = "posted.json"

def load_posted():
    if not os.path.exists(POSTED_FILE):
        return {"daily": [], "alerts": []}
    with open(POSTED_FILE, "r") as f:
        return json.load(f)

def save_posted(posted):
    with open(POSTED_FILE, "w") as f:
        json.dump(posted, f)

def escape_md(text):
    return html.escape(text)

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    requests.post(url, data=data)

def group_by_impact(events):
    grouped = {"High": [], "Medium": [], "Low": []}
    for event in events:
        impact = event.get("impact", "")
        if "high" in impact.lower():
            grouped["High"].append(event)
        elif "med" in impact.lower():
            grouped["Medium"].append(event)
        elif "low" in impact.lower():
            grouped["Low"].append(event)
    return grouped

def format_event(event):
    time_str = event["time"]
    dt_utc = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%S%z")
    dt_my = dt_utc.astimezone(TIMEZONE)
    clock = dt_my.strftime("%I:%M %p")

    return f"<b>{escape_md(event['title'])}</b>\n" \
           f"🕒 {clock} | {event['currency']}\n" \
           f"📊 Forecast: {event.get('forecast', 'N/A')}\n" \
           f"📉 Previous: {event.get('previous', 'N/A')}\n" \
           f"📈 Actual: {event.get('actual', 'N/A')}"

def fetch_and_post_events():
    while True:
        try:
            now = datetime.now(TIMEZONE)
            posted = load_posted()

            # Fetch data
            res = requests.get(DATA_URL)
            events = res.json()

            # Filter USD events only
            usd_events = [e for e in events if e.get("currency") == "USD"]

            # --- DAILY SUMMARY at 10:00 AM ---
            today_str = now.strftime("%Y-%m-%d")
            if now.hour == 10 and now.minute < 10 and today_str not in posted["daily"]:
                today_events = []
                for e in usd_events:
                    e_time = datetime.strptime(e["time"], "%Y-%m-%dT%H:%M:%S%z").astimezone(TIMEZONE)
                    if e_time.date() == now.date():
                        today_events.append(e)

                grouped = group_by_impact(today_events)

                if grouped["High"]:
                    msg = "💥 <b>High Impact USD Events Today:</b>\n\n"
                    msg += "\n\n".join(format_event(e) for e in grouped["High"])
                    send_telegram_message(msg)

                if grouped["Medium"]:
                    msg = "⚠️ <b>Medium Impact USD Events Today:</b>\n\n"
                    msg += "\n\n".join(format_event(e) for e in grouped["Medium"])
                    send_telegram_message(msg)

                if grouped["Low"]:
                    msg = "🟢 <b>Low Impact USD Events Today:</b>\n\n"
                    msg += "\n\n".join(format_event(e) for e in grouped["Low"])
                    send_telegram_message(msg)

                posted["daily"].append(today_str)
                save_posted(posted)

            # --- ALERTS 15 MINUTES BEFORE EVENT ---
            for event in usd_events:
                event_id = str(event["id"])
                if event_id in posted["alerts"]:
                    continue

                event_time = datetime.strptime(event["time"], "%Y-%m-%dT%H:%M:%S%z").astimezone(TIMEZONE)
                time_diff = (event_time - now).total_seconds() / 60

                if 13 <= time_diff <= 17:  # Roughly 15 mins before
                    # Impact icon
                    impact = event.get("impact", "").lower()
                    if "high" in impact:
                        icon = "💥"
                    elif "med" in impact:
                        icon = "⚠️"
                    elif "low" in impact:
                        icon = "🟢"
                    else:
                        icon = "ℹ️"

                    msg = f"📢 <b>Upcoming USD Event in 15 minutes:</b>\n\n{icon} {format_event(event)}"
                    send_telegram_message(msg)
                    posted["alerts"].append(event_id)
                    save_posted(posted)

        except Exception as e:
            print("Error:", e)

        time.sleep(600)  # Wait 10 minutes before next check

# Flask root route
@app.route("/")
def home():
    return "Forex Bot is running."

# Start background thread
threading.Thread(target=fetch_and_post_events, daemon=True).start()

# Run Flask app
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
