class DataProviderFactory:
    @staticmethod
    def get_provider(provider_type):
        if provider_type == "onchain":
            from .onchain_provider import OnchainProvider
            return OnchainProvider()

        if provider_type == "sentiment":
            from .sentiment_provider import SentimentProvider
            return SentimentProvider()

        raise ValueError("Unknown provider type")