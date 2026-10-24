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

# --- 1. إعدادات الصفحة والتصميم الاحترافي ---
st.set_page_config(page_title="The Candle Bot | Premium", page_icon="🕯️", layout="wide")

st.markdown("""
<style>
    /* خلفية وتصميم عام */
    .stApp { background: linear-gradient(180deg, #0E1117 0%, #1A1F2B 100%); }
    
    /* عنوان متوهج */
    .main-header { 
        font-size: 3.5rem; color: #FFD700; text-align: center; 
        font-family: 'Arial', sans-serif; font-weight: 900;
        text-shadow: 0 0 10px #FFD700, 0 0 20px #FF8C00, 0 0 30px #FF8C00; 
    }
    
    /* صندوق الإشارة */
    .signal-box { 
        padding: 30px; border-radius: 15px; text-align: center; 
        font-size: 2.8rem; font-weight: bold; margin: 20px 0; 
        box-shadow: 0 8px 32px 0 rgba(0,0,0,0.37);
        backdrop-filter: blur(4px); border: 1px solid rgba(255, 255, 255, 0.18);
        animation: pulse 2s infinite;
    }
    .signal-call { background: rgba(17, 153, 142, 0.8); color: white; border-left: 10px solid #38ef7d; }
    .signal-put { background: rgba(203, 45, 62, 0.8); color: white; border-left: 10px solid #ef473a; }
    .signal-neutral { background: rgba(117, 127, 154, 0.8); color: white; border-left: 10px solid #D7DDE8; }
    
    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 215, 0, 0.7); }
        70% { transform: scale(1.02); box-shadow: 0 0 0 15px rgba(255, 215, 0, 0); }
        100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(255, 215, 0, 0); }
    }

    /* زر البحث */
    .stButton>button { 
        background: linear-gradient(135deg, #FFD700, #FF8C00); 
        color: black; font-weight: 900; font-size: 1.3rem; 
        border: none; border-radius: 10px; padding: 15px 30px;
        transition: all 0.3s ease; width: 100%;
    }
    .stButton>button:hover { transform: translateY(-3px); box-shadow: 0px 10px 20px rgba(255, 215, 0, 0.4); }
</style>
""", unsafe_allow_html=True)

