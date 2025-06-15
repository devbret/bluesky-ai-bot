import anthropic
import time
from config import ANTHROPIC_API_KEY

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def generate_summary(keyword, combined_posts, retries=3, delay=2):
    system_prompt = (
        f"You are a well-spoken thought leader and concise tech commentator. "
        f"Summarize and add appropriate commentary to the most interesting or recurring insights from recent Bluesky posts about '{keyword}'. "
        f"Your response must sound natural, insightful and fit within 250 characters. Avoid hashtags and usernames."
    )

    if not combined_posts.strip():
        print("Error: No combined posts provided for summarization.")
        return None

    for attempt in range(1, retries + 1):
        try:
            response = client.messages.create(
                model="claude-opus-4-20250514",
                max_tokens=120,
                temperature=0.7,
                system=system_prompt,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": f"Here are some recent posts on '{keyword}':\n\n{combined_posts}\n\nSummarize them in 1 insightful paragraph, under 250 characters."
                            }
                        ]
                    }
                ]
            )

            if not response.content:
                raise IndexError("Claude returned an empty response.")

            return response.content[0].text.strip()

        except Exception as e:
            print(f"Attempt {attempt}: Error generating summary: {e}")
            if attempt < retries:
                time.sleep(delay)
            else:
                print("All retry attempts failed.")
                return None
