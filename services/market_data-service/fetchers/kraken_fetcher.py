import pandas as pd
import requests
from datetime import datetime, timezone
from base_fetcher import MarketDataFetcher

class KrakenFetcher(MarketDataFetcher):
    def fetch(self, pair, start_date):
        r = requests.get(
            "https://api.kraken.com/0/public/OHLC",
            params={"pair": pair, "interval": 1440}
        ).json()

        if "result" not in r:
            return None

        key = list(r["result"].keys())[0]
        rows = []
        for x in r["result"][key]:
            ts = datetime.fromtimestamp(x[0], tz=timezone.utc)
            if ts >= start_date:
                rows.append({
                    "open_time": ts,
                    "open": float(x[1]),
                    "high": float(x[2]),
                    "low": float(x[3]),
                    "close": float(x[4]),
                    "volume": float(x[6])
                })

        return pd.DataFrame(rows) if rows else None