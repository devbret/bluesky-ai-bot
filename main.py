import time
import datetime
import traceback
import os
import json
from curator import search_and_summarize_posts
from comment_generator import generate_summary
from atproto import Client
from config import BLUESKY_HANDLE, BLUESKY_APP_PASSWORD

SUMMARY_LOG = "summaries.log"
ERROR_LOG = "errors.log"
CACHE = "cache.json"

client = Client()
client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

def log_summary(keyword, summary):
    timestamp = datetime.datetime.now().isoformat()
    with open(SUMMARY_LOG, "a") as f:
        f.write(f"[{timestamp}] Keyword: {keyword}\n")
        f.write(f"{summary}\n\n")

def cache_posts(posts):
    if not isinstance(posts, list):
        raise ValueError("Expected posts to be a list of dictionaries.")

    existing_cache = []
    if os.path.exists(CACHE):
        with open(CACHE, "r") as f:
            try:
                existing_cache = json.load(f)
            except json.JSONDecodeError:
                print("⚠️ Warning: cache.json is corrupted or empty. Starting fresh.")

    existing_cache.extend(posts)

    with open(CACHE, "w") as f:
        json.dump(existing_cache, f, indent=2)

def log_error(error_msg):
    timestamp = datetime.datetime.now().isoformat()
    with open(ERROR_LOG, "a") as f:
        f.write(f"[{timestamp}] {error_msg}\n\n")

def try_post_summary(max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            keyword, combined_text, posts = search_and_summarize_posts()
            if combined_text:
                cache_posts(posts)
                summary = generate_summary(keyword, combined_text)
                if summary:
                    summary = summary.strip()
                    clean_summary = summary[:295].rstrip() + "..." if len(summary) > 300 else summary

                    client.app.bsky.feed.post.create(
                        record={
                            "$type": "app.bsky.feed.post",
                            "text": clean_summary,
                            "createdAt": client.get_current_time_iso()
                        },
                        repo=client.me.did
                    )
                    print(f"✅ Posted summary for keyword: {keyword}")
                    print(f"📝 {clean_summary}\n")
                    log_summary(keyword, clean_summary)
                    return
            else:
                print(f"⚠️ Attempt {attempt + 1}: No posts found for keyword: {keyword}")
        except Exception as e:
            err_trace = traceback.format_exc()
            print(f"❌ Error occurred on attempt {attempt + 1}:\n{err_trace}")
            log_error(err_trace)

def run():
    try_post_summary()

if __name__ == "__main__":
    while True:
        run()
        print("⏳ Waiting 5 minutes before next post...\n")
        time.sleep(5 * 60)
