import streamlit as st
import pandas as pd
from datetime import datetime, timezone, timedelta
import threading
from lstm_model import train_lstm

from pipe_and_filter import main, filter_2_last_date, DATA_DIR, EXCHANGES, make_pair

print_lock = threading.Lock()
MASTER_CSV = "all_merged.csv"

st.set_page_config(page_title="DataWave Crypto", layout="wide")
st.title("DataWave Crypto (PoC)")

#Navigation
option = st.sidebar.selectbox(
    "Select Screen",
    ["Home", "Start Full Fetch", "View Top 50 Coins", "Check Last Fetch", "Charts", "Indicators", "LSTM crypto prediction model", "On-chain & Sentiment Analysis"]
)

#Home
if option == "Home":
    st.write("Добредојдовте во proof-of-concept dashboard.")
    st.write("""
    Тука можете да стартувате fetch на 1000 топ криптовалути последните 10 години од берзите binance и kraken  
    Да видите топ 50 криптовалути или да проверите статус на последен fetch.
    """)

#Start Full Fetch
elif option == "Start Full Fetch":
    st.write("Стартување на full fetch за топ 1000 coins...")

    if st.button("Start Fetch"):
        with st.spinner("Fetching data, please wait..."):
            main()
        st.success("Fetch завршен!")
        st.write(f"Податоците се зачувани во `{MASTER_CSV}`")

#View Top 50 Coins
elif option == "View Top 50 Coins":
    st.subheader("Top 50 криптовалути според најголем вкупен volume")

    try:
        df = pd.read_csv(MASTER_CSV)

        if df.empty:
            st.warning("CSV фајлот постои, но нема податоци. Fetch-от можеби не успеал.")
        else:
            required_columns = {"coin", "volume"}
            if not required_columns.issubset(df.columns):
                st.error(
                    f"`{MASTER_CSV}` мора да ги содржи колоните {required_columns}, "
                    f"но ги има: {set(df.columns)}"
                )
            else:
                top_50 = (
                    df.groupby("coin", as_index=False)["volume"]
                    .sum()
                    .sort_values("volume", ascending=False)
                    .head(50)
                )

                top_50["volume"] = top_50["volume"].round(2)

                st.dataframe(top_50, use_container_width=True)

                st.download_button(
                    label="⬇️ Симни го целиот all_merged.csv",
                    data=open(MASTER_CSV, "rb").read(),
                    file_name="all_merged.csv",
                    mime="text/csv"
                )

    except FileNotFoundError:
        st.warning("Фајлот `all_merged.csv` не постои. Прво стартувај fetch!")

    except pd.errors.EmptyDataError:
        st.error(
            "`all_merged.csv` е празен фајл (нема колони). "
            "Провери дали fetch-от навистина завршил успешно."
        )

elif option == "Charts":
    st.subheader("Графици: Цена / Волумен / Market Cap")

    try:
        df = pd.read_csv(MASTER_CSV, parse_dates=["open_time"])
        df = df.sort_values("open_time")

        coin_list = sorted(df["coin"].astype(str).unique())
        coin = st.selectbox("Избери криптовалута", coin_list)

        coin_df = df[df["coin"] == coin].copy()

        if coin_df.empty:
            st.warning("Нема податоци за избраната криптовалута.")
            st.stop()

        # цена
        st.line_chart(
            coin_df.set_index("open_time")["close"],
            width=1200,
            height=300,
        )

        # волумен
        st.line_chart(
            coin_df.set_index("open_time")["volume"],
            width=1200,
            height=300,
        )

        # market cap = close * volume (ако немаш друга метрика)
        coin_df["market_cap"] = pd.to_numeric(coin_df["close"], errors="coerce") * \
                                pd.to_numeric(coin_df["volume"], errors="coerce")

        st.line_chart(
            coin_df.set_index("open_time")["market_cap"],
            width=1200,
            height=300,
        )

    except FileNotFoundError:
        st.error("CSV file не постои. Прво стартувај fetch!")

