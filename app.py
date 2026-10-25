# ============================================================
# ⚠️ يجب أن تكون هذه الأسطر في أعلى الملف قبل أي استيراد
# ============================================================
import os

os.environ['HOME'] = '/tmp'
os.environ['XDG_CONFIG_HOME'] = '/tmp/.config'
os.environ['XDG_CACHE_HOME'] = '/tmp/.cache'

for _p in ['/tmp/.config', '/tmp/.cache', '/tmp/.local', '/tmp/.local/share']:
    os.makedirs(_p, exist_ok=True)

# ============================================================
# استيرادات المكتبات
# ============================================================
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import requests
from datetime import datetime, timedelta
from streamlit_js_eval import streamlit_js_eval
from pocketoptionapi.stable_api import PocketOption

# ============================================================
# 1. إعدادات الصفحة والتصميم
# ============================================================
st.set_page_config(page_title="Candle Bot PRO 3.0", page_icon="🕯️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    .stApp { background: radial-gradient(circle at top, #0A0E17 0%, #000000 100%); font-family: 'Cairo', sans-serif; }
    .main-header { font-size: 2.5rem; color: #00FFAA; text-align: center; font-weight: 900; text-shadow: 0 0 15px rgba(0, 255, 170, 0.5); margin-bottom: 0; }
    .sub-header { font-size: 1.1rem; color: #8899AA; text-align: center; margin-bottom: 2rem; letter-spacing: 2px; }
    .metric-card { background: linear-gradient(135deg, #121826 0%, #0A0E17 100%); border: 1px solid #1F2A3C; border-radius: 15px; padding: 1.2rem 0.5rem; text-align: center; box-shadow: 0 4px 20px rgba(0, 255, 170, 0.05); display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 120px; }
    .metric-label { color: #8899AA; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 700; }
    .metric-value { font-size: 1.3rem; font-weight: 900; white-space: nowrap; }
    .buy-signal { color: #00FFAA; text-shadow: 0 0 10px rgba(0,255,170,0.4); }
    .sell-signal { color: #FF3355; text-shadow: 0 0 10px rgba(255,51,85,0.4); }
    .neutral-signal { color: #FFCC00; }
    .countdown-box { background: linear-gradient(135deg, #1F2A3C 0%, #0A0E17 100%); border: 2px solid #00FFAA; border-radius: 15px; padding: 1.5rem; text-align: center; margin: 1rem 0; box-shadow: 0 0 20px rgba(0,255,170,0.3); }
    .countdown-time { font-size: 3rem; font-weight: 900; color: #00FFAA; text-shadow: 0 0 10px rgba(0,255,170,0.6); margin: 0; }
    .countdown-label { color: #8899AA; font-size: 1.1rem; margin-bottom: 0.5rem; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0A0E17 0%, #050810 100%); border-right: 1px solid #1F2A3C; }
    .stButton>button { background: linear-gradient(135deg, #00FFAA 0%, #00AA77 100%); color: #000; font-weight: 700; border: none; border-radius: 10px; padding: 0.6rem 1.5rem; width: 100%; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🕯️ Candle Bot PRO 3.0</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">20 PAIRS • COUNTDOWN • WIN RATE • AUDIO ALERTS</div>', unsafe_allow_html=True)

# ============================================================
# 2. بيانات الاعتماد
# ============================================================
SSID = '42["auth",{"session":"bchtvth5m3bmdovlva3i5t59nq","isDemo":1,"uid":136934681,"platform":2,"isFastHistory":true,"isOptimized":true}]'
TELEGRAM_TOKEN = "8531787721:AAH6dmi42q9BGw7rsdJYW7Ux3gfJj7iZ51E"
TELEGRAM_CHAT_ID = "8758991455"

# ✅ مسار قابل للكتابة على Streamlit Cloud
CSV_FILE = "/tmp/paper_trading_log.csv"

PAIRS = [
    "EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDUSD_otc", "USDCAD_otc",
    "USDCHF_otc", "NZDUSD_otc", "EURGBP_otc", "EURJPY_otc", "GBPJPY_otc",
    "AUDCAD_otc", "AUDJPY_otc", "CADJPY_otc", "CHFJPY_otc", "EURCAD_otc",
    "EURAUD_otc", "GBPAUD_otc", "GBPCAD_otc", "XAUUSD_otc", "BTCUSD_otc"
]

# ============================================================
# 3. الشريط الجانبي
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ الإعدادات")
    symbol = st.selectbox("الزوج / الأصل (20 زوج)", PAIRS)
    period = st.selectbox(
        "الإطار الزمني",
        [15, 30, 60, 180, 900],
        format_func=lambda x: {15: "15 ثانية", 30: "30 ثانية", 60: "دقيقة واحدة", 180: "3 دقائق", 900: "15 دقيقة"}[x],
        index=2
    )
    max_candles = 300

    st.markdown("---")
    st.markdown("### 🔔 الميزات")
    enable_telegram = st.checkbox("إشعارات تيليجرام", value=False)
    enable_sound = st.checkbox("تنبيه صوتي", value=True)
    enable_auto_refresh = st.checkbox("تحديث تلقائي (60 ث)", value=False)

    st.markdown("---")
    if st.button("🚀 مزامنة البيانات", use_container_width=True):
        st.session_state['run_scan'] = True
        st.session_state['trade_opened_time'] = None

    if st.button("🗑️ مسح الذاكرة", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ============================================================
# 4. دوال مساعدة
# ============================================================
def play_sound():
    if enable_sound:
        try:
            streamlit_js_eval(
                js_expressions="new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg').play()",
                key=f"sound_alert_{time.time()}"
            )
        except Exception:
            pass

def send_telegram_alert(message):
    if not enable_telegram or TELEGRAM_TOKEN == "ضع_التوكن_هنا":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except Exception:
        pass

def get_otc_data(symbol, period, max_candles):
    """
    جلب البيانات عبر PocketOptionAPI (متزامنة) مع إدارة آمنة للأخطاء.
    """
    api = None
    try:
        api = PocketOption(SSID, demo=True)
        connected = api.connect()
        if not connected:
            st.error("فشل الاتصال بـ PocketOption. تأكد من صلاحية SSID.")
            return None

        time.sleep(2)

        end_time = int(datetime.now().timestamp())
        start_time = end_time - (max_candles * period)

        df = api.get_history(
            symbol,
            period,
            start_time=start_time,
            end_time=end_time
        )

        if df is None or df.empty:
            st.error("لم تُرجع المكتبة أي شموع. تحقق من الزوج/الإطار.")
            return None

        df = df.copy()
        if 'time' in df.columns:
            df['time'] = pd.to_datetime(df['time'], unit='s', errors='coerce')
            if df['time'].isna().all():
                df['time'] = pd.to_datetime(df['time'], errors='coerce')

        df = df.sort_values('time').tail(max_candles).reset_index(drop=True)
        return df

    except Exception as e:
        st.error(f"خطأ في الاتصال أو جلب البيانات: {e}")
        return None
    finally:
        if api is not None:
            try:
                api.disconnect()
            except Exception:
                pass

# ============================================================
# 5. المؤشرات الفنية
# ============================================================
def calculate_indicators(df):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']

    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    return df

# ============================================================
# 6. كشف الأنماط
# ============================================================
def detect_patterns(df):
    patterns = []
    for i in range(3, len(df)):
        o, h, l, c = df.loc[i, ["open", "high", "low", "close"]].astype(float)
        po, pc = df.loc[i - 1, ["open", "close"]].astype(float)
        ppo, ppc = df.loc[i - 2, ["open", "close"]].astype(float)

        body = abs(c - o)
        range_ = h - l + 1e-9
        upper_wick = h - max(o, c)
        lower_wick = min(o, c) - l

        if body / range_ < 0.1:
            patterns.append((i, "Doji", "neutral"))
        elif lower_wick > 2 * body and upper_wick < body * 0.5:
            patterns.append((i, "Hammer", "buy"))
        elif upper_wick > 2 * body and lower_wick < body * 0.5:
            patterns.append((i, "Shooting Star", "sell"))
        elif pc < po and c > o and c > po and o < pc:
            patterns.append((i, "Bullish Engulfing", "buy"))
        elif pc > po and c < o and c < po and o > pc:
            patterns.append((i, "Bearish Engulfing", "sell"))
        elif (ppc < ppo) and (abs(pc - po) / (po + 1e-9) < 0.001) and (c > o) and (c > (ppo + ppc) / 2):
            patterns.append((i, "Morning Star", "buy"))
        elif (ppc > ppo) and (abs(pc - po) / (po + 1e-9) < 0.001) and (c < o) and (c < (ppo + ppc) / 2):
            patterns.append((i, "Evening Star", "sell"))
        elif (ppc < ppo) and (pc < po) and (c < o) and (c < pc) and (o < po):
            patterns.append((i, "Three Black Crows", "sell"))
        elif (ppc > ppo) and (pc > po) and (c > o) and (c > pc) and (o > po):
            patterns.append((i, "Three White Soldiers", "buy"))

    return patterns

# ============================================================
# 7. الرسم البياني
# ============================================================
def plot_chart(df, patterns, symbol):
    fig = make_subplots(
        rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
        row_heights=[0.6, 0.2, 0.2],
        subplot_titles=(f"{symbol}", "RSI (14)", "MACD")
    )

    fig.add_trace(go.Candlestick(
        x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00FFAA", increasing_fillcolor="#00FFAA",
        decreasing_line_color="#FF3355", decreasing_fillcolor="#FF3355", name="Price"
    ), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA200"], name="EMA 200",
                             line=dict(color="#FF8800", width=2)), row=1, col=1)

    for i, name, sig in patterns:
        color = {"buy": "#00FFAA", "sell": "#FF3355", "neutral": "#FFCC00"}[sig]
        y = df.loc[i, "high"] if sig != "buy" else df.loc[i, "low"]
        fig.add_trace(go.Scatter(
            x=[df.loc[i, "time"]], y=[y], mode="markers+text",
            text=[name.split()[0]], textposition="top center",
            marker=dict(symbol="star", size=12, color=color),
            textfont=dict(color=color, size=9), showlegend=False
        ), row=1, col=1)

    fig.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI",
                             line=dict(color="#FFCC00", width=2)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF3355", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00FFAA", row=2, col=1)

    fig.add_trace(go.Bar(x=df["time"], y=df["MACD_Hist"], name="MACD Hist",
                         marker_color=np.where(df["MACD_Hist"] > 0, "#00FFAA", "#FF3355")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD",
                             line=dict(color="#00AAFF", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["Signal_Line"], name="Signal",
                             line=dict(color="#FF8800", width=1.5)), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,14,23,0.6)",
        xaxis_rangeslider_visible=False, height=700, margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="Cairo", color="#CCCCCC"), hovermode="x unified", showlegend=False
    )
    fig.update_xaxes(gridcolor="#1F2A3C")
    fig.update_yaxes(gridcolor="#1F2A3C", side="right")
    return fig

# ============================================================
# 8. منطق الإشارة
# ============================================================
def generate_signal(patterns, df):
    buys = sum(1 for _, _, s in patterns if s == "buy")
    sells = sum(1 for _, _, s in patterns if s == "sell")

    last_rsi = df['RSI'].iloc[-1]
    last_macd_hist = df['MACD_Hist'].iloc[-1]
    last_close = df['close'].iloc[-1]
    last_ema = df['EMA200'].iloc[-1]

    if buys > sells and last_rsi < 70 and last_macd_hist > 0 and last_close > last_ema:
        return "STRONG BUY", buys, sells, "توافق كامل (أنماط + RSI + MACD + EMA)"
    elif sells > buys and last_rsi > 30 and last_macd_hist < 0 and last_close < last_ema:
        return "STRONG SELL", buys, sells, "توافق كامل (أنماط + RSI + MACD + EMA)"
    elif buys > sells:
        return "WEAK BUY", buys, sells, "أنماط فقط (بدون تأكيد المؤشرات/الاتجاه)"
    elif sells > buys:
        return "WEAK SELL", buys, sells, "أنماط فقط (بدون تأكيد المؤشرات/الاتجاه)"
    return "NEUTRAL", buys, sells, "لا توجد إشارة"

# ============================================================
# 9. سجل الصفقات والتقييم
# ============================================================
def log_trade(symbol, signal, entry_price, timeframe):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expiry_time = (datetime.now() + timedelta(seconds=timeframe)).strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{
        "Time": timestamp, "Symbol": symbol, "Signal": signal,
        "Entry": entry_price, "Expiry": expiry_time, "Result": "PENDING"
    }])
    if os.path.exists(CSV_FILE):
        new_data.to_csv(CSV_FILE, mode='a', header=False, index=False)
    else:
        new_data.to_csv(CSV_FILE, mode='w', header=True, index=False)

def evaluate_trades(current_price, current_symbol):
    if not os.path.exists(CSV_FILE):
        return
    df = pd.read_csv(CSV_FILE)
    updated = False
    now = datetime.now()

    for index, row in df.iterrows():
        if row['Result'] == 'PENDING' and row['Symbol'] == current_symbol:
            expiry = datetime.strptime(row['Expiry'], "%Y-%m-%d %H:%M:%S")
            if now >= expiry:
                if "BUY" in row['Signal']:
                    result = "WIN" if current_price > row['Entry'] else "LOSS"
                else:
                    result = "WIN" if current_price < row['Entry'] else "LOSS"
                df.at[index, 'Result'] = result
                updated = True

    if updated:
        df.to_csv(CSV_FILE, index=False)

# ============================================================
# 10. العرض الرئيسي
# ============================================================
if st.session_state.get('run_scan') or enable_auto_refresh:
    df = get_otc_data(symbol, period, max_candles)

    if df is not None and len(df) > 0:
        df = calculate_indicators(df)
        patterns = detect_patterns(df)
        signal, buys, sells, reason = generate_signal(patterns, df)
        current_price = df['close'].iloc[-1]

        evaluate_trades(current_price, symbol)

        last_signal = st.session_state.get('last_signal', None)
        trade_expired = st.session_state.get('trade_opened_time') is None
        if signal in ["STRONG BUY", "STRONG SELL"] and (signal != last_signal or trade_expired):
            if enable_telegram:
                msg = (
                    f"🚨 <b>{signal}</b> على {symbol}\n"
                    f"💰 السعر: {current_price:.5f}\n"
                    f"📊 RSI: {df['RSI'].iloc[-1]:.1f}\n"
                    f"📝 {reason}"
                )
                send_telegram_alert(msg)

            play_sound()
            log_trade(symbol, signal, current_price, period)
            st.session_state['last_signal'] = signal
            st.session_state['trade_opened_time'] = time.time()
            st.session_state['trade_signal'] = signal

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">السعر</div>'
                f'<div class="metric-value">{current_price:,.5f}</div></div>',
                unsafe_allow_html=True
            )
        with c2:
            rsi_val = df['RSI'].iloc[-1]
            cls = "sell-signal" if rsi_val > 70 else "buy-signal" if rsi_val < 30 else ""
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">RSI</div>'
                f'<div class="metric-value {cls}">{rsi_val:.1f}</div></div>',
                unsafe_allow_html=True
            )
        with c3:
            trend = "صاعد ↗" if current_price > df['EMA200'].iloc[-1] else "هابط ↘"
            t_cls = "buy-signal" if "صاعد" in trend else "sell-signal"
            st.markdown(
                f'<div class="metric-card"><div class="metric-label">الاتجاه (EMA)</div>'
                f'<div class="metric-value {t_cls}">{trend}</div></div>',
                unsafe_allow_html=True
            )
        with c4:
            if os.path.exists(CSV_FILE):
                log_df = pd.read_csv(CSV_FILE)
                wins = len(log_df[log_df['Result'] == 'WIN'])
                total = len(log_df[log_df['Result'].isin(['WIN', 'LOSS'])])
                win_rate = (wins / total * 100) if total > 0 else 0
                st.markdown(
                    f'<div class="metric-card"><div class="metric-label">نسبة النجاح</div>'
                    f'<div class="metric-value" style="color:#FFCC00">{win_rate:.0f}%</div></div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f'<div class="metric-card"><div class="metric-label">نسبة النجاح</div>'
                    f'<div class="metric-value">--</div></div>',
                    unsafe_allow_html=True
                )

        st.markdown("<br>", unsafe_allow_html=True)
        st.plotly_chart(plot_chart(df, patterns, symbol), use_container_width=True)

        sig_color = "buy-signal" if "BUY" in signal else "sell-signal" if "SELL" in signal else "neutral-signal"
        emoji = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "🟡"

        st.markdown(f"""
        <div class="metric-card" style="margin-bottom: 10px;">
            <div class="metric-label">الإشارة النهائية</div>
            <div class="metric-value {sig_color}" style="font-size: 1.8rem;">{emoji} {signal}</div>
            <div style="color:#8899AA; font-size:0.9rem;">{reason}</div>
        </div>
        """, unsafe_allow_html=True)

        if st.session_state.get('trade_opened_time') and signal in ["STRONG BUY", "STRONG SELL"]:
            elapsed = time.time() - st.session_state['trade_opened_time']
            remaining = int(period - elapsed)

            if remaining > 0:
                st.markdown(f"""
                <div class="countdown-box">
                    <div class="countdown-label">⏳ الوقت المتبقي لإغلاق الصفقة (ثانية)</div>
                    <div class="countdown-time">{remaining}</div>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.success("✅ انتهت مدة الصفقة! تم تقييمها في السجل.")
                st.session_state['trade_opened_time'] = None

        if os.path.exists(CSV_FILE):
            with st.expander("📊 سجل الصفقات (Paper Trading)"):
                log_df = pd.read_csv(CSV_FILE)
                st.dataframe(log_df.tail(15), use_container_width=True)

    else:
        st.error("فشل سحب البيانات. تحقق من SSID أو اتصال المكتبة.")

else:
    st.info("👈 اضغط **مزامنة البيانات** في الشريط الجانبي لبدء التحليل.")

if enable_auto_refresh:
    time.sleep(60)
    st.rerun()