# تأثير صوتي احترافي
def play_sound():
    audio_html = """
    <audio autoplay>
        <source src="https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3" type="audio/mpeg">
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

# --- 2. الشريط الجانبي (المدخلات) ---
st.sidebar.markdown("<h2 style='text-align: center; color: #FFD700;'>⚙️ لوحة التحكم</h2>", unsafe_allow_html=True)

symbols_map = {
    "EUR/USD": "EURUSD=X", "GBP/USD": "GBPUSD=X", "USD/JPY": "USDJPY=X",
    "AUD/USD": "AUDUSD=X", "USD/CAD": "USDCAD=X", "EUR/GBP": "EURGBP=X",
    "XAU/USD (الذهب)": "GC=F", "BTC/USD (بيتكوين)": "BTC-USD"
}
selected_symbol_name = st.sidebar.selectbox("اختر زوج العملات", list(symbols_map.keys()))
yf_symbol = symbols_map[selected_symbol_name]

timeframes = {"1 دقيقة": "1m", "3 دقائق": "3m", "5 دقائق": "5m", "15 دقيقة": "15m"}
selected_tf_name = st.sidebar.radio("اختر الفريم الزمني", list(timeframes.keys()))
selected_tf = timeframes[selected_tf_name]

st.sidebar.markdown("---")
search_button = st.sidebar.button("🔍 بحث عن صفقة")

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
    except Exception as e:
        return None

def generate_advanced_signal(df, symbol):
    """نظام إشارات متعدد المؤشرات (AI Simulation)"""
    if df is None or len(df) < 50:
        return "NEUTRAL", "بيانات غير كافية", 0

    try:
        window = MarketDataWindow.from_arrays(
            symbol=symbol, open_=df['open'].values, high=df['high'].values,
            low=df['low'].values, close=df['close'].values, volume=df['volume'].values,
        )
        
        # دمج 3 استراتيجيات مختلفة
        ma_cross = MACrossover(fast_period=9, slow_period=21) # سريع للفريمات الصغيرة
        rsi_reversion = RSIMeanReversion(period=14, oversold=30, overbought=70)
        
        aggregator = SignalAggregator([ma_cross, rsi_reversion])
        bundle = aggregator.generate(window)

        # خوارزمية لزيادة الثقة (Trend + Momentum)
        close_prices = df['close']
        ema_50 = close_prices.ewm(span=50, adjust=False).mean()
        trend = "UP" if close_prices.iloc[-1] > ema_50.iloc[-1] else "DOWN"

        if bundle and bundle.signals:
            strongest = max(bundle.signals, key=lambda s: s.strength)
            
            # دمج الاتجاه العام مع الإشارة
            is_bullish = "bullish" in str(strongest.direction).lower() or "long" in str(strongest.direction).lower()
            
            if is_bullish and trend == "UP":
                direction = "CALL (صعود)"
                confidence = min(int((strongest.strength + 0.2) * 100), 99) # مكافأة ثقة للتوافق
            elif not is_bullish and trend == "DOWN":
                direction = "PUT (هبوط)"
                confidence = min(int((strongest.strength + 0.2) * 100), 99)
            else:
                return "NEUTRAL", "تعارض بين المؤشرات والاتجاه العام", 0
                
            return direction, f"توافق المؤشرات ({strongest.source})", confidence
        else:
            return "NEUTRAL", "السوق متذبذب، انتظر فرصة أفضل", 0
    except Exception as e:
        return "NEUTRAL", "خطأ في التحليل", 0

def create_report_image(df_history):
    """توليد تقرير فاخر باللونين الأسود والذهبي"""
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0E1117')
    ax.axis('tight'); ax.axis('off')
    
    table_data = [df_history.columns.tolist()] + df_history.values.tolist()
    table = ax.table(cellText=table_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2)
    
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#FFD700')
        if row == 0:
            cell.set_facecolor('#B8860B') # رأس الجدول ذهبي غامق
            cell.set_text_props(color='white', weight='bold')
        else:
            cell.set_facecolor('#1A1F2B')
            cell.set_text_props(color='#FFD700')

    plt.title("The Candle Bot - Premium Report", color='#FFD700', fontsize=18, weight='bold', pad=20)
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', facecolor='#0E1117')
    buf.seek(0)
    plt.close()
    return buf

# --- 4. الواجهة الرئيسية ---
st.markdown('<h1 class="main-header">🕯️ The Candle Bot</h1>', unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #A0AAB5; font-size: 1.2rem;'>منصة الإشارات الذكية - تحليل متعدد المؤشرات</p>", unsafe_allow_html=True)

if search_button:
    play_sound()
    
    # أنميشن تحميل متطور
    placeholder = st.empty()
    with placeholder.container():
        st.markdown("<h3 style='text-align: center; color: #FFD700;'>جاري تحليل السوق واستخراج الإشارة...</h3>", unsafe_allow_html=True)
        progress_bar = st.progress(0)
        for i in range(100):
            time.sleep(0.01)
            progress_bar.progress(i + 1)
    
    df = fetch_candles(yf_symbol, selected_tf)
    placeholder.empty()
    
    if df is not None:
        signal, reason, confidence = generate_advanced_signal(df, yf_symbol)
        
        # عرض الإشارة بتصميم ضخم
        if "CALL" in signal:
            st.markdown(f'<div class="signal-box signal-call">🚀 {signal} <br><span style="font-size: 1.5rem;">ثقة {confidence}%</span></div>', unsafe_allow_html=True)
        elif "PUT" in signal:
            st.markdown(f'<div class="signal-box signal-put">🔻 {signal} <br><span style="font-size: 1.5rem;">ثقة {confidence}%</span></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="signal-box signal-neutral">⚖️ {signal}</div>', unsafe_allow_html=True)
        
        st.info(f"📝 **التحليل:** {reason}")
        
        # رسم بياني احترافي للشموع اليابانية (Plotly)
        st.markdown("### 📊 الرسم البياني الفني")
        fig = go.Figure(data=[go.Candlestick(
            x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
            increasing_line_color='#38ef7d', decreasing_line_color='#ef473a'
        )])
        fig.update_layout(
            template='plotly_dark', plot_bgcolor='#0E1117', paper_bgcolor='#0E1117',
            xaxis_rangeslider_visible=False, height=400, margin=dict(l=10, r=10, t=10, b=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # حفظ السجل
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = []
        if "NEUTRAL" not in signal:
            st.session_state.trade_history.append({
                "الزوج": selected_symbol_name, "الفريم": selected_tf_name,
                "الإشارة": "CALL" if "CALL" in signal else "PUT",
                "الثقة": f"{confidence}%", "الوقت": pd.Timestamp.now().strftime("%H:%M")
            })

# --- 5. السجل والتقرير ---
st.sidebar.markdown("---")
st.sidebar.markdown("<h3 style='color: #FFD700;'>📈 الإحصائيات</h3>", unsafe_allow_html=True)

if 'trade_history' in st.session_state and st.session_state.trade_history:
    df_history = pd.DataFrame(st.session_state.trade_history)
    
    total = len(df_history)
    calls = len(df_history[df_history['الإشارة'] == 'CALL'])
    puts = len(df_history[df_history['الإشارة'] == 'PUT'])
    
    st.sidebar.metric("إجمالي الصفقات", total)
    col1, col2 = st.sidebar.columns(2)
    col1.metric("CALL 📈", calls)
    col2.metric("PUT 📉", puts)
    
    if st.sidebar.button("📸 تحميل التقرير كصورة", use_container_width=True):
        img_buf = create_report_image(df_history.tail(10))
        st.sidebar.download_button("⬇️ اضغط للتحميل", data=img_buf, file_name="Candle_Report.png", mime="image/png")
else:
    st.sidebar.info("لا توجد صفقات مسجلة. ابدأ البحث الآن!")