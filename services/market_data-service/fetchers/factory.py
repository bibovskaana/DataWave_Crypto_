from .binance_fetcher import BinanceFetcher
from .kraken_fetcher import KrakenFetcher

class DataSourceFactory:
    @staticmethod
    def get_fetcher(exchange: str):
        if exchange == "binance":
            return BinanceFetcher()
        elif exchange == "kraken":
            return KrakenFetcher()
        else:
            raise ValueError(f"Unknown exchange: {exchange}")