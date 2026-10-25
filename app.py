import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
import asyncio
import requests
import os
from datetime import datetime
from pocketoptionapi_async import AsyncPocketOptionClient

# ============================================================
# 1. إعدادات الصفحة والتصميم (CSS المحسن)
# ============================================================
st.set_page_config(page_title="The Candle Bot PRO", page_icon="🕯️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    
    /* خلفية التطبيق */
    .stApp { 
        background: radial-gradient(circle at top, #0A0E17 0%, #000000 100%); 
        font-family: 'Cairo', sans-serif; 
    }
    
    /* العناوين */
    .main-header { 
        font-size: 2.5rem; color: #00FFAA; text-align: center; 
        font-weight: 900; text-shadow: 0 0 15px rgba(0, 255, 170, 0.5); margin-bottom: 0; 
    }
    .sub-header { 
        font-size: 1.1rem; color: #8899AA; text-align: center; 
        margin-bottom: 2rem; letter-spacing: 2px; 
    }
    
    /* البطاقات (Cards) */
    .metric-card { 
        background: linear-gradient(135deg, #121826 0%, #0A0E17 100%); 
        border: 1px solid #1F2A3C; border-radius: 15px; 
        padding: 1.2rem 0.5rem;
        text-align: center; 
        box-shadow: 0 4px 20px rgba(0, 255, 170, 0.05); 
        display: flex; flex-direction: column; justify-content: center; align-items: center;
        min-height: 120px;
    }
    
    /* النصوص داخل البطاقات */
    .metric-label { 
        color: #8899AA; font-size: 0.85rem; 
        margin-bottom: 0.5rem; font-weight: 700;
    }
    .metric-value { 
        font-size: 1.3rem; 
        font-weight: 900; 
        white-space: nowrap; 
        overflow: hidden; text-overflow: ellipsis; 
        width: 100%;
    }
    
    /* الألوان */
    .buy-signal { color: #00FFAA; text-shadow: 0 0 10px rgba(0,255,170,0.4); }
    .sell-signal { color: #FF3355; text-shadow: 0 0 10px rgba(255,51,85,0.4); }
    .neutral-signal { color: #FFCC00; }
    
    /* الشريط الجانبي */
    div[data-testid="stSidebar"] { 
        background: linear-gradient(180deg, #0A0E17 0%, #050810 100%); 
        border-right: 1px solid #1F2A3C; 
    }
    
    /* الأزرار */
    .stButton>button { 
        background: linear-gradient(135deg, #00FFAA 0%, #00AA77 100%); 
        color: #000; font-weight: 700; border: none; border-radius: 10px; 
        padding: 0.6rem 1.5rem; width: 100%;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 15px rgba(0, 255, 170, 0.6);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🕯️ The Candle Bot PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">AUTO-REFRESH • RSI/MACD • SIGNAL LOG • TELEGRAM</div>', unsafe_allow_html=True)

# ============================================================
# 2. بيانات الاعتماد (يجب تعديلها)
# ============================================================
# ⚠️ ضع الـ SSID الجديد هنا (السلسلة الكاملة التي تبدأ بـ 42["auth")
SSID = '42["auth",{"session":"bchtvth5m3bmdovlva3i5t59nq","isDemo":1,"uid":136934681,"platform":2,"isFastHistory":true,"isOptimized":true}]'
TELEGRAM_TOKEN = "8531787721:AAH6dmi42q9BGw7rsdJYW7Ux3gfJj7iZ51E"
TELEGRAM_CHAT_ID = "8758991455"

CSV_FILE = "signals_log.csv"

# ============================================================
# 3. الشريط الجانبي
# ============================================================
with st.sidebar:
    st.markdown("### ⚙️ الإعدادات")
    symbol = st.selectbox("الزوج / الأصل", ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDCAD_otc", "EURJPY_otc"])
    period = st.selectbox("الإطار الزمني (ثانية)", [60, 120, 300, 600], index=0)
    max_candles = st.slider("أقصى عدد شموع", 50, 500, 200)
    
    st.markdown("---")
    st.markdown("### 🔔 الإشعارات والتحديث")
    enable_telegram = st.checkbox("تفعيل إشعارات تيليجرام", value=False)
    enable_auto_refresh = st.checkbox("تحديث تلقائي (كل 60 ثانية)", value=False)
    
    st.markdown("---")
    if st.button("🚀 مزامنة البيانات والتحليل", use_container_width=True):
        st.session_state['run_scan'] = True
        
    if st.button("🗑️ مسح الكاش والاتصال", use_container_width=True):
        for key in ['api', 'df', 'run_scan', 'last_signal']:
            st.session_state.pop(key, None)
        st.rerun()

# ============================================================
# 4. إرسال إشعار تيليجرام
# ============================================================
def send_telegram_alert(message):
    if not enable_telegram or TELEGRAM_TOKEN == "8531787721:AAH6dmi42q9BGw7rsdJYW7Ux3gfJj7iZ51E":
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "HTML"}
    try:
        requests.post(url, json=payload, timeout=5)
    except:
        pass

# ============================================================
# 5. الاتصال وسحب البيانات
# ============================================================
async def fetch_data_async(symbol, period, max_candles):
    client = AsyncPocketOptionClient(SSID, is_demo=True)
    await client.connect()
    candles = await client.get_candles(asset=symbol, timeframe=period, count=max_candles)
    await client.disconnect()
    return candles

def get_otc_data(symbol, period, max_candles):
    try:
        candles = asyncio.run(fetch_data_async(symbol, period, max_candles))
        if not candles:
            return None
        data = [{'time': c.timestamp, 'open': c.open, 'high': c.high, 'low': c.low, 'close': c.close} for c in candles]
        df = pd.DataFrame(data)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df.tail(max_candles).reset_index(drop=True)
    except Exception as e:
        st.error(f"خطأ في الاتصال: {e}")
        return None

# ============================================================
# 6. المؤشرات الفنية (RSI & MACD)
# ============================================================
def calculate_rsi(df, period=14):
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    return df

def calculate_macd(df, fast=12, slow=26, signal=9):
    exp1 = df['close'].ewm(span=fast, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal_Line'] = df['MACD'].ewm(span=signal, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['Signal_Line']
    return df

# ============================================================
# 7. اكتشاف الأنماط
# ============================================================
def detect_patterns(df):
    patterns = []
    for i in range(2, len(df)):
        o, h, l, c = df.loc[i, ["open", "high", "low", "close"]].astype(float)
        po, pc = df.loc[i-1, ["open", "close"]].astype(float)
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
    return patterns

# ============================================================
# 8. الرسم البياني (مع المؤشرات)
# ============================================================
def plot_chart_with_indicators(df, patterns, symbol):
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, 
                        row_heights=[0.6, 0.2, 0.2],
                        subplot_titles=(f"{symbol} Price", "RSI (14)", "MACD (12,26,9)"))

    # 1. الشموع اليابانية
    fig.add_trace(go.Candlestick(
        x=df["time"], open=df["open"], high=df["high"], low=df["low"], close=df["close"],
        increasing_line_color="#00FFAA", increasing_fillcolor="#00FFAA",
        decreasing_line_color="#FF3355", decreasing_fillcolor="#FF3355",
        name="Price"
    ), row=1, col=1)

    # 2. علامات الأنماط
    for i, name, sig in patterns:
        color = {"buy": "#00FFAA", "sell": "#FF3355", "neutral": "#FFCC00"}[sig]
        y = df.loc[i, "high"] if sig != "buy" else df.loc[i, "low"]
        fig.add_trace(go.Scatter(
            x=[df.loc[i, "time"]], y=[y], mode="markers+text", text=[name.split()[0]],
            textposition="top center", marker=dict(symbol="star", size=12, color=color),
            textfont=dict(color=color, size=9), showlegend=False
        ), row=1, col=1)

    # 3. RSI
    fig.add_trace(go.Scatter(x=df["time"], y=df["RSI"], name="RSI", line=dict(color="#FFCC00", width=2)), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="#FF3355", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="#00FFAA", row=2, col=1)

    # 4. MACD
    fig.add_trace(go.Bar(x=df["time"], y=df["MACD_Hist"], name="MACD Hist", marker_color=np.where(df["MACD_Hist"] > 0, "#00FFAA", "#FF3355")), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["MACD"], name="MACD", line=dict(color="#00AAFF", width=1.5)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["time"], y=df["Signal_Line"], name="Signal", line=dict(color="#FF8800", width=1.5)), row=3, col=1)

    fig.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(10,14,23,0.6)",
        xaxis_rangeslider_visible=False, height=800, margin=dict(l=20, r=20, t=40, b=20),
        font=dict(family="Cairo", color="#CCCCCC"), hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(gridcolor="#1F2A3C")
    fig.update_yaxes(gridcolor="#1F2A3C", side="right")
    return fig

# ============================================================
# 9. حفظ الإشارات (Signal Log)
# ============================================================
def log_signal(symbol, signal, price, rsi):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_data = pd.DataFrame([{"Time": timestamp, "Symbol": symbol, "Signal": signal, "Price": price, "RSI": rsi}])
    if os.path.exists(CSV_FILE):
        new_data.to_csv(CSV_FILE, mode='a', header=False, index=False)
    else:
        new_data.to_csv(CSV_FILE, mode='w', header=True, index=False)

# ============================================================
# 10. الإشارة النهائية (مع تأكيد المؤشرات)
# ============================================================
def generate_final_signal(patterns, df):
    buys = sum(1 for _, _, s in patterns if s == "buy")
    sells = sum(1 for _, _, s in patterns if s == "sell")
    
    last_rsi = df['RSI'].iloc[-1] if not pd.isna(df['RSI'].iloc[-1]) else 50
    last_macd_hist = df['MACD_Hist'].iloc[-1] if not pd.isna(df['MACD_Hist'].iloc[-1]) else 0
    
    if buys > sells and last_rsi < 70 and last_macd_hist > 0:
        return "STRONG BUY", buys, sells, "أنماط شراء + RSI غير متشبع + MACD إيجابي"
    elif sells > buys and last_rsi > 30 and last_macd_hist < 0:
        return "STRONG SELL", buys, sells, "أنماط بيع + RSI غير متشبع + MACD سلبي"
    elif buys > sells:
        return "WEAK BUY", buys, sells, "أنماط شراء فقط (بدون تأكيد مؤشرات)"
    elif sells > buys:
        return "WEAK SELL", buys, sells, "أنماط بيع فقط (بدون تأكيد مؤشرات)"
    return "NEUTRAL", buys, sells, "لا توجد إشارة واضحة"

# ============================================================
# 11. العرض الرئيسي
# ============================================================
if st.session_state.get('run_scan') or enable_auto_refresh:
    with st.spinner("جاري سحب البيانات وتحليلها..."):
        df = get_otc_data(symbol, period, max_candles)
        
        if df is not None and len(df) > 0:
            df = calculate_rsi(df)
            df = calculate_macd(df)
            patterns = detect_patterns(df)
            signal, buys, sells, reason = generate_final_signal(patterns, df)
            
            last_signal = st.session_state.get('last_signal', None)
            if signal in ["STRONG BUY", "STRONG SELL"] and signal != last_signal:
                msg = f"🚨 <b>إشارة {signal}</b> على {symbol}\n💰 السعر: {df['close'].iloc[-1]:.5f}\n📊 RSI: {df['RSI'].iloc[-1]:.1f}\n📝 السبب: {reason}"
                send_telegram_alert(msg)
                log_signal(symbol, signal, df['close'].iloc[-1], df['RSI'].iloc[-1])
                st.session_state['last_signal'] = signal
            
            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last
            change = ((last["close"] - prev["close"]) / prev["close"]) * 100

            c1, c2, c3, c4 = st.columns(4)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="metric-label">السعر الحالي</div><div class="metric-value">{last["close"]:,.5f}</div></div>', unsafe_allow_html=True)
            with c2:
                cls = "buy-signal" if change >= 0 else "sell-signal"
                st.markdown(f'<div class="metric-card"><div class="metric-label">التغير</div><div class="metric-value {cls}">{change:+.2f}%</div></div>', unsafe_allow_html=True)
            with c3:
                rsi_val = last['RSI'] if not pd.isna(last['RSI']) else 0
                rsi_color = "sell-signal" if rsi_val > 70 else "buy-signal" if rsi_val < 30 else ""
                st.markdown(f'<div class="metric-card"><div class="metric-label">RSI (14)</div><div class="metric-value {rsi_color}">{rsi_val:.1f}</div></div>', unsafe_allow_html=True)
            with c4:
                st.markdown(f'<div class="metric-card"><div class="metric-label">الأصل</div><div class="metric-value" style="color:#00FFAA">{symbol}</div></div>', unsafe_allow_html=True)

            st.markdown("<br>", unsafe_allow_html=True)

            st.plotly_chart(plot_chart_with_indicators(df, patterns, symbol), use_container_width=True)

            signal_class = "buy-signal" if "BUY" in signal else "sell-signal" if "SELL" in signal else "neutral-signal"
            emoji = "🟢" if "BUY" in signal else "🔴" if "SELL" in signal else "🟡"
            strength = "قوية 💪" if "STRONG" in signal else "ضعيفة ⚠️" if "WEAK" in signal else ""

            st.markdown(f"""
            <div class="metric-card" style="margin-top:1rem;">
                <div class="metric-label">الإشارة النهائية ({strength})</div>
                <div class="metric-value {signal_class}">{emoji} {signal}</div>
                <div style="margin-top:0.5rem; color:#8899AA; font-size:0.9rem;">{reason}</div>
                <div style="margin-top:0.5rem; color:#8899AA; font-size:0.8rem;">
                    أنماط شراء: <b style="color:#00FFAA">{buys}</b> | أنماط بيع: <b style="color:#FF3355">{sells}</b>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if patterns:
                with st.expander("📋 الأنماط المكتشفة"):
                    pat_df = pd.DataFrame([{"الشمعة": i, "النمط": name, "الإشارة": sig.upper()} for i, name, sig in patterns])
                    st.dataframe(pat_df, use_container_width=True)
            
            if os.path.exists(CSV_FILE):
                with st.expander("📊 سجل الإشارات السابقة (Signal Log)"):
                    log_df = pd.read_csv(CSV_FILE)
                    st.dataframe(log_df.tail(20), use_container_width=True)

        else:
            st.error("فشل سحب البيانات. قد يكون SSID منتهي الصلاحية.")

else:
    st.info("👈 اضغط **مزامنة البيانات والتحليل** في الشريط الجانبي لبدء السحب.")

if enable_auto_refresh:
    time.sleep(60)
    st.rerun()
