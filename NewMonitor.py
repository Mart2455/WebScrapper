import os
import json
import requests
from datetime import date, timedelta, datetime


# ------------CONFIGURATION------------

DISCORD_WEBHOOK_URL = os.environ.get("DISCORD_WEBHOOK")

# Cineplex API endpoint for showtimes
SHOWTIMES_API = "https://apis.cineplex.com/prod/cpx/theatrical/api/v1/showtimes"

# Theatre IDs to monitor (Cineplex internal IDs)
# * Find more IDs by inspecting network requests on cineplex.com
TARGET_THEATRES = {
    "7408": "Vaughan, ON",
    "7420": "Mississauga, ON",  # Cineplex Cinemas Mississauga Square One
    "9406": "Montreal, QC"
}


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
    # Right now we only have 1 date, Idea is to loop through every saturday throughout the year and check if the movie is available, if it is then we send a notification and save the number of showtimes, if the number of showtimes changes we send another notification. This way we can monitor the movie for the whole year and not just on release date.
    
    today = datetime.now()

    # Find the next Saturday from today (or today if it's already Saturday)
    days_until_saturday = (5 - today.weekday()) % 7
    first_saturday = today + timedelta(days=days_until_saturday)

    # Generate all Saturdays from now until 6 months out
    six_months_out = today + timedelta(weeks=26)
    saturdays = []
    current = first_saturday
    while current <= six_months_out:
        saturdays.append(current)
        current += timedelta(weeks=1)
    results = []

    for theatre_id, TheatreName in TARGET_THEATRES.items():
        print(f"Checking {TheatreName} (ID: {theatre_id})...")
        try:
            # Loop through all Saturdays in 2026 to check for showtimes on each date
            for saturday in saturdays:  # Check every Saturday for a year
                date = saturday.strftime("%#m/%#d/%Y") if os.name == 'nt' else saturday.strftime("%-m/%-d/%Y")
                resp = requests.get(SHOWTIMES_API, params=
                {
                    "language": "en",   
                    "locationId": theatre_id,
                    "date": date,
                }, 
                headers=
                {
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

                                    """ TODO: We can remove the movie name check and just count the total showtimes for all movies, 
                                     * this way we can monitor all movies for the whole year and not just one movie. 
                                     We can also add a counter for total movies available each saturday and 
                                     if that changes we send a notification. This way we can monitor the movie for the whole year 
                                     and not just on release date. """

                                    TotalSessions = sum(    # Count total sessions across all experiences for this movie
                                            len(exp.get("sessions", []))
                                            for exp in movie.get("experiences", [])
                                    )
                                        # Debug print to confirm movie found and session count
                                    if TotalSessions >= 1:
                                            print(f"  ✓ Found at date:  '{date}' — {TotalSessions} showtime(s) available")
                                            results.append((TheatreName, TotalSessions))
                                    else:
                                        print(f"Total Sessions for '{date}' at '{TheatreName}': {TotalSessions}")
                                    break
                                else:
                                    continue
                                break
            
                    elif isinstance(data, dict):
                        # Dump keys for debugging
                        print(f"  Response keys: {list(data.keys())[:10]}")
                        # Check if it's empty or has no relevant data
                        if not data:
                            print(f"  Empty response")
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
                        f"🎬 Tickets are now available at "
                        f"**{location}**! ({count} showtime(s))\n"
                    )
                SendDiscordNotification(message)
                print(f"Sent notification for {location} ({previous_count} → {count})")
                state[location] = count
    SaveState(state)
    print("Done.")

if __name__ == "__main__":
    main()