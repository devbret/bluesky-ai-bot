import random
from atproto import Client
from config import BLUESKY_HANDLE, BLUESKY_APP_PASSWORD

client = Client()
client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

KEYWORDS = ['content', 'keywords']

def search_and_summarize_posts(limit=23, top_n=3):
    keyword_one = random.choice(KEYWORDS)
    keyword_two = random.choice(KEYWORDS)
    combined_keyword = f"{keyword_one} {keyword_two}"
    print(f"🔍 Searching for: {combined_keyword}")

    results = client.app.bsky.feed.search_posts({'q': combined_keyword, 'limit': limit})
    posts = []

    for item in results.posts:
        try:
            post_text = item.record.text
            is_reply = bool(item.record.reply)
            repost_count = item.repost_count or 0
            like_count = item.like_count or 0
        except AttributeError:
            continue

        if post_text and not is_reply and len(post_text) > 30:
            posts.append({
                "text": post_text.strip(),
                "score": like_count + (2 * repost_count),
                "uri": item.uri,
                "cid": item.cid,
                "author": getattr(item.author, 'handle', 'unknown')
            })

    top_posts = sorted(posts, key=lambda p: p["score"], reverse=True)[:top_n]
    combined_text = "\n\n".join([p["text"] for p in top_posts])

    return combined_keyword, combined_text, posts

