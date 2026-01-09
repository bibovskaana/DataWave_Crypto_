import requests

class SentimentProvider:
    def fetch(self, coin):
        try:
            r = requests.get(f"http://sentiment:8003/sentiment/%7Bcoin%7D", timeout=10)
            data = r.json()
            data.setdefault("sentiment_score", 0)
            data.setdefault("sentiment_label", "UNKNOWN")
            return data
        except:
            return {"sentiment_score": 0, "sentiment_label": "UNKNOWN"}