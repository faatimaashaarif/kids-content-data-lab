"""
WHAT:  Checks the latest videos (from fetch_videos.py) for content problems
       and prints a report.
IN:    the "videos" table in stats.db
OUT:   one line per check (PASS or WARN), plus the videos it flagged.
PLAN:
  1. No description:  videos with an empty description
  2. Long titles:     titles longer than MAX_TITLE_LENGTH characters
  3. No tags:         videos with zero tags
  4. Bonus:           a check of your own
NOTE:  These are all WARN, not FAIL. The data isn't broken; these are
       things a content team might want to look at.
"""

import sqlite3

DB_FILE = "stats.db"
MAX_TITLE_LENGTH = 70    # YouTube cuts off longer titles in search results


def report(status, check_name, detail):
    """Print one line of the report and hand the status back."""
    print(f"[{status}] {check_name}: {detail}")
    return status


# ---------------------------------------------------------------------------
# CHECK 1: written for you, as the example to copy
# ---------------------------------------------------------------------------
def check_no_description(conn):
    """Find videos whose description is empty."""
    rows = conn.execute("""
        SELECT handle, title
        FROM videos
        WHERE description IS NULL OR TRIM(description) = ''
    """).fetchall()
    # TRIM removes spaces from both ends, so a description of just "   " counts as empty too

    if not rows:
        return report("PASS", "No description", "every video has a description")

    status = report("WARN", "No description", f"{len(rows)} video(s) have no description")
    for handle, title in rows:                     # list each flagged video underneath
        print(f"      {handle}: {title[:60]}")     # [:60] keeps long titles tidy
    return status


# ---------------------------------------------------------------------------
# CHECK 2: YOUR TURN
# ---------------------------------------------------------------------------
def check_long_titles(conn):
    """Find videos whose title is longer than MAX_TITLE_LENGTH characters."""
    rows = conn.execute("""
        SELECT handle, title
        FROM videos
        WHERE LENGTH(title) > ? 
    """, (MAX_TITLE_LENGTH,)).fetchall()
    
    if not rows:
        return report("PASS", "Long title", "every title is within limit")

    status = report("WARN", "No title", f"{len(rows)} video(s) have title over limit")
    for handle, title in rows:                     # list each flagged video underneath
        print(f"      {handle}: {title[:60]}")     # [:60] keeps long titles tidy
    return status


# ---------------------------------------------------------------------------
# CHECK 3: YOUR TURN
# ---------------------------------------------------------------------------
def check_no_tags(conn):
    """Find videos that have no tags at all."""
    rows = conn.execute("""
        SELECT handle, title
        FROM videos
        WHERE tag_count = 0
    """).fetchall()
    # TRIM removes spaces from both ends, so a tag of just "   " counts as empty too

    if not rows:
        return report("PASS", "No tags", "every video has tags")

    status = report("WARN", "No tags", f"{len(rows)} video(s) have no tags")
    for handle, title in rows:                     # list each flagged video underneath
        print(f"      {handle}: {title[:60]}")     # [:60] keeps long titles tidy
    return status


# ---------------------------------------------------------------------------
# CHECK 4 (BONUS): YOUR OWN IDEA
# ---------------------------------------------------------------------------
def check_bonus(conn):
    """Your own check. Ideas:
       - How many videos per channel have '#shorts' in the title?
         (SQL: title LIKE '%#shorts%'  ->  % means "anything before or after")
       - Any videos NOT marked made_for_kids = 1?
    """
    # TODO (optional): write your own check, or leave this as it is.
    return report("TODO", "Bonus", "not written yet")


def main():
    conn = sqlite3.connect(DB_FILE)
    results = [
        check_no_description(conn),
        check_long_titles(conn),
        check_no_tags(conn),
        check_bonus(conn),
    ]
    conn.close()

    warns = results.count("WARN")
    todos = results.count("TODO")
    print(f"\nSummary: {warns} warnings, {len(results) - warns - todos} passed, {todos} still to write")


if __name__ == "__main__":
    main()
