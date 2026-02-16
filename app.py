import streamlit as st
import yfinance as yf
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
import os
import platform
import datetime
import urllib.request

# --- 1. 字型設定 (改用 g0v 穩定連結) ---
def set_font():
    # 如果是 Windows (您的 Surface Pro)，直接用微軟正黑體
    if platform.system() == 'Windows':
        plt.rcParams['font.sans-serif'] = ['Microsoft JhengHei']
        plt.rcParams['axes.unicode_minus'] = False
    else:
        # 如果是 Linux (Streamlit Cloud)，下載 g0v 託管的 Noto Sans TC
        font_filename = "NotoSansTC-Regular.ttf"
        
        if not os.path.exists(font_filename):
            with st.spinner("正在下載中文字型檔 (使用 g0v 來源)..."):
                # 這是 g0v 專案的穩定連結，絕不會 404
                url = "https://raw.githubusercontent.com/g0v/ogp-commitments/main/NotoSansTC-Regular.ttf"
                try:
                    # 模擬瀏覽器下載，避免被擋
                    opener = urllib.request.build_opener()
                    opener.addheaders = [('User-agent', 'Mozilla/5.0')]
                    urllib.request.install_opener(opener)
                    urllib.request.urlretrieve(url, font_filename)
                except Exception as e:
                    st.error(f"字型下載失敗: {e}")
                    return

        # 強制加入字型檔
        try:
            fm.fontManager.addfont(font_filename)
            plt.rcParams['font.family'] = 'Noto Sans TC'
        except Exception as e:
            st.warning(f"字型載入異常: {e}")

    plt.rcParams['axes.unicode_minus'] = False

# 呼叫字型設定
set_font()

# --- 2. 網頁標題 ---
st.title("📈 亞當理論 - 趨勢預測神器")
st.write("輸入台股代號，自動生成亞當理論第二映像圖！")

# --- 3. 側邊欄輸入區 ---
st.sidebar.header("參數設定")
stock_input = st.sidebar.text_input("輸入台股代號 (例如 2330, 3653):", value="2330")

interval_option = st.sidebar.selectbox(
    "選擇週期",
    ("日線 (Daily)", "週線 (Weekly)", "月線 (Monthly)")
)

interval_map = {"日線 (Daily)": "1d", "週線 (Weekly)": "1wk", "月線 (Monthly)": "1mo"}
sel_interval = interval_map[interval_option]

# --- 4. 核心功能函數 ---
def get_stock_data(code_input, interval):
    code_input = str(code_input).strip()
    suffixes = ['.TW', '.TWO']
    
    period = '2y' if interval == '1d' else '5y'
    if interval == '1mo': period = '10y'
    
    # 優先嘗試使用者輸入的格式
    if code_input.upper().endswith('.TW') or code_input.upper().endswith('.TWO'):
        try:
            df = yf.download(code_input, period=period, interval=interval, progress=False)
            if not df.empty and len(df) > 30:
                return df, code_input
        except:
            pass
    else:
        # 自動嘗試上市或上櫃
        for suffix in suffixes:
            stock_id = f"{code_input}{suffix}"
            try:
                df = yf.download(stock_id, period=period, interval=interval, progress=False)
                if not df.empty and len(df) > 30:
                    return df, stock_id
            except:
                continue
    return None, None

# --- 5. 執行按鈕 ---
if st.sidebar.button("開始分析"):
    with st.spinner(f'正在分析 {stock_input} ...'):
        df, full_code = get_stock_data(stock_input, sel_interval)
        
        if df is None:
            st.error(f"找不到代號 {stock_input} 的資料。")
        else:
            if 'Close' in df.columns:
                if isinstance(df.columns, pd.MultiIndex):
                    close = df['Close'].iloc[:, 0]
                else:
                    close = df['Close']
            else:
                st.error("資料格式異常。")
                st.stop()
            
            # --- 亞當理論運算 ---
            current_price = close.iloc[-1]
            last_date = close.index[-1]
            lookback = 10 
            
            projection = []
            future_dates = []
            
            if sel_interval == '1d':
                delta = datetime.timedelta(days=1)
            elif sel_interval == '1wk':
                delta = datetime.timedelta(weeks=1)
            else:
                delta = datetime.timedelta(days=30)
                
            for i in range(1, lookback + 1):
                past_p = close.iloc[-i]
                proj_p = current_price + (current_price - past_p)
                projection.append(proj_p)
                future_dates.append(last_date + (delta * i))
                
            proj_series = pd.Series(projection, index=future_dates)
            
            ma50 = close.rolling(50).mean()
            ma100 = close.rolling(100).mean()

            # --- 6. 畫圖 ---
            fig, ax = plt.subplots(figsize=(10, 6))
            
            display_len = 120
            if len(close) > display_len:
                plot_data = close.iloc[-display_len:]
                plot_ma50 = ma50.iloc[-display_len:]
                plot_ma100 = ma100.iloc[-display_len:]
            else:
                plot_data = close
                plot_ma50 = ma50
                plot_ma100 = ma100

            ax.plot(plot_data.index, plot_data.values, label='歷史股價', color='black')
            ax.plot(plot_ma50.index, plot_ma50.values, label='50MA', color='blue', alpha=0.4)
            ax.plot(plot_ma100.index, plot_ma100.values, label='100MA', color='orange', alpha=0.4)
            ax.plot(proj_series.index, proj_series.values, label='亞當理論預測', color='red', linestyle='--', linewidth=2)
            
            ax.set_title(f"{full_code} - {interval_option} 亞當理論分析")
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            st.pyplot(fig)
            st.success(f"目前價格: {current_price:.2f}")
