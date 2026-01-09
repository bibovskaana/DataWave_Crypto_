import streamlit as st
import pandas as pd
import requests
import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError

from lstm_model_core import train_lstm_model as train_lstm
from scoring import calculate_signal

# ============================================================
# DATABASE CONFIG
# ============================================================
DB_URL = os.getenv("DB_URL")

def wait_for_db(max_retries=10, delay=2):
    retries = 0
    while retries < max_retries:
        try:
            engine = create_engine(DB_URL)
            with engine.connect():
                pass
            return engine
        except OperationalError:
            print(f"Waiting for database... ({retries+1}/{max_retries})")
            time.sleep(delay)
            retries += 1
    raise RuntimeError("Database not available")

engine = wait_for_db()

def load_data(query="SELECT * FROM public.market_data"):
    return pd.read_sql(query, engine, parse_dates=["open_time"])

# ============================================================
# STREAMLIT CONFIG
# ============================================================
st.set_page_config(page_title="DataWave Crypto", layout="wide")
st.title("🌊 DataWave Crypto (PoC)")

# ============================================================
# NAVIGATION
# ============================================================
option = st.sidebar.selectbox(
    "Select Screen",
    [
        "Home",
        "Start Full Fetch",
        "View Top 50 Coins",
        "Check Last Fetch",
        "Charts",
        "Indicators",
        "LSTM crypto prediction model",
        "On-chain & Sentiment Analysis",
    ],
)

# ============================================================
# HOME
# ============================================================
if option == "Home":
    st.write("Добредојдовте во proof-of-concept dashboard.")
    st.write("""
    - Fetch на топ 1000 криптовалути (10+ години)
    - Binance и Kraken
    - PostgreSQL backend
    - Technical indicators, LSTM, sentiment & on-chain
    """)

# ============================================================
# START FULL FETCH
# ============================================================
elif option == "Start Full Fetch":
    st.subheader("Стартување на full fetch")

    if st.button("Start Fetch"):
        with st.spinner("Fetching market data..."):
            try:
                r = requests.post("http://market_data:8001/fetch", timeout=10)
                if r.status_code == 200:
                    st.success("Fetch е успешно стартуван!")
                else:
                    st.error(f"Fetch error: {r.status_code}")
            except requests.exceptions.RequestException as e:
                st.error(f"Market service недостапен: {e}")

# ============================================================
# VIEW TOP 50
# ============================================================
elif option == "View Top 50 Coins":
    st.subheader("Top 50 криптовалути според вкупен volume")

    df = load_data()
    if df.empty:
        st.warning("Нема податоци во базата.")
        st.stop()

    top_50 = (
        df.groupby("coin", as_index=False)["volume"]
        .sum()
        .sort_values("volume", ascending=False)
        .head(50)
    )

    top_50["volume"] = top_50["volume"].round(2)
    st.dataframe(top_50, use_container_width=True)

# ============================================================
# CHECK LAST FETCH
# ============================================================
elif option == "Check Last Fetch":
    st.subheader("High / Low / Volume по берза")

    df = load_data()
    if df.empty:
        st.warning("Нема податоци.")
        st.stop()

    coin = st.selectbox("Избери криптовалута", sorted(df["coin"].unique()))
    coin_df = df[df["coin"] == coin]

    stats = (
        coin_df
        .groupby("exchange", as_index=False)
        .agg(
            high=("high", "max"),
            low=("low", "min"),
            volume=("volume", "sum"),
        )
    )

    st.dataframe(stats.round(6), use_container_width=True)

# ============================================================
# CHARTS
# ============================================================
elif option == "Charts":
    st.subheader("Графици: Цена / Волумен / Market Cap")

    df = load_data().sort_values("open_time")
    coin = st.selectbox("Избери криптовалута", sorted(df["coin"].unique()))
    coin_df = df[df["coin"] == coin]

    if coin_df.empty:
        st.warning("Нема податоци.")
        st.stop()

    st.line_chart(coin_df.set_index("open_time")["close"])
    st.line_chart(coin_df.set_index("open_time")["volume"])

    coin_df["market_cap"] = coin_df["close"] * coin_df["volume"]
    st.line_chart(coin_df.set_index("open_time")["market_cap"])

