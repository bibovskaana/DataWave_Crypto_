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

