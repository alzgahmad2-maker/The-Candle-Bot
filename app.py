import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pyalbedo
from pyalbedo import MarketDataWindow
from pyalbedo.signals import MACrossover, RSIMeanReversion, SignalAggregator
import matplotlib.pyplot as plt
from io import BytesIO
import time
import plotly.graph_objects as go

# --- 1. إعدادات الصفحة والتصميم الفاخر ---
st.set_page_config(page_title="The Candle Bot | Premium", page_icon="🕯️", layout="centered")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    
    /* إخفاء القوائم المزعجة فقط، مع الإبقاء على شريط الأدوات */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* الخلفية العامة والتخطيط */
    .stApp { 
        background: radial-gradient(circle at top, #1A1F2B 0%, #0E1117 100%);
        font-family: 'Cairo', sans-serif;
    }
    
    /* العنوان الرئيسي */
    .main-header { 
        font-size: 2.8rem; color: #FFD700; text-align: center; 
        font-weight: 900; margin-bottom: 0px; margin-top: -30px;
        text-shadow: 0 0 15px rgba(255, 215, 0, 0.4); 
    }
    .sub-header {
        text-align: center; color: #A0AAB5; font-size: 1rem; margin-bottom: 20px;
    }

    /* تصميم صناديق الإشارات */
    .signal-box { 
        padding: 25px; border-radius: 20px; text-align: center; 
        font-size: 2.2rem; font-weight: 900; margin: 20px 0; 
        backdrop-filter: blur(10px); -webkit-backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px 0 rgba(0,0,0,0.5);
        animation: fade-in 0.5s ease-out;
    }
    .signal-call { background: rgba(56, 239, 125, 0.1); color: #38ef7d; border-left: 5px solid #38ef7d; box-shadow: 0 0 20px rgba(56, 239, 125, 0.2); }
    .signal-put { background: rgba(239, 71, 58, 0.1); color: #ef473a; border-left: 5px solid #ef473a; box-shadow: 0 0 20px rgba(239, 71, 58, 0.2); }
    .signal-neutral { background: rgba(117, 127, 154, 0.1); color: #A0AAB5; border-left: 5px solid #A0AAB5; }

    /* تصميم أزرار Streamlit */
    .stButton>button { 
        background: linear-gradient(135deg, #FFD700, #FF8C00); 
        color: #000; font-weight: 900; font-size: 1.2rem; 
        border: none; border-radius: 12px; padding: 12px 24px;
        transition: all 0.3s ease; width: 100%; margin-top: 10px;
        box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3);
    }
    .stButton>button:hover { transform: translateY(-2px); box-shadow: 0 6px 20px rgba(255, 215, 0, 0.5); }

    /* بطاقات الإحصائيات */
    .stat-card {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.05);
        border-radius: 15px; padding: 15px; text-align: center; margin-bottom: 10px;
    }
    
    @keyframes fade-in {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }
</style>
""", unsafe_allow_html=True)

def play_sound():
    st.markdown("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3" type="audio/mpeg"></audio>""", unsafe_allow_html=True)

# --- 2. الواجهة الرئيسية ---
st.markdown('<h1 class="main-header">🕯️ The Candle Bot</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">منصة الإشارات الذكية - النسخة الاحترافية</p>', unsafe_allow_html=True)

# وضع الإعدادات في منتصف الشاشة (أفضل للهاتف)
col1, col2 = st.columns(2)
with col1:
    symbols_map = {
        "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
        "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "EUR/GBP": "EURGBP=X",
        "XAU/USD (ذهب)": "GC=F", "BTC/USD (بيتكوين)": "BTC-USD"
    }
    selected_symbol_name = st.selectbox("الزوج", list(symbols_map.keys()))
    yf_symbol = symbols_map[selected_symbol_name]

with col2:
    timeframes = {"1 دقيقة": "1m", "3 دقائق": "3m", "5 دقائق": "5m", "15 دقيقة": "15m"}
    selected_tf_name = st.selectbox("الفريم", list(timeframes.keys()))
    selected_tf = timeframes[selected_tf_name]

search_button = st.button("🔍 بحث عن صفقة الآن")

# --- 3. الدوال الأساسية ---
@st.cache_data(ttl=30)
def fetch_candles(symbol, tf):
    period = "7d" if tf in ["1m", "3m"] else "60d"
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1m" if tf == "3m" else tf)
        if df.empty: return None
        df = df.reset_index()
        df = df.rename(columns={'Datetime': 'time', 'Date': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        if tf == "3m":
            df = df.set_index('time')
            df = df.resample('3T').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
            df = df.reset_index()
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)
        return df.tail(1000)
    except Exception:
        return None

def generate_advanced_signal(df, symbol):
    if df is None or len(df) < 50: return "NEUTRAL", "بيانات غير كافية", 0
    try:
        window = MarketDataWindow.from_arrays(
            symbol=symbol, open_=df['open'].values, high=df['high'].values,
            low=df['low'].values, close=df['close'].values, volume=df['volume'].values,
        )
        ma_cross = MACrossover(fast_period=5, slow_period=13) 
        rsi_reversion = RSIMeanReversion(period=14, oversold=40, overbought=60) 
        aggregator = SignalAggregator([ma_cross, rsi_reversion])
        bundle = aggregator.generate(window)

        if bundle and bundle.signals:
            strongest = max(bundle.signals, key=lambda s: s.strength)
            is_bullish = "bullish" in str(strongest.direction).lower() or "long" in str(strongest.direction).lower()
            direction = "CALL" if is_bullish else "PUT"
            confidence = min(int((strongest.strength + 0.3) * 100), 95)
            return direction, f"إشارة من ({strongest.source})", confidence
        else:
            close_prices = df['close']
            ema_5 = close_prices.ewm(span=5, adjust=False).mean()
            ema_13 = close_prices.ewm(span=13, adjust=False).mean()
            if ema_5.iloc[-1] > ema_13.iloc[-1]: return "CALL", "اتجاه سريع (صاعد)", 60
            else: return "PUT", "اتجاه سريع (هابط)", 60
    except Exception:
        return "NEUTRAL", "خطأ في التحليل", 0

def create_report_image(df_history):
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#0E1117')
    ax.axis('tight'); ax.axis('off')
    table_data = [df_history.columns.tolist()] + df_history.values.tolist()
    table = ax.table(cellText=table_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False); table.set_fontsize(12); table.scale(1, 2)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#333')
        if row == 0:
            cell.set_facecolor('#B8860B'); cell.set_text_props(color='white', weight='bold')
        else:
            cell.set_facecolor('#1A1F2B'); cell.set_text_props(color='#FFD700')
    plt.title("The Candle Bot - Premium Report", color='#FFD700', fontsize=18, weight='bold', pad=20)
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', facecolor='#0E1117')
    buf.seek(0); plt.close()
    return buf

# --- 4. تنفيذ البحث ---
if search_button:
    play_sound()
    with st.spinner("جاري تحليل السوق..."):
        df = fetch_candles(yf_symbol, selected_tf)
    
    if df is not None:
        signal, reason, confidence = generate_advanced_signal(df, yf_symbol)
        
        if "CALL" in signal:
            st.markdown(f'<div class="signal-box signal-call">🚀 CALL<br><span style="font-size: 1.2rem; color: #fff;">ثقة {confidence}%</span></div>', unsafe_allow_html=True)
        elif "PUT" in signal:
            st.markdown(f'<div class="signal-box signal-put">🔻 PUT<br><span style="font-size: 1.2rem; color: #fff;">ثقة {confidence}%</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="signal-box signal-neutral">⚖️ NEUTRAL</div>', unsafe_allow_html=True)
        
        st.markdown(f'<div class="stat-card"><h4 style="color: #A0AAB5; margin: 0;">التحليل الفني</h4><p style="color: #fff; font-size: 1.1rem; margin: 5px 0;">{reason}</p></div>', unsafe_allow_html=True)
        
        # الرسم البياني
        st.markdown("<h4 style='color: #FFD700;'>📊 حركة السعر</h4>", unsafe_allow_html=True)
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#38ef7d', decreasing_line_color='#ef473a'
        )])
        fig.update_layout(
            template='plotly_dark', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
            xaxis_rangeslider_visible=False, height=300, margin=dict(l=0, r=0, t=10, b=0),
            xaxis=dict(showgrid=False), yaxis=dict(showgrid=True, gridcolor='rgba(255,255,255,0.05)')
        )
        st.plotly_chart(fig, use_container_width=True)
        
        if 'trade_history' not in st.session_state: st.session_state.trade_history = []
        if "NEUTRAL" not in signal:
            st.session_state.trade_history.append({
                "الزوج": selected_symbol_name, "الفريم": selected_tf_name,
                "الإشارة": signal, "الثقة": f"{confidence}%", "الوقت": pd.Timestamp.now().strftime("%H:%M")
            })

