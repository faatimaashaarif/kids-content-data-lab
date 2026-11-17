"""
WHAT:  Fetches the latest videos for each channel and saves their details
       (title, description, tags, made-for-kids flag) in stats.db.
IN:    the same channel list and API key as fetch_stats.py
OUT:   up to 10 rows per channel in a new "videos" table.
       Running it again updates the same videos instead of adding copies.
PLAN:
  1. For each channel, find its "uploads" playlist (every channel has one,
     holding all its public videos, newest first).
  2. Get the IDs of the newest 10 videos in that playlist.
  3. Ask for the details of those 10 videos in ONE call.
  4. Save each video, replacing any older copy of the same video.
SPEED: 3 API calls per channel (12 units of the free 10,000 a day).
"""

import sqlite3
from datetime import datetime, timezone

import requests

# Reuse what fetch_stats.py already has, instead of copying it.
# This works because fetch_stats.py only runs main() when run directly
# (that's what its  if __name__ == "__main__":  line is for).
from fetch_stats import get_api_key, CHANNEL_HANDLES, DB_FILE

API_BASE = "https://www.googleapis.com/youtube/v3"   # the start of every YouTube API address
VIDEOS_PER_CHANNEL = 10


def create_table(conn):
    """Make the videos table the first time; does nothing if it already exists."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            video_id      TEXT PRIMARY KEY,  -- YouTube's ID; PRIMARY KEY means no two rows can share it
            handle        TEXT NOT NULL,     -- which channel, e.g. @Blippi
            title         TEXT,
            description   TEXT,
            tag_count     INTEGER,           -- how many tags the video has
            made_for_kids INTEGER,           -- 1 = yes, 0 = no, empty = YouTube didn't say
            published_at  TEXT,              -- when the video went live
            fetched_at    TEXT NOT NULL      -- when we last checked it
        )
    """)


def call_api(endpoint, params, api_key):
    """Ask one YouTube API endpoint a question and return the list of items it sends back.
    One shared helper means the request code is written once, not three times."""
    params["key"] = api_key                                  # every call needs the key
    response = requests.get(f"{API_BASE}/{endpoint}", params=params, timeout=10)
    response.raise_for_status()                              # stop with an error if YouTube said no
    return response.json().get("items", [])                 # empty list if nothing was found


def get_uploads_playlist(handle, api_key):
    """Step 1: find the channel's uploads playlist ID, or None if the channel isn't found."""
    items = call_api("channels", {"part": "contentDetails", "forHandle": handle}, api_key)
    if not items:
        return None
    return items[0]["contentDetails"]["relatedPlaylists"]["uploads"]


def get_latest_video_ids(playlist_id, api_key):
    """Step 2: get the IDs of the newest videos in the playlist."""
    items = call_api(
        "playlistItems",
        {"part": "contentDetails", "playlistId": playlist_id, "maxResults": VIDEOS_PER_CHANNEL},
        api_key,
    )
    # Pull just the video ID out of each item, e.g. ["abc123", "def456", ...]
    return [item["contentDetails"]["videoId"] for item in items]


def get_video_details(video_ids, api_key):
    """Step 3: get details for all the videos in ONE call (IDs joined with commas)."""
    return call_api(
        "videos",
        {"part": "snippet,status", "id": ",".join(video_ids)},   # snippet = title etc., status = made for kids
        api_key,
    )


def save_video(conn, handle, video, fetched_at):
    """Step 4: save one video. INSERT OR REPLACE = add it, or overwrite the old copy
    if this video_id is already saved. So re-running never creates duplicates."""
    snippet = video["snippet"]
    made_for_kids = video.get("status", {}).get("madeForKids")   # True, False, or None if missing
    conn.execute(
        """
        INSERT OR REPLACE INTO videos
            (video_id, handle, title, description, tag_count, made_for_kids, published_at, fetched_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            video["id"],
            handle,
            snippet.get("title"),
            snippet.get("description", ""),          # "" if the video has no description
            len(snippet.get("tags", [])),            # no tags -> empty list -> 0
            None if made_for_kids is None else int(made_for_kids),   # True -> 1, False -> 0
            snippet.get("publishedAt"),
            fetched_at,
        ),
    )


def main():
    api_key = get_api_key()
    fetched_at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    conn = sqlite3.connect(DB_FILE)
    create_table(conn)

    total = 0
    for handle in CHANNEL_HANDLES:
        playlist_id = get_uploads_playlist(handle, api_key)                 # Step 1
        if playlist_id is None:
            print(f"  Not found: {handle}")
            continue

        video_ids = get_latest_video_ids(playlist_id, api_key)             # Step 2
        if not video_ids:
            print(f"  No videos found for {handle}")
            continue

        videos = get_video_details(video_ids, api_key)                     # Step 3
        for video in videos:
            save_video(conn, handle, video, fetched_at)                    # Step 4
        total += len(videos)
        print(f"  {handle}: saved {len(videos)} videos")

    conn.commit()
    conn.close()
    print(f"Done: saved {total} videos at {fetched_at}")


if __name__ == "__main__":
    main()

# CHECKED: tested with fake API responses: 10 videos per channel saved,
#          running twice still gives 10 per channel (no duplicates),
#          a video with no tags or description saves as tag_count 0 and "".
# DECISION: INSERT OR REPLACE, because we care about each video's CURRENT
#           details, not a history of them (unlike channel stats).
