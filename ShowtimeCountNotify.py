import os
import json
import requests
from datetime import datetime, timedelta

# ------------CONFIGURATION------------

THEATRE_ID = "9406"  # Cinema Banque Scotia Montreal
THEATRE_NAME = "Cinema Banque Scotia Montreal"
SHOWTIMES_API = "https://apis.cineplex.com/prod/cpx/theatrical/api/v1/showtimes"
STATE_FILE = "showtime_state.json"
DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

def get_next_saturday():
    today = datetime.now()
    days_ahead = 5 - today.weekday()  # 5 = Saturday (Monday=0)
    if days_ahead <= 0:
        days_ahead += 7
    next_saturday = today + timedelta(days=days_ahead)
    return next_saturday.strftime("%#m/%#d/%Y") if os.name == 'nt' else next_saturday.strftime("%-m/%-d/%Y")

CHECK_DATE = get_next_saturday()

def send_discord_notification(message):
    try:
        requests.post(DISCORD_WEBHOOK_URL, json={"content": message})
    except Exception as e:
        print(f"Failed to send Discord notification: {e}")

def save_state(count):
    with open(STATE_FILE, "w") as f:
        json.dump({"count": count}, f)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f).get("count", 0)
        except Exception:
            return 0
    return 0

def get_showtime_count():
    if CHECK_DATE:
        date = CHECK_DATE
    elif os.name == 'nt':
        date = datetime.now().strftime("%#m/%#d/%Y")
    else:
        date = datetime.now().strftime("%-m/%-d/%Y")
    print(f"Checking showtimes for {THEATRE_NAME} (ID: {THEATRE_ID}) on {date}")
    try:
        resp = requests.get(SHOWTIMES_API, params={
            "language": "en",
            "locationId": THEATRE_ID,
            "date": date,
        }, headers={
             ### Use a realistic User-Agent to avoid potential blocking
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",   
            "Accept": "application/json",
            "Referer": "https://www.cineplex.com/",
            "Origin": "https://www.cineplex.com",
            "Ocp-Apim-Subscription-Key": "dcdac5601d864addbc2675a2e96cb1f8",
        }, timeout=15)
        # Handle different response scenarios
        if resp.status_code == 200:
            data = resp.json() if resp.text else {}
            total_showings = 0
            if isinstance(data, list):
                for theatre_entry in data:
                    for date_entry in theatre_entry.get("dates", []):
                        for movie in date_entry.get("movies", []):
                            for exp in movie.get("experiences", []):
                                total_showings += len(exp.get("sessions", []))
                print(f"Total showings at {THEATRE_NAME}: {total_showings}")
                return total_showings
            else:
                print("Unexpected response format or no data.")
        # Some theatres return 204 No Content when there are no showtimes for the day, which is a valid response indicating zero showings. We can treat this as zero showings rather than an error.
        elif resp.status_code == 204:
            print("No showtimes data for this theatre today (204 No Content)")

        else:
            print(f"API error: {resp.status_code} - {resp.text[:200]}") # Print first 200 chars of response for debugging
    except Exception as e:
        print(f"Error checking showtimes: {e}")
    return None

def main():
    # Load previous count, get current count, compare and notify if changed
    previous_count = load_state()
    current_count = get_showtime_count()
    if current_count is not None:
        if current_count != previous_count:
            message = (
                f"🎬 Showtimes for **{THEATRE_NAME}** have changed!\n"
                f"Previous: {previous_count}\nCurrent: {current_count}"
            )
            send_discord_notification(message)
            print(f"Notification sent. ({previous_count} → {current_count})")
            save_state(current_count)
        else:
            print(f"No change in showtime count. ({current_count})")
    else:
        print("Could not retrieve showtime count.")

if __name__ == "__main__":
    main()
