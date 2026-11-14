"""
WHAT:  Fetches public YouTube statistics for a few children's channels
       and saves them in a small local database.
IN:    - a list of channel handles (CHANNEL_HANDLES below)
       - a YouTube API key, read from an environment variable
OUT:   one new row per channel in stats.db every time you run it.
       Run it once a day and you build up a history you can compare over time.
PLAN:
  1. Read the API key from the environment (keys never go in the code).
  2. Open the database and make sure the table exists.
  3. For each channel handle, ask the YouTube API for its statistics.
  4. Save one row per channel, stamped with the time we fetched it.
  5. Print a short summary so we can see it worked.
SPEED: one API call per channel, so it grows with the number of channels.
       Each call costs 1 unit of YouTube's free 10,000 units a day.
"""

import os                                   # lets us read environment variables
import sqlite3                              # Python's built-in database library
from datetime import datetime, timezone     # for stamping each row with the time

import requests                             # sends web requests (installed with pip)


# ---- Settings you can change ----

# Channel handles: the @name in a channel's YouTube web address.
# Check each one on YouTube before running, and add or remove as you like.
CHANNEL_HANDLES = ["@CoComelon", "@Blippi", "@LittleAngel", "@Morphle"]

DB_FILE = "stats.db"                        # the database file this script creates
API_URL = "https://www.googleapis.com/youtube/v3/channels"   # YouTube's "channels" endpoint


def get_api_key():
    """Step 1: read the API key from the environment, or stop with a clear message."""
    api_key = os.environ.get("YOUTUBE_API_KEY")          # None if it isn't set
    if not api_key:
        raise SystemExit("No API key found. Run: export YOUTUBE_API_KEY='your-key'")
    return api_key


def create_table(conn):
    """Step 2: create the table the first time; does nothing if it already exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS channel_stats (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,  -- row number, added for us
            fetched_at       TEXT    NOT NULL,                   -- when we asked (UTC time)
            handle           TEXT    NOT NULL,                   -- e.g. @Blippi
            channel_id       TEXT,                               -- YouTube's own ID for the channel
            channel_name     TEXT,                               -- the channel's display name
            view_count       INTEGER,                            -- total views, all time
            subscriber_count INTEGER,                            -- can be hidden, so may be empty
            video_count      INTEGER                             -- number of public videos
        )
    """)


def to_number(value):
    """YouTube sends numbers as text ("123"). Turn them into whole numbers, or None if missing."""
    return int(value) if value is not None else None


def fetch_channel(handle, api_key):
    """Step 3: ask YouTube for one channel's details. Returns a dictionary, or None if not found."""
    response = requests.get(
        API_URL,
        params={
            "part": "snippet,statistics",   # snippet = name; statistics = the counts
            "forHandle": handle,            # look the channel up by its @handle
            "key": api_key,                 # proves who is asking
        },
        timeout=10,                         # give up after 10 seconds instead of hanging
    )
    response.raise_for_status()             # stop with an error if YouTube said no (bad key, etc.)

    items = response.json().get("items", [])    # the channels YouTube found (usually 0 or 1)
    if not items:
        print(f"  Not found: {handle} (check the handle on YouTube)")
        return None

    channel = items[0]                      # we asked for one handle, so take the first match
    stats = channel["statistics"]           # the part with the counts
    return {
        "handle": handle,
        "channel_id": channel["id"],
        "channel_name": channel["snippet"]["title"],
        "view_count": to_number(stats.get("viewCount")),
        # .get() returns None instead of crashing if a channel hides its subscriber count
        "subscriber_count": to_number(stats.get("subscriberCount")),
        "video_count": to_number(stats.get("videoCount")),
    }


def save_row(conn, row, fetched_at):
    """Step 4: add one channel's numbers to the table."""
    conn.execute(
        """
        INSERT INTO channel_stats
            (fetched_at, handle, channel_id, channel_name, view_count, subscriber_count, video_count)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        # The ? marks are filled in safely from this list, in order.
        # This is safer than gluing text into SQL yourself (it prevents "SQL injection").
        (fetched_at, row["handle"], row["channel_id"], row["channel_name"],
         row["view_count"], row["subscriber_count"], row["video_count"]),
    )


def main():
    api_key = get_api_key()                                  # Step 1
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")  # one time for this whole run

    conn = sqlite3.connect(DB_FILE)                          # opens the file, or creates it
    create_table(conn)                                       # Step 2

    saved = 0                                                # counts how many rows we saved
    for handle in CHANNEL_HANDLES:                           # Step 3: one channel at a time
        row = fetch_channel(handle, api_key)
        if row is None:
            continue                                         # skip this one and carry on
        save_row(conn, row, fetched_at)                      # Step 4
        saved += 1
        print(f"  Saved {row['channel_name']}: {row['view_count']:,} views")

    conn.commit()                                            # actually write the changes to the file
    conn.close()
    print(f"Done: saved {saved} of {len(CHANNEL_HANDLES)} channels at {fetched_at}")   # Step 5


# Only run main() when this file is run directly (not when another file imports it)
if __name__ == "__main__":
    main()

# CHECKED: run twice; stats.db gets 4 rows per run with the same fetched_at time.
# EDGE CASES: wrong handle -> "Not found" and the others still save.
#             missing key -> clear message instead of a confusing error.
# DECISION: one simple file and plain requests, so every line can be explained.
