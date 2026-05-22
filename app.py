import pandas as pd
import pandas_ta as ta
import requests
import streamlit as st
import yfinance as yf

# 💡 請在下方引號內置換為你專屬的 LINE 官方帳號密鑰與個人 ID
LINE_ACCESS_TOKEN = "e8hCJuWgIrFXgg3be6Ed4+oZ/7C7xhyRlTujHjMu4CIlym1n9IdALT6HWxJ4ZoY21XVoQl8ffm5yoRjdWYObJReFTA1P47xXZeqHjv0MEMxCuzUiPDnPluVR3ssT+LLeBC7NYPLyuqWv5ww/Xo5SHwdB04t89/1O/w1cDnyilFU="
LINE_USER_ID = "@175jasgf"

# 設定手機網頁最佳化排版
st.set_page_config(page_title="個人即時選股 App", layout="centered")
st.title("📊 我的即時選股與 LINE 助理")
st.write("已全面升級為 LINE Messaging API！盤中隨時微調條件，一鍵即時推播。")

# ----------------- 1. 手機/電腦介面：隨時微調篩選條件 -----------------
st.sidebar.header("⚙️ 篩選條件設定")
pe_limit = st.sidebar.slider(
    "本益比上限", min_value=5.0, max_value=40.0, value=15.0, step=1.0
)
yield_limit = st.sidebar.slider(
    "殖利率下限 (%)", min_value=0.0, max_value=15.0, value=5.0, step=0.5
)

st.sidebar.write("---")
need_ma = st.sidebar.checkbox("開啟 均線黃金交叉", value=True)
short_ma = st.sidebar.number_input(
    "短均線天數 (日線)", min_value=2, max_value=20, value=5
)
long_ma = st.sidebar.number_input(
    "長均線天數 (月線)", min_value=10, max_value=120, value=20
)

st.sidebar.write("---")
need_macd = st.sidebar.checkbox("開啟 MACD 黃金交叉", value=True)


# ----------------- 2. 核心技術大腦：盤中即時指標計算 -----------------
def check_technical_realtime(stock_id, need_ma, s_ma, l_ma, need_macd):
    ticker = f"{stock_id}.TW"
    try:
        df = yf.download(ticker, period="7d", interval="5m", progress=False)
        if df.empty or len(df) < max(30, l_ma):
            return False
        df = df.reset_index()

        df["Short_MA"] = ta.sma(df["Close"], length=s_ma)
        df["Long_MA"] = ta.sma(df["Close"], length=l_ma)

        macd_df = ta.macd(df["Close"], fast=12, slow=26, signal=9)
        if macd_df is not None:
            df = pd.concat([df, macd_df], axis=1)

        today = df.iloc[-1]
        yesterday = df.iloc[-2]

        ma_match = True
        macd_match = True

        if need_ma:
            ma_match = (yesterday["Short_MA"] <= yesterday["Long_MA"]) and (
                today["Short_MA"] > today["Long_MA"]
            )

        if need_macd:
            dif_col = [c for c in df.columns if "MACD_" in str(c)]
            macds_col = [c for c in df.columns if "MACDs_" in str(c)]
            macd_match = (yesterday[dif_col] <= yesterday[macds_col]) and (
                today[dif_col] > today[macds_col]
            )

        return ma_match and macd_match
    except:
        return False


# ----------------- 3. LINE 發送功能 -----------------
def send_line_message_via_bot(stocks, pe, dy, ma, s_ma, l_ma, macd):
    header_msg = f"📊 即時選股結果：\n(條件：PE<{pe} | 殖利率>{dy}%"
    if ma:
        header_msg += f" | {s_ma}MA>{l_ma}MA"
    if macd:
        header_msg += " | MACD交叉"
    header_msg += ")\n"

    if not stocks:
        message = header_msg + "❌ 目前盤中無符合全部條件的股票。"
    else:
        message = header_msg + f"🔥 符合條件股票共 {len(stocks)} 檔：\n"
        message += "=" * 20 + "\n"
        for stock in stocks[:20]:
            message += f"📈 {stock['股票代號']} {stock['股票名稱']}\n   PE: {stock['本益比']} | 殖利率: {stock['殖利率(%)']}%\n"
            message += "-" * 20 + "\n"

    url = "https://line.me"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_ACCESS_TOKEN}",
    }
    payload = {
        "to": LINE_USER_ID,
        "messages": [{"type": "text", "text": message.strip()}],
    }
    requests.post(url, headers=headers, json=payload)


# ----------------- 4. 按鈕互動 -----------------
if st.button("🚀 開始即時篩選並發送 LINE", use_container_width=True):
    with st.spinner("正在抓取並計算全台股即時資料，請稍候..."):
        url = "https://twse.com.tw"
        res = requests.get(url, timeout=10)

        if res.status_code == 200:
            stocks_data = res.json()
            final_list = []

            for stock in stocks_data:
                stock_id = stock.get("Code", "").strip()
                stock_name = stock.get("Name", "").strip()
                if len(stock_id) != 4:
                    continue

                try:
                    pe_val = (
                        float(stock.get("PEratio", "999"))
                        if stock.get("PEratio") != "-"
                        else 999.0
                    )
                    dy_val = (
                        float(stock.get("DividendYield", "0"))
                        if stock.get("DividendYield") != "-"
                        else 0.0
                    )

                    if pe_val < pe_limit and dy_val > yield_limit and pe_val > 0:
                        if need_ma or need_macd:
                            if check_technical_realtime(
                                stock_id, need_ma, short_ma, long_ma, need_macd
                            ):
                                final_list.append(
                                    {
                                        "股票代號": stock_id,
                                        "股票名稱": stock_name,
                                        "本益比": pe_val,
                                        "殖利率(%)": dy_val,
                                    }
                                )
                        else:
                            final_list.append(
                                {
                                    "股票代號": stock_id,
                                    "股票名稱": stock_name,
                                    "本益比": pe_val,
                                    "殖利率(%)": dy_val,
                                }
                            )
                except:
                    continue

            send_line_message_via_bot(
                final_list,
                pe_limit,
                yield_limit,
                need_ma,
                short_ma,
                long_ma,
                need_macd,
            )

            if final_list:
                st.success(
                    f"🎉 篩選完成！結果已發送。共 {len(final_list)} 檔："
                )
                result_df = pd.DataFrame(final_list)
                st.dataframe(result_df, use_container_width=True)
            else:
                st.info(
                    "目前盤中暫無符合全部條件的股票，LINE 已發送未達標通報。"
                )
        else:
            st.error("無法連線至證交所 API。")
