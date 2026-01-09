import pandas as pd
import requests
import time
from base_fetcher import MarketDataFetcher

from datetime import datetime, timezone


class BinanceFetcher(MarketDataFetcher):
    def fetch(self, pair, start_date):
        url = "https://api.binance.com/api/v3/klines"
        rows = []
        start_ts = int(start_date.timestamp() * 1000)

        while True:
            params = {
                "symbol": pair,
                "interval": "1d",
                "startTime": start_ts,
                "limit": 1000
            }
            data = requests.get(url, params=params).json()
            if not isinstance(data, list) or not data:
                break
            rows.extend(data)
            start_ts = data[-1][0] + 1
            time.sleep(0.05)

        if not rows:
            return None

        df = pd.DataFrame(rows, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "ct", "q1", "q2", "q3", "q4", "q5"
        ])

        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
        for col in ["open", "high", "low", "close", "volume"]:
            df[col] = pd.to_numeric(df[col], errors="coerce", downcast="float")

        return df[["open_time", "open", "high", "low", "close", "volume"]]