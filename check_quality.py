"""
WHAT:  Runs simple data quality checks on stats.db and prints a report.
IN:    stats.db (made by fetch_stats.py)
OUT:   one line per check: PASS, WARN or FAIL, with details.
       Exits with code 1 if anything FAILs, so another tool could spot it.
PLAN:
  1. Missing values:  are any important columns empty?
  2. Duplicates:      did the same channel get saved twice in one run?
  3. Freshness:       is the newest data recent enough to trust?
  4. Odd changes:     did any channel's views stay the same or go DOWN since the run before?
SPEED: each check reads the table once, which is tiny for this project.
"""

import sqlite3
import sys                                           # lets us set the exit code
from datetime import datetime, timezone, timedelta

DB_FILE = "stats.db"
MAX_AGE_HOURS = 36    # we run daily, so data older than a day and a half is "stale"


def report(status, check_name, detail):
    """Print one line of the report, e.g.  [PASS] Missing values: none found"""
    print(f"[{status}] {check_name}: {detail}")
    return status                                    # hand the status back so main() can count FAILs


def check_missing(conn):
    """Check 1: these columns should never be empty.
    (subscriber_count is left out on purpose: channels are allowed to hide it.)"""
    count = conn.execute("""
        SELECT COUNT(*)
        FROM channel_stats
        WHERE channel_id IS NULL OR channel_name IS NULL OR view_count IS NULL
    """).fetchone()[0]                               # fetchone() gives one row; [0] takes its only value
    if count == 0:
        return report("PASS", "Missing values", "none found")
    return report("FAIL", "Missing values", f"{count} row(s) have an empty id, name or view count")


def check_duplicates(conn):
    """Check 2: each channel should appear once per run (per fetched_at time)."""
    rows = conn.execute("""
        SELECT handle, fetched_at, COUNT(*) AS copies
        FROM channel_stats
        GROUP BY handle, fetched_at          -- squash rows that share channel AND time
        HAVING COUNT(*) > 1                  -- keep only groups with more than one row
    """).fetchall()
    if not rows:
        return report("PASS", "Duplicates", "none found")
    details = ", ".join(f"{handle} at {when} x{copies}" for handle, when, copies in rows)
    return report("FAIL", "Duplicates", details)


def check_freshness(conn):
    """Check 3: the newest row should be less than MAX_AGE_HOURS old."""
    newest = conn.execute("SELECT MAX(fetched_at) FROM channel_stats").fetchone()[0]
    if newest is None:
        return report("FAIL", "Freshness", "the table is empty")

    newest_time = datetime.fromisoformat(newest)                 # turn the saved text back into a time
    age = datetime.now(timezone.utc) - newest_time               # how long ago that was
    hours_old = age.total_seconds() / 3600                       # 3600 seconds in an hour
    if age > timedelta(hours=MAX_AGE_HOURS):
        return report("FAIL", "Freshness", f"newest data is {hours_old:.0f} hours old (limit {MAX_AGE_HOURS})")
    return report("PASS", "Freshness", f"newest data is {hours_old:.1f} hours old")


def check_odd_changes(conn):
    """Check 4: compare each channel's latest run with the run before it.
    Views going DOWN or staying EXACTLY the same are worth a look,
    but they're a WARN, not a FAIL: YouTube refreshes counts on its own schedule
    and sometimes removes fake views."""
    rows = conn.execute("""
        WITH numbered AS (
            SELECT
                channel_name,
                view_count,
                LAG(view_count) OVER (PARTITION BY handle ORDER BY fetched_at, id) AS previous_views,
                -- ROW_NUMBER counts each channel's rows from newest (1) backwards
                ROW_NUMBER() OVER (PARTITION BY handle ORDER BY fetched_at DESC, id DESC) AS newest_first
            FROM channel_stats
        )
        SELECT channel_name, previous_views, view_count
        FROM numbered
        WHERE newest_first = 1               -- only each channel's latest run
          AND previous_views IS NOT NULL     -- skip channels with only one run so far
          AND view_count <= previous_views   -- same or lower than last time
    """).fetchall()
    if not rows:
        return report("PASS", "Odd changes", "every channel's views went up")
    details = ", ".join(
        f"{name} {'unchanged' if now == before else 'went DOWN'} ({before:,} -> {now:,})"
        for name, before, now in rows
    )
    return report("WARN", "Odd changes", details)


def main():
    conn = sqlite3.connect(DB_FILE)
    results = [
        check_missing(conn),
        check_duplicates(conn),
        check_freshness(conn),
        check_odd_changes(conn),
    ]
    conn.close()

    fails = results.count("FAIL")                   # how many checks failed
    warns = results.count("WARN")
    print(f"\nSummary: {fails} failed, {warns} warnings, {len(results) - fails - warns} passed")
    sys.exit(1 if fails else 0)                     # 1 = something failed, 0 = all good


if __name__ == "__main__":
    main()

# CHECKED: tested with a clean database (all PASS) and a broken one
#          (missing value, duplicate, old data, views going down): each check caught its problem.
# DECISION: "odd changes" is a WARN not a FAIL, because unchanged counts are
#           normal for YouTube (it refreshes on its own schedule).
