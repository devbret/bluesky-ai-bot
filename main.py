import time
import datetime
import traceback
import os
import json
from curator import search_and_summarize_posts
from comment_generator import generate_summary
from content_moderation import analyze_content
from atproto import Client
from config import BLUESKY_HANDLE, BLUESKY_APP_PASSWORD

SUMMARY_LOG = "summaries.log"
ERROR_LOG = "errors.log"
DATA_DIR = "data"

client = Client()
client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

def ensure_data_dir():
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)

def get_today_filepath():
    today_str = datetime.date.today().isoformat()
    return os.path.join(DATA_DIR, f"{today_str}.jsonl")

def append_posts(posts):
    ensure_data_dir()
    path = get_today_filepath()
    with open(path, "a", encoding="utf-8") as f:
        for post in posts:
            json.dump(post, f, ensure_ascii=False)
            f.write("\n")

def log_summary(keyword, summary):
    timestamp = datetime.datetime.now().isoformat()
    with open(SUMMARY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] Keyword: {keyword}\n")
        f.write(f"{summary}\n\n")

def log_error(e):
    timestamp = datetime.datetime.now().isoformat()
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{timestamp}] {str(e)}\n")

def try_post_summary(max_retries=3):
    for attempt in range(max_retries + 1):
        try:
            keyword, combined_text, posts = search_and_summarize_posts()
            if combined_text:
                append_posts(posts)
                summary = generate_summary(keyword, combined_text)
                analysis = analyze_content(summary)
                if not analysis["is_family_friendly"]:
                    print(f"🚫 Skipped posting due to content concerns: {analysis}")
                    log_error(f"Skipped summary (keyword: {keyword}) due to moderation check: {analysis}")
                    return
                if summary:
                    summary = summary.strip()
                    clean_summary = "AI Bot: " + summary[:286].rstrip() + "..." if len(summary) > 300 else "AI Bot: " + summary

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
        print("⏳ Waiting 2 minutes before next post...\n")
        time.sleep(2 * 60)