elif option == "Indicators":
    st.title("Технички индикатори")

    from indicators import add_indicators, generate_signal, resample_timeframes

    df = pd.read_csv(MASTER_CSV, parse_dates=["open_time"])

    coin = st.selectbox("Избери coin", sorted(df["coin"].unique()))

    coin_df = df[df["coin"] == coin].copy().sort_values("open_time")

    tf = resample_timeframes(coin_df)

    timeframe = st.selectbox("Timeframe", ["1D", "1W", "1M"])

    selected_df = tf[timeframe].copy()

    analyzed = add_indicators(selected_df)
    analyzed = analyzed.dropna().copy()

    if "pair" in analyzed.columns:
        analyzed = analyzed.drop(columns=["pair"])

    meta_cols = [c for c in ["coin", "symbol", "exchange"] if c in analyzed.columns]
    other_cols = [c for c in analyzed.columns if c not in meta_cols]
    analyzed = analyzed[meta_cols + other_cols]

    st.line_chart(analyzed[["close"]])
    st.line_chart(analyzed[["rsi"]])
    st.line_chart(analyzed[["macd"]])

    st.dataframe(analyzed.tail(20))

    st.subheader("Сигнали (buy/sell/hold)")
    signals = generate_signal(analyzed)
    st.write(signals)

elif option == "LSTM crypto prediction model":
    st.title("📈 LSTM Crypto Price Prediction")

    df = pd.read_csv(MASTER_CSV, parse_dates=["open_time"])

    coin = st.selectbox(
        "Избери криптовалута",
        sorted(df["coin"].unique())
    )

    coin_df = (
        df[df["coin"] == coin]
        .sort_values("open_time")
        .tail(500)   # стабилност
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
                coin_df,
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


#Check Last Fetch
elif option == "Check Last Fetch":
    st.subheader("Преглед на high / low / volume по криптовалута")

    try:
        df = pd.read_csv(MASTER_CSV)

        st.markdown("""
        **High** = највисока цена на криптовалутата  
        На пример, ако BTC достигнал 69.000 USDT на Binance, тоа е неговиот high.

        **Low** = најниска цена на криптовалутата  
        На пример, ако BTC паднал на 32.000 USDT, тоа е неговиот low.

        **Volume** = вкупен обем на тргување  
        Голем volume значи дека има многу тргувања, а мал volume покажува помала активност на пазарот.
        """)

        if df.empty:
            st.warning("CSV фајлот е празен.")
            st.stop()

        # clean
        df["coin"] = df["coin"].astype(str).str.upper().str.strip()
        df["high"] = pd.to_numeric(df["high"], errors="coerce")
        df["low"] = pd.to_numeric(df["low"], errors="coerce")
        df["volume"] = pd.to_numeric(df["volume"], errors="coerce")

        coin_list = sorted(df["coin"].dropna().unique())

        selected_coin = st.selectbox(
            "Избери криптовалута",
            options=coin_list
        )

        coin_df = df[df["coin"] == selected_coin]

        if coin_df.empty:
            st.warning("Нема податоци за оваа криптовалута.")
        else:
            stats = (
                coin_df
                .groupby("exchange", as_index=False)
                .agg(
                    high=("high", "max"),
                    low=("low", "min"),
                    volume=("volume", "sum"),
                )
            )

            stats["high"] = stats["high"].round(6)
            stats["low"] = stats["low"].round(6)
            stats["volume"] = stats["volume"].round(2)

            st.success(f"Статистика за {selected_coin}")
            st.dataframe(stats, use_container_width=True)

    except FileNotFoundError:
        st.error("`all_merged.csv` не постои.")


elif option == "On-chain & Sentiment Analysis":
    st.title("On-chain & Sentiment Analysis")

    from onchain import get_onchain_metrics
    from sentiment import get_sentiment
    from scoring import calculate_signal

    df = pd.read_csv(MASTER_CSV)

    coin = st.selectbox(
        "Избери криптовалута",
        sorted(df["coin"].unique())
    )
    coin_id = coin.lower()

    with st.spinner("Fetching on-chain data..."):
        onchain = get_onchain_metrics(coin_id)

    with st.spinner("Analyzing sentiment..."):
        sentiment_score, sentiment_label = get_sentiment(coin)

    st.subheader("On-chain metrics")
    st.json(onchain)

    st.subheader("Sentiment analysis")
    st.metric("Sentiment Score", sentiment_score)
    st.metric("Sentiment Label", sentiment_label)

    st.subheader("Combined signal")
    final_score, signal = calculate_signal(onchain, sentiment_score)

    if signal == "BUY":
        st.success(f"BUY signal ({signal}) — Combined score: {final_score}")
    elif signal == "SELL":
        st.error(f"SELL signal ({signal}) — Combined score: {final_score}")
    else:
        st.warning(f"HOLD signal ({signal}) — Combined score: {final_score}")
