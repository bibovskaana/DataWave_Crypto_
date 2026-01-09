import pandas as pd
import ta


def add_indicators(df):
    df = df.copy()

    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()

    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()

    df["stochastic"] = ta.momentum.StochasticOscillator(
        high=df["high"], low=df["low"], close=df["close"]
    ).stoch()

    df["adx"] = ta.trend.ADXIndicator(
        high=df["high"], low=df["low"], close=df["close"]
    ).adx()

    df["cci"] = ta.trend.CCIIndicator(
        high=df["high"], low=df["low"], close=df["close"], window=20
    ).cci()

    df["sma_20"] = df["close"].rolling(20).mean()
    df["ema_20"] = df["close"].ewm(span=20).mean()

    df["wma_20"] = df["close"].rolling(20).apply(
        lambda prices: (prices * pd.Series(range(1, len(prices) + 1))).sum()
        / pd.Series(range(1, len(prices) + 1)).sum(),
        raw=False
    )

    boll = ta.volatility.BollingerBands(df["close"])
    df["bollinger_high"] = boll.bollinger_hband()
    df["bollinger_low"] = boll.bollinger_lband()

    df["vol_ma_20"] = df["volume"].rolling(20).mean()

    return df


def generate_signal(df):
    latest = df.iloc[-1]

    signals = []

    if latest["rsi"] < 30:
        signals.append("RSI: BUY")
    elif latest["rsi"] > 70:
        signals.append("RSI: SELL")
    else:
        signals.append("RSI: HOLD")

    if latest["macd"] > latest["macd_signal"]:
        signals.append("MACD: BUY")
    elif latest["macd"] < latest["macd_signal"]:
        signals.append("MACD: SELL")
    else:
        signals.append("MACD: HOLD")

    return signals


def resample_timeframes(df):
    return {
        "1D": df,
        "1W": df.resample("W", on="open_time").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum"
        }).dropna(),
        "1M": df.resample("M", on="open_time").agg({
            "open": "first", "high": "max", "low": "min",
            "close": "last", "volume": "sum"
        }).dropna(),
    }
def combined_score(df):
    latest = df.iloc[-1]

    score = 50

    if latest["rsi"] < 30:
        score += 25
    elif latest["rsi"] > 70:
        score -= 25

    if latest["macd"] > latest["macd_signal"]:
        score += 25
    elif latest["macd"] < latest["macd_signal"]:
        score -= 25

    score = max(0, min(100, score))


    if score >= 67:
        status = "BUY"
    elif score <= 33:
        status = "SELL"
    else:
        status = "HOLD"

    return score, status