import os
import json
import requests
from datetime import datetime


# ------------CONFIGURATION------------

MOVIE_URL = "https://www.cineplex.com/movie/the-odyssey?openTM=true&theatreId=7408"

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

# Cineplex API endpoint for showtimes
SHOWTIMES_API = "https://apis.cineplex.com/prod/cpx/theatrical/api/v1/showtimes"

# Theatre IDs to monitor (Cineplex internal IDs)
# 7408 = Cineplex Cinemas Vaughan
# Find more IDs by inspecting network requests on cineplex.com
TARGET_THEATRES = {
    "7408": "Vaughan, ON",
    "7420": "Mississauga, ON",  # Cineplex Cinemas Mississauga Square One
}

MOVIE_NAME = "The Odyssey"

# Set a specific date to check (M/D/YYYY), or None to use today's date
CHECK_DATE = "7/18/2026"

STATE_FILE = "states.json"

def SendDiscordNotification(message):
    requests.post(DISCORD_WEBHOOK_URL, json={"content": message})


def SaveState(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def LoadState():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, ValueError):
            return {}
    return {}


def CheckShowtimes():
    if CHECK_DATE:
        date = CHECK_DATE
    elif os.name == 'nt':  # Windows
        date = datetime.now().strftime("%#m/%#d/%Y")
    else:  # Linux/macOS (GitHub Actions)
        date = datetime.now().strftime("%-m/%-d/%Y")
    print(f"Searching for date: {date}")    # Debug print to confirm the date being used
    results = []

    for theatre_id, TheatreName in TARGET_THEATRES.items():
        print(f"Checking {TheatreName} (ID: {theatre_id})...")
        try:
            resp = requests.get(SHOWTIMES_API, params={
                "language": "en",   
                "locationId": theatre_id,
                "date": date,
            }, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",    # Use a realistic User-Agent to avoid potential blocking
                "Accept": "application/json",
                "Referer": "https://www.cineplex.com/", # Some APIs require a Referer header matching the site
                "Origin": "https://www.cineplex.com",
                "Ocp-Apim-Subscription-Key": "dcdac5601d864addbc2675a2e96cb1f8",
            }, timeout=15)

            if resp.status_code == 200:
                data = resp.json() if resp.text else {}


                # Look for our movie in the response
                # API structure: [ { theatre, theatreId, dates: [ { movies: [ { name, experiences: [ { sessions } ] } ] } ] } ]
                if isinstance(data, list):
                    for theatre_entry in data:
                        for date_entry in theatre_entry.get("dates", []):
                            for movie in date_entry.get("movies", []):
                                MovieTitle = movie.get("name", "")
                                if MOVIE_NAME.lower() in MovieTitle.lower():

                                    TotalSessions = sum(    # Count total sessions across all experiences for this movie
                                        len(exp.get("sessions", []))
                                        for exp in movie.get("experiences", [])
                                    )
                                    # Debug print to confirm movie found and session count
                                    if TotalSessions >= 1:
                                        print(f"  ✓ Found '{MovieTitle}' — {TotalSessions} showtime(s) available")
                                        results.append((TheatreName, TotalSessions))
                                    else:
                                        print(f"  ✗ Found '{MovieTitle}' but 0 showtimes")
                                    break
                            else:
                                continue
                            break
                    # If we went through the data and didn't find the movie, print a message
                    if not any(name == TheatreName for name, _ in results):
                        total_movies = sum(
                            len(m) for t in data for d in t.get("dates", []) for m in [d.get("movies", [])]
                        )
                        print(f"  '{MOVIE_NAME}' not found in {total_movies} movie(s)")
                elif isinstance(data, dict):
                    # Dump keys for debugging
                    print(f"  Response keys: {list(data.keys())[:10]}")
                    # Check if it's empty or has no relevant data
                    if not data:
                        print(f"  Empty response")
                else:
                    print(f"  Unexpected response type: {type(data)}")
            elif resp.status_code == 204:
                print(f"  No showtimes data for this theatre today (204 No Content)")
            else:
                print(f"  API error: {resp.status_code} - {resp.text[:200]}")
        except Exception as e:
            print(f"  Error checking {TheatreName}: {e}")

    return results

def main():
    print("Starting Cineplex monitor...")
    state = LoadState()

    results = CheckShowtimes()

    if results:
        for location, count in results:
            previous_count = state.get(location, 0)
            if count > previous_count:
                new_showtimes = count - previous_count
                if previous_count == 0:
                    message = (
                        f"🎬 **{MOVIE_NAME}** tickets are now available at "
                        f"**{location}**! ({count} showtime(s))\n"
                        f"Book here: {MOVIE_URL}"
                    )
                else:
                    message = (
                        f"🎬 **{new_showtimes} NEW showtime(s)** for **{MOVIE_NAME}** at "
                        f"**{location}**! (now {count} total)\n"
                        f"Book here: {MOVIE_URL}"
                    )
                SendDiscordNotification(message)
                print(f"Sent notification for {location} ({previous_count} → {count})")
                state[location] = count
            else:
                print(f"No new showtimes for {location} ({count} showtime(s), same as before).")
    else:
        print("No target theatres with showtimes found yet.")
    SaveState(state)
    print("Done.")

if __name__ == "__main__":
    main()
