class DashboardObserver:
    def __init__(self, coin):
        self.coin = coin
        self.onchain = {}
        self.sentiment = {}

    def update_onchain(self, data):
        self.onchain = data or {}

    def update_sentiment(self, data):
        self.sentiment = data or {}
