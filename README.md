# Kids Content Data Lab

A small learning project. It collects public YouTube statistics for a few children's channels every day, stores them in a database, and shows how each channel changes over time.

Built with Python, SQLite and the YouTube Data API. It uses public data only and isn't affiliated with any of the channels.

## What it does (step 1 of 5)

| File | What it does |
| --- | --- |
| `fetch_stats.py` | Asks YouTube for each channel's views, subscribers and video count, and saves one row per channel |
| `view_stats.py` | Prints the history, with "views since last run" worked out in SQL using a window function (`LAG`) |

Run `fetch_stats.py` once a day. After two or more runs, `view_stats.py` shows the change.

## How to run it (Mac)

```bash
cd kids-content-data-lab
python3 -m venv .venv                 # make a private space for this project's packages
source .venv/bin/activate             # switch into it (your prompt shows (.venv))
pip install -r requirements.txt       # install requests
export YOUTUBE_API_KEY="paste-your-key-here"   # only lasts for this terminal window
python3 fetch_stats.py
python3 view_stats.py
```

## Roadmap

1. **Collect the data** (done): daily channel stats into SQLite
2. **Check the data**: missing values, duplicates, stale data
3. **Check the videos**: flag missing descriptions, very long titles, missing tags
4. **Let AI use it**: an MCP server so Claude can answer questions from the database
5. **Test the AI**: 10 questions with known answers, and a score
6. **Try BigQuery**: load the data into the free sandbox and rerun the `LAG` query

## What I learned

- *Testing found a bug:* two runs in the same second got the same timestamp, so the "since last run" order was a coin toss. Fixed by ordering by `fetched_at, id`.
-- *Key rotation:* I exposed my API key while setting up, so I rotated it in Google Cloud and deleted the old one. Keys now live only in an environment variable.
- *Source refresh rate:* two runs a few minutes apart gave identical view counts. YouTube refreshes public counts periodically, so daily runs are enough.