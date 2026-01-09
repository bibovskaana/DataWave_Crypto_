import requests

class OnchainProvider:
    def fetch(self, coin):
        try:
            r = requests.get(f"http://onchain:8002/onchain/%7Bcoin%7D", timeout=10)
            return r.json() if r.status_code == 200 else {}
        except:
            return {}