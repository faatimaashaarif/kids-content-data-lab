"""
WHAT:  Shows what is in stats.db, and how much each channel's views
       went up since the previous run.
IN:    stats.db (made by fetch_stats.py)
OUT:   a small table printed in the terminal
PLAN:
  1. Open the database.
  2. Run one SQL query that uses a window function (LAG) to find the change.
  3. Print each row neatly.
SPEED: reads every row once, which is tiny for this project.
"""

import sqlite3

DB_FILE = "stats.db"

# LAG(view_count) looks at the previous row for the SAME channel
# (PARTITION BY handle), in time order (ORDER BY fetched_at).
# Subtracting gives "views gained since last run".
# The first run for a channel has no previous row, so the change is empty (None).
QUERY = """
SELECT
    channel_name,
    fetched_at,
    view_count,
    view_count - LAG(view_count) OVER (
        PARTITION BY handle
        ORDER BY fetched_at, id
    ) AS views_since_last_run,
    video_count,
    video_count - LAG(video_count) OVER (
        PARTITION BY handle
        ORDER BY fetched_at, id
    ) AS videos_since_last_run
FROM channel_stats
ORDER BY channel_name, fetched_at, id;
"""
# Why "fetched_at, id"? Two runs in the same second share a time, so the
# order would be a coin toss. id always goes up, so it breaks the tie.


def main():
    conn = sqlite3.connect(DB_FILE)                  # Step 1
    # Step 2: a list of rows (tuples)
    rows = conn.execute(QUERY).fetchall()
    conn.close()

    if not rows:
        print("No data yet. Run fetch_stats.py first.")
        return

    # Step 3: print a header, then one line per row
    print(f"{'Channel':<20} {'Fetched at (UTC)':<27} {'Views':>16} {'Since last run':>16} {'Videos':>8} {'New videos':>12}")
    for name, fetched_at, views, change, videos, video_change in rows:     # unpack each row into four names
        change_text = f"{change:,}" if change is not None else "first run"
        video_change_text = f"{video_change:,}" if video_change is not None else "first run"
        print(
            f"{name[:20]:<20} {fetched_at:<27} {views:>16,} {change_text:>16} {videos:>8,} {video_change_text:>12}")


if __name__ == "__main__":
    main()

# CHECKED: with two runs saved, each channel shows "first run" then a number.
# DECISION: did the maths in SQL, not Python, because that's how a data
#           warehouse (like BigQuery or ClickHouse) would do it.
