import random
import time
import socket
from typing import List, Tuple, Dict, Any, Optional

from atproto import Client
from config import BLUESKY_HANDLE, BLUESKY_APP_PASSWORD

socket.setdefaulttimeout(15)

client = Client()
client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

KEYWORDS = ["keywords", "keywords"]
MAX_PER_QUERY = 120
MIN_TEXT_LEN = 30
PER_QUERY_TIME_CAP = 20 

def _debug(msg: str) -> None:
    print(msg, flush=True)

def _unique_keyword_pair() -> Tuple[str, str]:
    if len(KEYWORDS) < 2:
        raise ValueError("Need at least 2 KEYWORDS.")
    return tuple(random.sample(KEYWORDS, 2))

def _collect_posts_for_query(q: str, per_query_limit: int) -> List[Any]:
    posts: List[Any] = []
    cursor: Optional[str] = None
    start = time.monotonic()

    while len(posts) < per_query_limit:
        if time.monotonic() - start > PER_QUERY_TIME_CAP:
            _debug(f"Time cap hit for query {q!r}")
            break
        try:
            _debug(f"search_posts q={q!r} have={len(posts)} cursor={bool(cursor)}")
            resp = client.app.bsky.feed.search_posts(
                params={
                    "q": q,
                    "limit": min(100, per_query_limit - len(posts)),
                    "cursor": cursor
                }
            )
            _debug("Got response")
        except Exception as e:
            _debug(f"search_posts error for {q!r}: {e}")
            break

        batch = getattr(resp, "posts", []) or []
        if not batch:
            _debug("Empty batch; done")
            break

        posts.extend(batch)
        cursor = getattr(resp, "cursor", None)
        _debug(f"… fetched {len(batch)} (total {len(posts)}) next_cursor={bool(cursor)}")
        if not cursor:
            break

        time.sleep(0.4) 

    return posts

def _safe_text(item: Any) -> str:
    rec = getattr(item, "record", None)
    return ((getattr(rec, "text", "") or "").strip()) if rec else ""

def _is_reply(item: Any) -> bool:
    rec = getattr(item, "record", None)
    return bool(getattr(rec, "reply", None)) if rec else False

def _facets_links(item: Any) -> List[str]:
    rec = getattr(item, "record", None)
    if not rec:
        return []
    out: List[str] = []
    for facet in (getattr(rec, "facets", []) or []):
        for feat in (getattr(facet, "features", []) or []):
            uri = getattr(feat, "uri", None)
            if uri:
                out.append(uri)
    return out

def _post_dict(item: Any, kw: str) -> Dict[str, Any]:
    rec = getattr(item, "record", None)
    author = getattr(item, "author", None)
    return {
        "text": _safe_text(item),
        "score": (getattr(item, "like_count", 0) or 0) + 2 * (getattr(item, "repost_count", 0) or 0),
        "like_count": getattr(item, "like_count", 0) or 0,
        "repost_count": getattr(item, "repost_count", 0) or 0,
        "reply_count": getattr(item, "reply_count", 0) or 0,
        "quote_count": getattr(item, "quote_count", 0) or 0,
        "uri": getattr(item, "uri", None),
        "cid": getattr(item, "cid", None),
        "indexed_at": getattr(item, "indexed_at", None),
        "embed": getattr(item, "embed", None),
        "threadgate": getattr(item, "threadgate", None),
        "keywords": kw,
        "post_created_at": getattr(rec, "created_at", None) if rec else None,
        "langs": getattr(rec, "langs", []) or [] if rec else [],
        "author_handle": getattr(author, "handle", None) if author else None,
        "author_did": getattr(author, "did", None) if author else None,
        "author_avatar": getattr(author, "avatar", None) if author else None,
        "author_display_name": getattr(author, "display_name", "") if author else "",
        "author_created_at": getattr(author, "created_at", None) if author else None,
        "link_urls": _facets_links(item),
    }

def search_and_summarize_posts(queries: int = 1, limit: int = MAX_PER_QUERY):
    _debug("curator.search_and_summarize_posts: start")
    k1, k2 = _unique_keyword_pair()
    combined_keyword = f"{k1} {k2}"
    _debug(f"🔍 Searching for: {combined_keyword!r}")

    raw = _collect_posts_for_query(combined_keyword, per_query_limit=limit)

    kept: List[Dict[str, Any]] = []
    for it in raw:
        try:
            if _is_reply(it):
                continue
            txt = _safe_text(it)
            if len(txt) < MIN_TEXT_LEN:
                continue
            kept.append(_post_dict(it, combined_keyword))
        except Exception as e:
            _debug(f"⚠️ parse error skipped: {e}")
            continue

    combined_text = "\n\n".join(p["text"] for p in kept)
    _debug(f"collected={len(raw)} kept={len(kept)} text_chars={len(combined_text)}")
    _debug("curator.search_and_summarize_posts: end")
    return combined_keyword, combined_text, kept