# --- 5. السجل والإحصائيات (في منتصف الشاشة) ---
st.markdown("---")
st.markdown("<h3 style='color: #FFD700; text-align: center;'>📈 سجل الصفقات</h3>", unsafe_allow_html=True)

if 'trade_history' in st.session_state and st.session_state.trade_history:
    df_history = pd.DataFrame(st.session_state.trade_history)
    total = len(df_history)
    calls = len(df_history[df_history['الإشارة'] == 'CALL'])
    puts = len(df_history[df_history['الإشارة'] == 'PUT'])
    
    c1, c2, c3 = st.columns(3)
    with c1: st.markdown(f'<div class="stat-card"><p style="margin: 0; color: #A0AAB5; font-size: 0.9rem;">الإجمالي</p><h3 style="margin: 0; color: #fff;">{total}</h3></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-card" style="border-bottom: 3px solid #38ef7d;"><p style="margin: 0; color: #A0AAB5; font-size: 0.9rem;">CALL</p><h3 style="margin: 0; color: #38ef7d;">{calls}</h3></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-card" style="border-bottom: 3px solid #ef473a;"><p style="margin: 0; color: #A0AAB5; font-size: 0.9rem;">PUT</p><h3 style="margin: 0; color: #ef473a;">{puts}</h3></div>', unsafe_allow_html=True)
    
    if st.button("📸 تحميل التقرير كصورة", use_container_width=True):
        img_buf = create_report_image(df_history.tail(8))
        st.download_button("⬇️ اضغط هنا للحفظ", data=img_buf, file_name="Candle_Report.png", mime="image/png", use_container_width=True)
else:
    st.info("لا توجد إشارات مسجلة حتى الآن. اضغط على زر البحث للبدء.")