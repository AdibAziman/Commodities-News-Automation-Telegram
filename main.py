from flask import Flask
from threading import Thread
import requests
import json
import os
import time
from datetime import datetime

app = Flask(__name__)

# Flask route (dummy) to keep the web service running
@app.route('/')
def index():
    return "Bot is running"

# Function to send message to Telegram channel
def send_to_telegram(message):
    bot_token = os.getenv("BOT_TOKEN")  # Get bot token from environment
    channel_id = os.getenv("CHANNEL_ID")  # Get channel ID from environment
    url = f'https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={channel_id}&text={message}'
    response = requests.get(url)
    return response.json()

# Function to fetch economic calendar events (filtered by high/medium/low impact)
def fetch_and_post_events():
    url = "https://www.forexfactory.com/ffcal_week_this.json"  # Forex Factory calendar JSON
    response = requests.get(url)
    if response.status_code == 200:
        events = response.json()

        for event in events:
            if event.get("currency") != "USD":
                continue  # Only process USD events

            event_id = event["id"]
            title = event["title"]
            impact = event["impact"]
            time_str = event["time"]
            forecast = event.get("forecast", "N/A")
            previous = event.get("previous", "N/A")
            actual = event.get("actual", "N/A")

            # Convert time to a more readable format
            event_time = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")  # Example: '2025-04-17 14:00:00'
            formatted_time = event_time.strftime("%Y-%m-%d %H:%M:%S")  # Change the format as needed

            # Add emoji based on the event's impact level
            if impact == 'High':
                emoji = "🔴"  # Red circle for high impact
            elif impact == 'Medium':
                emoji = "🟡"  # Yellow circle for medium impact
            elif impact == 'Low':
                emoji = "🟢"  # Green circle for low impact
            else:
                emoji = "⚪"  # White circle if no impact is specified

            # Format the message with event details, time, impact, forecast, previous, and actual data
            message = (
                f"Event: {title}\n"
                f"Impact: {emoji} {impact}\n"
                f"Time: {formatted_time}\n"
                f"Forecast: {forecast}\n"
                f"Previous: {previous}\n"
                f"Actual: {actual}"
            )
            send_to_telegram(message)

            # Store event ID in a JSON file to avoid sending it again
            store_posted_event(event_id)

def store_posted_event(event_id):
    # Load existing posted events
    if os.path.exists("posted.json"):
        with open("posted.json", "r") as file:
            posted_events = json.load(file)
    else:
        posted_events = []

    # Check if the event ID is already posted
    if event_id not in posted_events:
        posted_events.append(event_id)

        # Save back to posted.json
        with open("posted.json", "w") as file:
            json.dump(posted_events, file)

# Function to run the Flask server in a separate thread
def run():
    app.run(host='0.0.0.0', port=8080)

# Main function to keep the bot running
if __name__ == "__main__":
    # Start the Flask web server in a new thread
    t = Thread(target=run)
    t.start()

    # Run bot logic to fetch and post events every 10 minutes
    while True:
        fetch_and_post_events()
        time.sleep(600)  # Sleep for 10 minutes before running again
