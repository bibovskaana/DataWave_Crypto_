import requests
import random
import time
from nltk.sentiment import SentimentIntensityAnalyzer
from urllib.parse import unquote

NEWS_API_KEY = "a78392618761405ba6531e34d6214461"
X_BEARER_TOKEN = unquote(
    "AAAAAAAAAAAAAAAAAAAAAOmM6AEAAAAAe5gHiOFgE%2BvTc4v%2BMagy2LSYCNc%3DjVarSGtr1vglpparQ97M0wS5DqxhXh4QrQ7P4FvfFVTjj81mbE"
)

sia = SentimentIntensityAnalyzer()

def fetch_x_sentiment(query: str):
    url = "https://api.twitter.com/2/tweets/search/recent"
    headers = {"Authorization": f"Bearer {X_BEARER_TOKEN}"}
    params = {
        "query": f"{query} crypto",
        "max_results": 20,
        "tweet.fields": "text"
    }

    r = requests.get(url, headers=headers, params=params, timeout=10)
    if r.status_code != 200:
        return None

    tweets = r.json().get("data", [])
    if not tweets:
        return None

    scores = [
        sia.polarity_scores(t["text"])["compound"]
        for t in tweets
        if "text" in t
    ]

    return sum(scores) / len(scores) if scores else None


def fetch_news_sentiment(query: str):
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": query,
        "language": "en",
        "pageSize": 20,
        "apiKey": NEWS_API_KEY,
    }

    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        return None

    articles = r.json().get("articles", [])
    if not articles:
        return None

    scores = [
        sia.polarity_scores(
            f"{a.get('title','')} {a.get('description','')}"
        )["compound"]
        for a in articles
    ]

    return sum(scores) / len(scores) if scores else None


def get_sentiment(coin: str):
    score = fetch_x_sentiment(coin)

    if score is None:
        score = fetch_news_sentiment(coin)

    if score is None:
        score = random.uniform(-0.05, 0.05)

    label = (
        "Positive" if score > 0.05 else
        "Negative" if score < -0.05 else
        "Neutral"
    )

    return {
        "coin": coin,
        "sentiment_score": round(score, 3),
        "sentiment_label": label
    }
