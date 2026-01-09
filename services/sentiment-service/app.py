# app.py
from fastapi import FastAPI
from sentiment_core import get_sentiment

app = FastAPI(
    title="Sentiment Microservice",
    description="Provides sentiment analysis for cryptocurrencies",
    version="1.0.0",
)


@app.get("/sentiment/{coin}")
def sentiment_endpoint(coin: str):
    return get_sentiment(coin)
