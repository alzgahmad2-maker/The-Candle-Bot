import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import requests
import os
from datetime import datetime, timedelta
from streamlit_js_eval import streamlit_js_eval
from otcharts import Client
from io import BytesIO

# ============================================================
# 1. إعدادات الصفحة والتصميم (CSS) - ELZOGHEIR VIP
# ============================================================
st.set_page_config(page_title="ELZOGHEIR CANDLE-VIP", page_icon="👑", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    .stApp { background: radial-gradient(circle at top, #0A0E17 0%, #000000 100%); font-family: 'Cairo', sans-serif; }
    .main-header { font-size: 2.8rem; color: #FFD700; text-align: center; font-weight: 900; text-shadow: 0 0 20px rgba(255, 215, 0, 0.6); margin-bottom: 0; }
    .sub-header { font-size: 1.1rem; color: #8899AA; text-align: center; margin-bottom: 2rem; letter-spacing: 3px; }
    .metric-card { background: linear-gradient(135deg, #121826 0%, #0A0E17 100%); border: 1px solid #1F2A3C; border-radius: 15px; padding: 1rem 0.5rem; text-align: center; box-shadow: 0 4px 20px rgba(0, 255, 170, 0.05); display: flex; flex-direction: column; justify-content: center; align-items: center; min-height: 110px; }
    .metric-label { color: #8899AA; font-size: 0.85rem; margin-bottom: 0.5rem; font-weight: 700; }
    .metric-value { font-size: 1.3rem; font-weight: 900; white-space: nowrap; }
    .buy-signal { color: #00FFAA; text-shadow: 0 0 10px rgba(0,255,170,0.4); }
    .sell-signal { color: #FF3355; text-shadow: 0 0 10px rgba(255,51,85,0.4); }
    .neutral-signal { color: #FFCC00; }
    .countdown-box { background: linear-gradient(135deg, #1F2A3C 0%, #0A0E17 100%); border: 2px solid #FFD700; border-radius: 15px; padding: 1.5rem; text-align: center; margin: 1rem 0; box-shadow: 0 0 25px rgba(255,215,0,0.4); }
    .countdown-time { font-size: 3.5rem; font-weight: 900; color: #FFD700; text-shadow: 0 0 15px rgba(255,215,0,0.8); margin: 0; }
    .countdown-label { color: #8899AA; font-size: 1.1rem; margin-bottom: 0.5rem; }
    .warning-box { background: linear-gradient(135deg, #3C1F1F 0%, #0A0E17 100%); border: 2px solid #FF8800; border-radius: 15px; padding: 1.2rem; text-align: center; margin: 1rem 0; box-shadow: 0 0 25px rgba(255,136,0,0.5); }
    .warning-time { font-size: 2.5rem; font-weight: 900; color: #FF8800; text-shadow: 0 0 15px rgba(255,136,0,0.8); margin: 0; }
    div[data-testid="stSidebar"] { background: linear-gradient(180deg, #0A0E17 0%, #050810 100%); border-right: 1px solid #1F2A3C; }
    .stButton>button { background: linear-gradient(135deg, #FFD700 0%, #B8860B 100%); color: #000; font-weight: 700; border: none; border-radius: 10px; padding: 0.6rem 1.5rem; width: 100%; }
    .stButton>button:hover { box-shadow: 0 0 15px rgba(255, 215, 0, 0.6); transform: translateY(-2px); }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">👑 ELZOGHEIR CANDLE-VIP</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">ULTIMATE TRADING SYSTEM • LITE EDITION • 5 PAIRS</div>', unsafe_allow_html=True)

# ============================================================
# 2. بيانات الاعتماد والإعدادات
# ============================================================
os.environ["OTCHARTS_API_KEY"] = "otc_live_5d2b2cd7499551d584f44aa19cdd4f9e4bf695c366e17a8e6a2ac42b300bb7d3"

TELEGRAM_TOKEN = "8531787721:AAH6dmi42q9BGw7rsdJYW7Ux3gfJj7iZ51E"
TELEGRAM_CHAT_ID = "8758991455"
CSV_FILE = "elzogheir_vip_log.csv"

# 🔥 أفضل 5 أزواج لخطة OTCharts Lite (متوافقة مع Pocket Option)
PAIRS = [
    "EURUSD_otc",   # عائد ~92%
    "GBPUSD_otc",   # عائد ~77%
    "USDJPY_otc",   # عائد ~80%
    "AUDCAD_otc",   # عائد ~92%
    "EURGBP_otc",   # عائد ~62% (مفتوح افتراضيًا في OTCharts)
]

# ⏱️ مدة التحذير قبل الدخول (بالثواني)
ALERT_DELAY_SECONDS = 30

# 🌍 إزاحة توقيت دفتر Pocket Option (UTC+3)
POCKET_OPTION_TZ_OFFSET = 3

# ============================================================
# 3. الشريط الجانبي
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ إعدادات VIP (Lite)")
    symbol = st.selectbox("الزوج / الأصل (5 أزواج)", PAIRS)
    period = st.selectbox("الإطار الزمني",
        [15, 30, 60, 180, 300, 900, 1800],
        format_func=lambda x: {15: "15 ثانية", 30: "30 ثانية", 60: "دقيقة", 180: "3 دقائق", 300: "5 دقائق", 900: "15 دقيقة", 1800: "30 دقيقة"}[x],
        index=2
    )
    max_candles = 200

    st.markdown("---")
    st.markdown("### 🛡️ إدارة المخاطر")
    base_stake = st.number_input("حجم الدخول الأساسي ($)", min_value=1.0, value=1.0, step=1.0)
    martingale_mode = st.checkbox("تفعيل المضاعفة (Martingale)", value=False)

    st.markdown("---")
    st.markdown("### 🔔 الميزات")
    enable_telegram = st.checkbox("إشعارات تيليجرام", value=False)
    enable_sound = st.checkbox("تنبيه صوتي", value=True)
    enable_auto_refresh = st.checkbox("تحديث تلقائي (كل 5 ثوانٍ)", value=False)
    st.caption(f"⏱️ تأخير التحذير قبل الدخول: {ALERT_DELAY_SECONDS} ثانية")
    st.caption(f"🌍 توقيت Pocket Option: UTC+{POCKET_OPTION_TZ_OFFSET}")

    st.markdown("---")
    if st.button("🚀 مزامنة وتحليل", use_container_width=True):
        st.session_state['run_scan'] = True
        st.session_state['trade_opened_time'] = None
        st.session_state['pending_signal'] = None
        st.session_state['signal_detected_time'] = None
        st.session_state['alert_sent'] = False

    if st.button("🔍 مسح السوق (Scanner)", use_container_width=True):
        st.session_state['run_scanner'] = True

    if st.button("🗑️ مسح الذاكرة", use_container_width=True):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# ============================================================
# 4. دوال مساعدة
# ============================================================
def play_sound():
    if enable_sound:
        streamlit_js_eval(
            js_expressions="new Audio('https://actions.google.com/sounds/v1/alarms/beep_short.ogg').play()",
            key=f"sound_{time.time()}"
        )

def send_telegram_alert(message):
    if not enable_telegram or TELEGRAM_TOKEN == "ضع_التوكن_هنا":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

@st.cache_resource(show_spinner=False)
def get_otc_client():
    return Client()

def get_otc_data(symbol, period, max_candles):
    """جلب بيانات OTC من OTCharts مع التحقق الديناميكي من الرمز"""
    try:
        otc = get_otc_client()

        try:
            available = otc.symbols("otc")
            if symbol not in available:
                st.warning(f"⚠️ الرمز {symbol} غير متاح حاليًا.")
                return None
        except:
            pass

        df = otc.dataframe("otc", symbol, tf=period, limit=max_candles)

        if df is None or df.empty:
            return None

        time_col = None
        for candidate in ['time', 'timestamp', 'date', 'datetime']:
            if candidate in df.columns:
                time_col = candidate
                break

        if time_col is not None:
            if pd.api.types.is_numeric_dtype(df[time_col]):
                df['time'] = pd.to_datetime(df[time_col], unit='s')
            else:
                df['time'] = pd.to_datetime(df[time_col])
        else:
            df['time'] = pd.date_range(end=datetime.now(), periods=len(df), freq=f'{period}s')

        required = ['open', 'high', 'low', 'close']
        for col in required:
            if col not in df.columns:
                alt = [c for c in df.columns if c.lower() == col]
                if alt:
                    df[col] = df[alt[0]]
                else:
                    st.error(f"العمود '{col}' مفقود. الأعمدة المتاحة: {list(df.columns)}")
                    return None
            df[col] = pd.to_numeric(df[col], errors='coerce')

        df = df.dropna(subset=required)
        if df.empty:
            return None

        df = df[['time'] + required].copy()
        return df.tail(max_candles).reset_index(drop=True)

    except Exception as e:
        st.error(f"فشل جلب البيانات من OTCharts: {e}")
        return None

# ============================================================
# 5. المؤشرات والأنماط
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

def detect_patterns(df):
    patterns = []
    for i in range(3, len(df)):
        o, h, l, c = df.loc[i, ["open", "high", "low", "close"]].astype(float)
        po, pc = df.loc[i-1, ["open", "close"]].astype(float)
        ppo, ppc = df.loc[i-2, ["open", "close"]].astype(float)
        body = abs(c - o); range_ = h - l + 1e-9
        upper_wick = h - max(o, c); lower_wick = min(o, c) - l

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
        elif (ppc < ppo) and (abs(pc - po) / (po + 1e-9) < 0.001) and (c > o) and (c > (ppo + ppc)/2):
            patterns.append((i, "Morning Star", "buy"))
        elif (ppc > ppo) and (abs(pc - po) / (po + 1e-9) < 0.001) and (c < o) and (c < (ppo + ppc)/2):
            patterns.append((i, "Evening Star", "sell"))
    return patterns

# ============================================================
# 6. منطق الإشارة (مع فلترة الجلسات والاتجاه)
# ============================================================
def generate_signal(patterns, df, higher_tf_df):
    buys = sum(1 for _, _, s in patterns if s == "buy")
    sells = sum(1 for _, _, s in patterns if s == "sell")

    last_rsi = df['RSI'].iloc[-1]; last_macd = df['MACD_Hist'].iloc[-1]
    last_close = df['close'].iloc[-1]; last_ema = df['EMA200'].iloc[-1]

    # ✅ تصحيح التوقيت: دفتر Pocket Option يستخدم UTC+3
    current_hour = (datetime.utcnow() + timedelta(hours=POCKET_OPTION_TZ_OFFSET)).hour
    is_active_session = 7 <= current_hour <= 21

    higher_trend = "UP"
    if higher_tf_df is not None and len(higher_tf_df) > 0:
        higher_close = higher_tf_df['close'].iloc[-1]
        higher_ema = higher_tf_df['close'].ewm(span=200, adjust=False).mean().iloc[-1]
        higher_trend = "UP" if higher_close > higher_ema else "DOWN"

    reason = ""
    if not is_active_session:
        reason = "⚠️ جلسة غير نشطة"

    if buys > sells and last_rsi < 70 and last_macd > 0 and last_close > last_ema and higher_trend == "UP" and is_active_session:
        return "STRONG BUY", buys, sells, "توافق كامل (أنماط + RSI + MACD + EMA + إطار أكبر + جلسة)"
    elif sells > buys and last_rsi > 30 and last_macd < 0 and last_close < last_ema and higher_trend == "DOWN" and is_active_session:
        return "STRONG SELL", buys, sells, "توافق كامل (أنماط + RSI + MACD + EMA + إطار أكبر + جلسة)"
    elif buys > sells:
        return "WEAK BUY", buys, sells, f"أنماط شراء فقط ({reason if reason else 'بدون تأكيد'})"
    elif sells > buys:
        return "WEAK SELL", buys, sells, f"أنماط بيع فقط ({reason if reason else 'بدون تأكيد'})"
    return "NEUTRAL", buys, sells, "لا توجد إشارة"

# ============================================================
# 7. إدارة السجل والتحليلات
# ============================================================
def log_trade(symbol, signal, entry_price, timeframe, stake):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expiry_time = (datetime.now() + timedelta(seconds=timeframe)).strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{"Time": timestamp, "Symbol": symbol, "Signal": signal,
                              "Entry": entry_price, "Expiry": expiry_time,
                              "Stake": stake, "Result": "PENDING"}])
    if os.path.exists(CSV_FILE):
        new_data.to_csv(CSV_FILE, mode='a', header=False, index=False)
    else:
        new_data.to_csv(CSV_FILE, mode='w', header=True, index=False)

def evaluate_trades(current_price):
    if not os.path.exists(CSV_FILE):
        return
    df = pd.read_csv(CSV_FILE)
    updated = False
    now = datetime.now()
    for index, row in df.iterrows():
        if row['Result'] == 'PENDING':
            expiry = datetime.strptime(row['Expiry'], "%Y-%m-%d %H:%M:%S")
            if now >= expiry:
                result = "WIN" if ("BUY" in row['Signal'] and current_price > row['Entry']) or \
                                  ("SELL" in row['Signal'] and current_price < row['Entry']) else "LOSS"
                df.at[index, 'Result'] = result
                updated = True
    if updated:
        df.to_csv(CSV_FILE, index=False)

# ============================================================
# 8. الرسم البياني وتصدير الصورة
# ============================================================
def plot_chart(df, patterns, symbol):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, vertical_spacing=0.05,
                        row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"{symbol}", "RSI (14)", "MACD"))
    fig.add_trace(go.Candlestick(x=df["time"], open=df["open"], high=df["high"],
                                  low=df["low"], close=df["close"],
                                  increasing_line_color="#00FFAA", increasing_fillcolor="#00FFAA",
                                  decreasing_line_color="#FF3355", decreasing_fillcolor="#FF3355",
                                  name="Price"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["EMA200"], name="EMA 200",
                              line=dict(color="#FFD700", width=2)), row=1, col=1)

    for i, name, sig in patterns:
        color = {"buy": "#00FFAA", "sell": "#FF3355", "neutral": "#FFCC00"}[sig]
        y = df.loc[i, "high"] if sig != "buy" else df.loc[i, "low"]
        fig.add_trace(go.Scatter(x=[df.loc[i, "time"]], y=[y], mode="markers+text",
                                  text=[name.split()[0]], textposition="top center",
                                  marker=dict(symbol="star", size=12, color=color),
                                  textfont=dict(color=color, size=9), showlegend=False),
                      row=1, col=1)

    fig.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI",
                              line=dict(color="#FFCC00", width=2)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF3355", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00FFAA", row=2, col=1)

    fig.add_trace(go.Bar(x=df["time"], y=df["MACD_Hist"], name="MACD Hist",
                          marker_color=np.where(df["MACD_Hist"] > 0, "#00FFAA", "#FF3355")),
                  row=3, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD",
                              line=dict(color="#00AAFF", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["Signal_Line"], name="Signal",
                              line=dict(color="#FF8800", width=1.5)), row=3, col=1)

    fig.update_layout(template="plotly_dark",
                      paper_bgcolor="rgba(0,0,0,0)",
                      plot_bgcolor="rgba(10,14,23,0.6)",
                      xaxis_rangeslider_visible=False, height=700,
                      margin=dict(l=20, r=20, t=40, b=20),
                      font=dict(family="Cairo", color="#CCCCCC"),
                      hovermode="x unified", showlegend=False)
    fig.update_xaxes(gridcolor="#1F2A3C")
    fig.update_yaxes(gridcolor="#1F2A3C", side="right")
    return fig

def export_chart_image(fig, symbol):
    try:
        img_bytes = fig.to_image(format="png", width=1200, height=700, scale=2)
        st.download_button(
            label="📥 تحميل الرسم البياني كصورة (PNG)",
            data=img_bytes,
            file_name=f"{symbol}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png",
            mime="image/png",
            use_container_width=True
        )
    except:
        st.info("لتحميل الصورة، ثبّت kaleido: py -m pip install kaleido")

# ============================================================
# 9. العرض الرئيسي
# ============================================================
if st.session_state.get('run_scan') or enable_auto_refresh:
    df = get_otc_data(symbol, period, max_candles)

    if df is not None and len(df) > 0:
        df = calculate_indicators(df)

        higher_tf = 300 if period < 300 else 900
        higher_df = get_otc_data(symbol, higher_tf, 50)
        if higher_df is not None:
            higher_df = calculate_indicators(higher_df)

        patterns = detect_patterns(df)
        signal, buys, sells, reason = generate_signal(patterns, df, higher_df)
        current_price = df['close'].iloc[-1]

        evaluate_trades(current_price)

        current_stake = base_stake
        if os.path.exists(CSV_FILE) and martingale_mode:
            log_df = pd.read_csv(CSV_FILE)
            completed = log_df[log_df['Result'].isin(['WIN', 'LOSS'])]
            if len(completed) > 0:
                last_result = completed.iloc[-1]['Result']
                last_stake = completed.iloc[-1]['Stake']
                if last_result == 'LOSS':
                    current_stake = last_stake * 2

        # ============================================================
        # 🔔 منطق الإشارة مع التحذير المسبق (30 ثانية)
        # ============================================================
        last_signal = st.session_state.get('last_signal', None)

        # 1) اكتشاف إشارة قوية جديدة
        if signal in ["STRONG BUY", "STRONG SELL"] and signal != last_signal:
            if st.session_state.get('pending_signal') != signal:
                st.session_state['signal_detected_time'] = time.time()
                st.session_state['pending_signal'] = signal
                st.session_state['pending_price'] = current_price
                st.session_state['pending_stake'] = current_stake
                st.session_state['alert_sent'] = False

                msg = (
                    f"⚠️ <b>تحذير مسبق — دخول بعد {ALERT_DELAY_SECONDS} ثانية</b>\n"
                    f"💰 الزوج: {symbol}\n"
                    f"📊 الإشارة: {signal}\n"
                    f"💵 السعر المتوقع: {current_price:.5f}\n"
                    f"💸 حجم الدخول المتوقع: ${current_stake}\n"
                    f"📝 {reason}\n"
                    f"⏳ يرجى الاستعداد للدخول!"
                )
                if enable_telegram:
                    send_telegram_alert(msg)
                play_sound()
                st.session_state['alert_sent'] = True

        # 2) عرض العداد التنازلي + تنفيذ الدخول
        if st.session_state.get('pending_signal') == signal:
            elapsed = time.time() - st.session_state.get('signal_detected_time', time.time())
            remaining = int(ALERT_DELAY_SECONDS - elapsed)

            if remaining > 0:
                st.markdown(f"""
                <div class="warning-box">
                    <div class="countdown-label">⚠️ تحذير: الدخول خلال {remaining} ثانية</div>
                    <div class="warning-time">{remaining}</div>
                    <div style="color:#FFD700; margin-top:8px; font-size:1rem;">
                        الإشارة: <b>{signal}</b> — الزوج: <b>{symbol}</b>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                actual_entry_price = df['close'].iloc[-1]
                final_stake = st.session_state.get('pending_stake', current_stake)

                msg = (
                    f"👑 <b>ELZOGHEIR VIP: تنفيذ {signal}</b>\n"
                    f"💰 {symbol}\n"
                    f"💵 سعر الدخول: {actual_entry_price:.5f}\n"
                    f"💸 حجم الدخول: ${final_stake}\n"
                    f"📝 {reason}"
                )
                if enable_telegram:
                    send_telegram_alert(msg)
                play_sound()

                log_trade(symbol, signal, actual_entry_price, period, final_stake)
                st.session_state['last_signal'] = signal
                st.session_state['trade_opened_time'] = time.time()
                st.session_state['active_stake'] = final_stake

                st.session_state['pending_signal'] = None
                st.session_state['signal_detected_time'] = None
                st.session_state['alert_sent'] = False

                st.rerun()

        # ============================================================
        # عرض البطاقات
        # ============================================================
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f'<div class="metric-card"><div class="metric-label">السعر</div>'
                        f'<div class="metric-value">{current_price:,.5f}</div></div>',
                        unsafe_allow_html=True)
        with c2:
            rsi_val = df['RSI'].iloc[-1]
            cls = "sell-signal" if rsi_val > 70 else "buy-signal" if rsi_val < 30 else ""
            st.markdown(f'<div class="metric-card"><div class="metric-label">RSI</div>'
                        f'<div class="metric-value {cls}">{rsi_val:.1f}</div></div>',
                        unsafe_allow_html=True)
        with c3:
            trend = "صاعد ↗" if current_price > df['EMA200'].iloc[-1] else "هابط ↘"
            t_cls = "buy-signal" if "صاعد" in trend else "sell-signal"
            st.markdown(f'<div class="metric-card"><div class="metric-label">الاتجاه</div>'
                        f'<div class="metric-value {t_cls}">{trend}</div></div>',
                        unsafe_allow_html=True)
        with c4:
            st.markdown(f'<div class="metric-card"><div class="metric-label">حجم الدخول</div>'
                        f'<div class="metric-value" style="color:#FFD700">${current_stake}</div></div>',
                        unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        fig = plot_chart(df, patterns, symbol)
        st.plotly_chart(fig, use_container_width=True)
        export_chart_image(fig, symbol)

        sig_color = "buy-signal" if "BUY" in signal else "sell-signal" if "SELL" in signal else "neutral-signal"
        emoji = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "🟡"
        st.markdown(f"""
        <div class="metric-card" style="margin-bottom: 10px; border-color: #FFD700;">
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
                    <div class="countdown-label">⏳ الوقت المتبقي لإغلاق صفقة {symbol} (ثانية)</div>
                    <div class="countdown-time">{remaining}</div>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(1)
                st.rerun()
            else:
                st.success("✅ انتهت مدة الصفقة! تم تقييمها في السجل.")
                st.session_state['trade_opened_time'] = None

        if os.path.exists(CSV_FILE):
            log_df = pd.read_csv(CSV_FILE)
            with st.expander("📊 لوحة التحليلات وإدارة رأس المال"):
                col1, col2 = st.columns(2)
                with col1:
                    wins = len(log_df[log_df['Result'] == 'WIN'])
                    losses = len(log_df[log_df['Result'] == 'LOSS'])
                    if wins + losses > 0:
                        pie_fig = go.Figure(data=[go.Pie(labels=['Wins', 'Losses'],
                                                          values=[wins, losses], hole=.4,
                                                          marker_colors=['#00FFAA', '#FF3355'])])
                        pie_fig.update_layout(template="plotly_dark",
                                              paper_bgcolor="rgba(0,0,0,0)",
                                              height=300, margin=dict(t=10, b=10))
                        st.plotly_chart(pie_fig, use_container_width=True)
                with col2:
                    st.markdown("### أفضل الأزواج (Top Pairs)")
                    completed = log_df[log_df['Result'].isin(['WIN', 'LOSS'])]
                    if len(completed) > 0:
                        pair_stats = completed.groupby('Symbol')['Result'].value_counts().unstack(fill_value=0)
                        st.dataframe(pair_stats, use_container_width=True)
                    st.download_button("📥 تحميل السجل (CSV)",
                                       log_df.to_csv(index=False).encode('utf-8'),
                                       "elzogheir_log.csv", "text/csv",
                                       use_container_width=True)

# مسح السوق (Scanner)
if st.session_state.get('run_scanner'):
    st.markdown("### 🔍 نتائج مسح السوق (Scanner)")
    with st.spinner("جاري فحص الأزواج الخمسة..."):
        results = []
        for p in PAIRS:
            d = get_otc_data(p, 60, 100)
            if d is not None:
                d = calculate_indicators(d)
                pats = detect_patterns(d)
                sig, _, _, _ = generate_signal(pats, d, None)
                results.append({"الزوج": p, "الإشارة": sig, "السعر": f"{d['close'].iloc[-1]:.5f}"})
        if results:
            st.table(pd.DataFrame(results))
        else:
            st.warning("لم يتمكن الماسح من جلب البيانات. تحقق من الاتصال بـ OTCharts.")

else:
    st.info("👈 اضغط **مزامنة وتحليل** في الشريط الجانبي لبدء التحليل.")

if enable_auto_refresh:
    time.sleep(5)
    st.rerun()
