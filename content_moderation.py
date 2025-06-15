from textblob import TextBlob
from better_profanity import profanity

def analyze_content(summary_text):
    blob = TextBlob(summary_text)
    polarity = blob.sentiment.polarity
    subjectivity = blob.sentiment.subjectivity

    contains_profanity = profanity.contains_profanity(summary_text)

    is_family_friendly = not contains_profanity and polarity >= -0.5

    return {
        "is_family_friendly": is_family_friendly,
        "contains_profanity": contains_profanity,
        "sentiment_polarity": polarity,
        "sentiment_subjectivity": subjectivity,
    }
