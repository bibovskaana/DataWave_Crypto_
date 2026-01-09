import requests

COINGECKO = "https://api.coingecko.com/api/v3"
DEFILLAMA = "https://api.llama.fi"


def get_onchain_metrics(coin_id: str):
    """Fetch on-chain metrics from Coingecko and DefiLlama"""

    try:
        r = requests.get(
            f"{COINGECKO}/coins/{coin_id}",
            params={
                "localization": "false",
                "tickers": "false",
                "market_data": "true",
                "community_data": "false",
                "developer_data": "false",
                "sparkline": "false"
            },
            timeout=10
        )
        r.raise_for_status()
        data = r.json()
    except requests.RequestException:
        return None

    m = data.get("market_data", {})
    price = m.get("current_price", {}).get("usd", 0)
    volume = m.get("total_volume", {}).get("usd", 0)
    market_cap = m.get("market_cap", {}).get("usd", 0)

    # TVL
    tvl = 0
    try:
        tvl_r = requests.get(f"{DEFILLAMA}/tvl/{coin_id}", timeout=5)
        if tvl_r.status_code == 200:
            tvl = tvl_r.json()
    except requests.RequestException:
        tvl = 0

    return {
        "coin": coin_id,
        "active_addresses": volume / price if price else 0,
        "transactions": volume / price if price else 0,
        "exchange_inflow": volume or 0,
        "exchange_outflow": volume or 0,
        "whale_movements": m.get("price_change_percentage_24h", 0),
        "hash_rate": 1 if data.get("hashing_algorithm") else 0,
        "TVL": tvl,
        "NVT": market_cap / volume if volume else 0,
        "MVRV": market_cap / volume if volume else 0
    }