# ============================================================
# INDICATORS
# ============================================================
elif option == "Indicators":
    st.title("Технички индикатори")

    from indicators import add_indicators, generate_signal, resample_timeframes

    df = load_data().sort_values("open_time")

    if df.empty:
        st.warning("Нема податоци во базата.")
        st.stop()

    coin = st.selectbox("Избери coin", sorted(df["coin"].unique()))
    coin_df = df[df["coin"] == coin].copy()

    tf = resample_timeframes(coin_df)
    timeframe = st.selectbox("Timeframe", ["1D", "1W", "1M"])
    selected_df = tf[timeframe].copy()

    analyzed = add_indicators(selected_df).dropna()

    if analyzed.dropna().empty:
        st.warning("Нема доволно податоци за индикатори.")
        st.stop()

    analyzed = analyzed.dropna()

    st.line_chart(analyzed[["close"]])
    st.line_chart(analyzed[["rsi"]])
    st.line_chart(analyzed[["macd"]])

    st.dataframe(analyzed.tail(20), use_container_width=True)

    st.subheader("Сигнали")
    st.write(generate_signal(analyzed))


# ============================================================
# LSTM MODEL (ИСТА ВИЗУЕЛИЗАЦИЈА КАКО ПРВИОТ КОД)
# ============================================================
elif option == "LSTM crypto prediction model":
    st.title("📈 LSTM Crypto Price Prediction")

    df = load_data()
    coin = st.selectbox("Избери криптовалута", sorted(df["coin"].unique()))

    coin_df = (
        df[df["coin"] == coin]
        .sort_values("open_time")
        .tail(500)
        [["open", "high", "low", "close", "volume"]]
        .dropna()
    )

    if len(coin_df) < 60:
        st.warning("Нема доволно податоци за LSTM.")
        st.stop()

    lookback = st.slider("Lookback период", 10, 60, 30)
    epochs = st.slider("Epochs", 10, 100, 30, step=10)

    if st.button("Train LSTM Model"):
        with st.spinner("Тренирање на LSTM моделот..."):
            model, pred, real, rmse, mape, r2, next_price = train_lstm(
                coin_df.to_dict("records"),
                lookback=lookback,
                epochs=epochs
            )

        st.success("Моделот е успешно истрениран!")

        c1, c2, c3 = st.columns(3)
        c1.metric("RMSE", f"{rmse:.4f}")
        c2.metric("MAPE", f"{mape:.4f}")
        c3.metric("R²", f"{r2:.4f}")

        st.subheader("Next-day prediction")
        st.metric("Predicted Close Price", f"{next_price:.4f}")

        chart_df = pd.DataFrame({
            "Real Price": real,
            "Predicted Price": pred
        })

        st.line_chart(chart_df)

# ============================================================
# ON-CHAIN & SENTIMENT
# ============================================================
elif option == "On-chain & Sentiment Analysis":
    st.title("On-chain & Sentiment Analysis")

    from data_providers.factory import DataProviderFactory
    from observers.dashboard_observer import DashboardObserver

    df = load_data("SELECT DISTINCT coin FROM public.market_data")
    coin = st.selectbox("Избери криптовалута", sorted(df["coin"].unique()))

    # ---- Observer instance ----
    dashboard = DashboardObserver(coin)

    # ---- Providers (Factory builds them) ----
    onchain_provider = DataProviderFactory.get_provider("onchain")
    sentiment_provider = DataProviderFactory.get_provider("sentiment")

    # ---- Execute with loading states ----
    with st.spinner("Fetching on-chain data..."):
        onchain_data = onchain_provider.fetch(coin)
        dashboard.update_onchain(onchain_data)

    with st.spinner("Analyzing sentiment..."):
        sentiment_data = sentiment_provider.fetch(coin)
        dashboard.update_sentiment(sentiment_data)

    # ---- Visual output ----
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("On-chain metrics")
        st.json(onchain_data or {})

    with c2:
        score = sentiment_data.get("sentiment_score", 0)
        label = sentiment_data.get("sentiment_label", "UNKNOWN")
        st.subheader("Sentiment analysis")
        st.metric("Sentiment Score", score)
        st.metric("Sentiment Label", label)

    # ---- Trading signal ----
    final_score, signal = calculate_signal(onchain_data or {}, score)

    st.subheader("Combined Trading Signal")

    if signal == "BUY":
        st.success(f"🟢 BUY — Combined score: {final_score}")
    elif signal == "SELL":
        st.error(f"🔴 SELL — Combined score: {final_score}")
    else:
        st.warning(f"🟡 HOLD — Combined score: {final_score}")