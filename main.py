import os
import time
import json
import datetime
import traceback
import socket
import threading

from atproto import Client
from comment_generator import generate_summary
from content_moderation import analyze_content
from config import BLUESKY_HANDLE, BLUESKY_APP_PASSWORD

socket.setdefaulttimeout(15)

SUMMARY_LOG = "summaries.log"
ERROR_LOG = "errors.log"
DATA_DIR = "data"
CYCLE_TIMEOUT_SECS = 45

def _json_default(o):
    if o is None or isinstance(o, (str, int, float, bool)):
        return o
    if isinstance(o, (list, tuple, set)):
        return [_json_default(x) for x in o]
    if isinstance(o, dict):
        return {k: _json_default(v) for k, v in o.items()}
    md = getattr(o, "model_dump", None)
    if callable(md):
        try:
            return _json_default(md())
        except Exception:
            pass
    for attr in ("to_dict", "dict"):
        fn = getattr(o, attr, None)
        if callable(fn):
            try:
                return _json_default(fn())
            except Exception:
                pass
    return str(o)


def _now():
    return datetime.datetime.now().isoformat()

def debug(msg):
    print(msg, flush=True)

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
        for post in posts or []:
            json.dump(post, f, ensure_ascii=False, default=_json_default)
            f.write("\n")

def log_summary(keyword, summary):
    with open(SUMMARY_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{_now()}] Keyword: {keyword}\n{summary}\n\n")

def log_error(e):
    with open(ERROR_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{_now()}] {e}\n")

client = Client()

def login_once():
    handle = BLUESKY_HANDLE.strip()
    app_pw = BLUESKY_APP_PASSWORD.strip()
    if not handle or not app_pw:
        raise RuntimeError("Missing BLUESKY credentials.")
    debug(f"Logging into Bluesky as {handle!r}")
    client.login(handle, app_pw)
    debug(f"Logged in. DID={client.me.did}, handle={client.me.handle}")

from curator import search_and_summarize_posts

def try_post_summary(max_retries=1):
    for attempt in range(1, max_retries + 1):
        try:
            result_holder = {"ok": False, "data": None, "err": None}

            def _runner():
                try:
                    result_holder["data"] = search_and_summarize_posts(queries=1, limit=120)
                    result_holder["ok"] = True
                except Exception as e:
                    result_holder["err"] = traceback.format_exc()

            t = threading.Thread(target=_runner, daemon=True)
            debug("attempt=%d: calling curator.search_and_summarize_posts()" % attempt)
            t.start()
            t.join(CYCLE_TIMEOUT_SECS)

            if t.is_alive():
                debug("curator timed out; skipping this cycle.")
                return False

            if not result_holder["ok"]:
                raise RuntimeError(result_holder["err"] or "curator failed")

            keyword, combined_text, posts = result_holder["data"]
            debug(f"keyword={keyword!r} text_len={len(combined_text or '')} posts={len(posts or [])}")

            if not combined_text:
                msg = f"No posts found or empty combined_text for keyword={keyword!r}"
                debug(f"{msg}")
                log_error(msg)
                return False

            append_posts(posts)
            debug("Generating summary…")
            summary = generate_summary(keyword, combined_text) or ""
            debug(f"summary_len={len(summary)}")

            debug("Moderation…")
            analysis = analyze_content(summary) or {}
            if not bool(analysis.get("is_family_friendly", True)):
                msg = f"Skipped posting due to moderation (keyword={keyword!r}), details={analysis}"
                debug("" + msg)
                log_error(msg)
                return False

            clean = summary.strip()
            clean = (clean[:286].rstrip() + "...") if len(clean) > 300 else (clean)
            if not clean:
                debug("Empty summary after cleaning; skipping.")
                return False

            debug("Posting to Bluesky…")
            client.send_post(text=clean)

            debug(f"Posted summary for keyword: {keyword}\n {clean}\n")
            log_summary(keyword, clean)
            return True

        except Exception:
            err = traceback.format_exc()
            debug(f"Error on attempt {attempt}:\n{err}")
            log_error(err)
            time.sleep(2)

    return False

def main():
    debug("Bot starting…")
    login_once()
    interval_sec = 23
    while True:
        debug(f"cycle start {_now()}")
        posted = try_post_summary()
        if not posted:
            debug("No post this cycle.")
        debug(f"Sleeping {interval_sec}s…")
        time.sleep(interval_sec)

if __name__ == "__main__":
    main()
