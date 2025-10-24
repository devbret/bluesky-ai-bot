import requests
import time
import os

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://192.168.1.157:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mixtral:8x7b")

def generate_summary(keyword, combined_posts, retries=3, delay=2):
    system_prompt = (
        f"You are a well-spoken thought leader and concise tech commentator. "
        f"Summarize and add appropriate commentary to the most interesting or recurring insights from recent Bluesky posts about '{keyword}'. "
        f"Your response must sound natural, insightful and be only one sentence long. Avoid hashtags, links and usernames."
    )

    if not combined_posts.strip():
        print("Error: No combined posts provided for summarization.")
        return None

    payload = {
        "model": OLLAMA_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": f"Here are some recent posts on '{keyword}':\n\n{combined_posts}\n\nSummarize them in 1 insightful sentence, under 150 characters."
            }
        ],
        "options": {
            "temperature": 0.2,
            "num_predict": 120
        },
        "stream": False
    }

    for attempt in range(1, retries + 1):
        try:
            response = requests.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
            response.raise_for_status()
            data = response.json()

            if "message" in data and "content" in data["message"]:
                return data["message"]["content"].strip()
            elif "content" in data:
                return data["content"].strip()
            else:
                raise IndexError("Ollama returned an unexpected response format.")

        except Exception as e:
            print(f"Attempt {attempt}: Error generating summary: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                print("All retry attempts failed.")
                return None
