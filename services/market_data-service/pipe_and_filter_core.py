# market_data-service/fetch_core.py
import requests
import pandas as pd
import time
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor
import threading
from sqlalchemy import create_engine, text

EXCHANGES = ["binance", "kraken"]
START_FULL_HISTORY = datetime(2015, 1, 1, tzinfo=timezone.utc)
THREADS = 10

DB_URL = "postgresql+psycopg2://postgres:postgres_password_ana_bibovska@postgres:5432/crypto"
engine = create_engine(DB_URL, pool_size=20, max_overflow=0)

print_lock = threading.Lock()
write_lock = threading.Lock()


# ---------------- CREATE TABLE ----------------
def create_table_if_not_exists():
    query = """
    CREATE TABLE IF NOT EXISTS market_data (
        open_time TIMESTAMP,
        open FLOAT,
        high FLOAT,
        low FLOAT,
        close FLOAT,
        volume FLOAT,
        coin TEXT,
        symbol TEXT,
        exchange TEXT,
        pair TEXT
    );
    """
    with engine.begin() as conn:
        conn.execute(text(query))
    print("✅ Table 'market_data' is ready.")


# ---------------- UTILITY ----------------
def make_pair(symbol, exchange):
    base = symbol.upper()
    if exchange == "binance":
        return base + "USDT"
    if exchange == "kraken":
        if base == "BTC":
            base = "XBT"
        if base == "DOGE":
            base = "XDG"
        return base + "USD"
    return None


_binance_symbols = None
_kraken_pairs = None


def pair_exists_binance(pair):
    global _binance_symbols
    if _binance_symbols is None:
        data = requests.get("https://api.binance.com/api/v3/exchangeInfo").json()
        _binance_symbols = {s["symbol"] for s in data["symbols"]}
    return pair in _binance_symbols


def pair_exists_kraken(pair):
    global _kraken_pairs
    if _kraken_pairs is None:
        data = requests.get("https://api.kraken.com/0/public/AssetPairs").json()
        _kraken_pairs = set(data["result"].keys()) if "result" in data else set()
    return pair in _kraken_pairs


# ---------------- FETCH ----------------
def fetch_binance(pair, start_date):
    url = "https://api.binance.com/api/v3/klines"
    rows = []
    start_ts = int(start_date.timestamp() * 1000)
    while True:
        params = {"symbol": pair, "interval": "1d", "startTime": start_ts, "limit": 1000}
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


def fetch_kraken(pair, start_date):
    r = requests.get("https://api.kraken.com/0/public/OHLC", params={"pair": pair, "interval": 1440}).json()
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


def fetch_data(exchange, pair, start_date):
    return fetch_binance(pair, start_date) if exchange == "binance" else fetch_kraken(pair, start_date)


# ---------------- DATABASE ----------------
def last_date_from_db(coin, exchange, pair):
    query = """
        SELECT MAX(open_time)
        FROM market_data
        WHERE coin=:coin AND exchange=:exchange AND pair=:pair
    """
    with engine.connect() as conn:
        res = conn.execute(text(query), {"coin": coin, "exchange": exchange, "pair": pair}).scalar()
    return res


# ---------------- PROCESS ----------------
def process_coin(row):
    coin = row["id"]
    sym = row["symbol_up"]
    with print_lock:
        print(f"\n▶ {coin} ({sym})")
    for ex in EXCHANGES:
        pair = make_pair(sym, ex)
        if ex == "binance" and not pair_exists_binance(pair):
            continue
        if ex == "kraken" and not pair_exists_kraken(pair):
            continue
        last = last_date_from_db(coin, ex, pair)
        start_date = START_FULL_HISTORY if last is None else last + timedelta(days=1)
        df = fetch_data(ex, pair, start_date)
        if df is None or df.empty:
            continue
        df["coin"] = coin
        df["symbol"] = sym
        df["exchange"] = ex
        df["pair"] = pair
        with write_lock:
            df.to_sql("market_data", engine, if_exists="append", index=False, method="multi")
        with print_lock:
            print(f"  ✔ {len(df)} rows from {ex}")


# ---------------- MAIN ----------------
def filter_1_get_top_1000():
    all_coins = []
    for page in range(1, 15):
        r = requests.get("https://api.coingecko.com/api/v3/coins/markets", params={
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 250,
            "page": page
        })
        data = r.json()
        if isinstance(data, list):
            all_coins.extend(data)
        time.sleep(4)
    df = pd.DataFrame(all_coins)
    df["total_volume"] = pd.to_numeric(df["total_volume"], errors="coerce")
    df = df.sort_values("total_volume", ascending=False).head(1000)
    df["symbol_up"] = df["symbol"].str.upper()
    return df.reset_index(drop=True)


def main():
    create_table_if_not_exists()
    start = time.time()
    df = filter_1_get_top_1000()
    from concurrent.futures import ThreadPoolExecutor
    with ThreadPoolExecutor(max_workers=THREADS) as ex:
        ex.map(process_coin, [row for _, row in df.iterrows()])
    print(f"\n✅ Finished in {time.time() - start:.2f} seconds")
