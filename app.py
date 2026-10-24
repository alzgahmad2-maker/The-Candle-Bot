import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import pyalbedo
from pyalbedo import MarketDataWindow
from pyalbedo.signals import MACrossover, RSIMeanReversion, SignalAggregator
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from io import BytesIO
import time

# --- 1. إعدادات الصفحة والتصميم ---
st.set_page_config(page_title="The Candle Bot", page_icon="🕯️", layout="wide")

st.markdown("""
<style>
    /* تصميم عام */
    .stApp { background-color: #0E1117; }
    .main-header { font-size: 3rem; color: #FFD700; text-align: center; font-family: 'Arial', sans-serif; text-shadow: 2px 2px 4px #000000; }
    .signal-box { padding: 25px; border-radius: 15px; text-align: center; font-size: 2.5rem; font-weight: bold; margin: 20px 0; box-shadow: 0 4px 8px 0 rgba(0,0,0,0.2); }
    .signal-call { background: linear-gradient(135deg, #11998e, #38ef7d); color: white; }
    .signal-put { background: linear-gradient(135deg, #cb2d3e, #ef473a); color: white; }
    .signal-neutral { background: linear-gradient(135deg, #757F9A, #D7DDE8); color: black; }
    
    /* زر البحث المتحرك */
    .stButton>button { 
        background: linear-gradient(135deg, #FFD700, #FF8C00); 
        color: black; font-weight: bold; font-size: 1.2rem; 
        border: none; border-radius: 8px; padding: 10px 24px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover { transform: scale(1.05); box-shadow: 0px 0px 15px #FFD700; }
</style>
""", unsafe_allow_html=True)

# إضافة تأثير صوتي (Beep) عند الضغط على زر البحث
def play_sound():
    audio_html = """
    <audio autoplay>
        <source src="https://www.soundjay.com/buttons/sounds/button-09a.mp3" type="audio/mpeg">
    </audio>
    """
    st.markdown(audio_html, unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🕯️ The Candle Bot</h1>', unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: gray;'>نظام إشارات ذكي ومحلل فني لسوق العملات</p>", unsafe_allow_html=True)

# --- 2. الشريط الجانبي (المدخلات) ---
st.sidebar.header("⚙️ إعدادات التداول")

# قائمة أزواج العملات (متوافقة مع Yahoo Finance)
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
search_button = st.sidebar.button("🔍 بحث عن صفقة", use_container_width=True)

# --- 3. الدوال الأساسية ---

@st.cache_data(ttl=60) # تحديث البيانات كل دقيقة
def fetch_candles(symbol, tf):
    period = "7d" if tf in ["1m", "3m"] else "60d"
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period=period, interval="1m" if tf == "3m" else tf)
        
        if df.empty:
            return None
            
        df = df.reset_index()
        # إعادة تسمية الأعمدة
        df = df.rename(columns={'Datetime': 'time', 'Date': 'time', 'Open': 'open', 'High': 'high', 'Low': 'low', 'Close': 'close', 'Volume': 'volume'})
        
        # إذا كان الفريم 3 دقائق، نقوم بتجميع بيانات الدقيقة الواحدة إلى 3 دقائق
        if tf == "3m":
            df = df.set_index('time')
            df = df.resample('3T').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna()
            df = df.reset_index()

        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None) # إزالة المنطقة الزمنية لتجنب الأخطاء
        return df.tail(1000) # جلب آخر 1000 شمعة
    except Exception as e:
        st.error(f"خطأ في جلب البيانات: {e}")
        return None

def generate_signal(df, symbol):
    if df is None or len(df) < 50:
        return "NEUTRAL", "بيانات غير كافية للتحليل (أقل من 50 شمعة)", 0

    try:
        window = MarketDataWindow.from_arrays(
            symbol=symbol, open_=df['open'].values, high=df['high'].values,
            low=df['low'].values, close=df['close'].values, volume=df['volume'].values,
        )
        ma_cross = MACrossover(fast_period=12, slow_period=26)
        rsi_reversion = RSIMeanReversion(period=14, oversold=30, overbought=70)
        aggregator = SignalAggregator([ma_cross, rsi_reversion])
        bundle = aggregator.generate(window)

        if bundle and bundle.signals:
            strongest = max(bundle.signals, key=lambda s: s.strength)
            # تحديد الاتجاه
            if "bullish" in str(strongest.direction).lower() or "long" in str(strongest.direction).lower():
                direction = "CALL (صعود)"
            else:
                direction = "PUT (هبوط)"
            
            confidence = min(int(strongest.strength * 100), 99) # نسبة الثقة كرقم مئوي
            return direction, f"الاستراتيجية: {strongest.source}", confidence
        else:
            return "NEUTRAL", "لا توجد إشارة قوية حالياً، السوق متذبذب", 0
    except Exception as e:
        return "NEUTRAL", f"خطأ في المؤشرات: {e}", 0

def create_report_image(df_history):
    """توليد صورة جميلة لسجل الصفقات باستخدام Matplotlib"""
    fig, ax = plt.subplots(figsize=(10, 6), facecolor='#0E1117')
    ax.axis('tight'); ax.axis('off')
    
    # إعداد الجدول
    table_data = [df_history.columns.tolist()] + df_history.values.tolist()
    table = ax.table(cellText=table_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False)
    table.set_fontsize(12)
    table.scale(1, 2)
    
    # تلوين الجدول
    for (row, col), cell in table.get_celld().items():
        cell.set_text_props(color='white')
        cell.set_edgecolor('#FFD700')
        if row == 0:
            cell.set_facecolor('#1E3A8A') # لون رأس الجدول
            cell.set_text_props(weight='bold')
        else:
            cell.set_facecolor('#1F2937')

    plt.title("The Candle Bot - Trade History", color='#FFD700', fontsize=16, pad=20)
    
    # حفظ الصورة في الذاكرة
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', facecolor='#0E1117')
    buf.seek(0)
    plt.close()
    return buf

# --- 4. المنطق الرئيسي عند الضغط على الزر ---
if search_button:
    play_sound() # تشغيل الصوت
    
    # أنميشن البحث
    with st.spinner("🔄 جاري الاتصال بالسوق وجلب الشموع..."):
        time.sleep(1) 
        df = fetch_candles(yf_symbol, selected_tf)
        
    if df is not None:
        st.success(f"✅ تم جلب {len(df)} شمعة بنجاح لـ {selected_symbol_name}.")
        
        with st.spinner("🧠 جاري تحليل المؤشرات واستخراج الإشارة..."):
            time.sleep(1)
            signal, reason, confidence = generate_signal(df, yf_symbol)
        
        # عرض الإشارة
        st.subheader("📊 نتيجة التحليل")
        if "CALL" in signal:
            st.markdown(f'<div class="signal-box signal-call">🚀 {signal} (ثقة {confidence}%)</div>', unsafe_allow_html=True)
        elif "PUT" in signal:
            st.markdown(f'<div class="signal-box signal-put">🔻 {signal} (ثقة {confidence}%)</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="signal-box signal-neutral">⚖️ {signal}</div>', unsafe_allow_html=True)
        
        st.info(f"📝 **السبب:** {reason}")
        
        # رسم بياني تفاعلي
        st.line_chart(df.set_index('time')['close'], color="#FFD700")
        
        # إدارة سجل الصفقات
        if 'trade_history' not in st.session_state:
            st.session_state.trade_history = []
            
        if "NEUTRAL" not in signal:
            new_trade = {
                "الزوج": selected_symbol_name,
                "الفريم": selected_tf_name,
                "الإشارة": signal,
                "الثقة": f"{confidence}%",
                "الوقت": pd.Timestamp.now().strftime("%H:%M")
            }
            st.session_state.trade_history.append(new_trade)

# --- 5. عرض السجل والإحصائيات وتحميل الصورة ---
st.sidebar.markdown("---")
st.sidebar.header("📈 سجل وإحصائيات")

if 'trade_history' in st.session_state and st.session_state.trade_history:
    df_history = pd.DataFrame(st.session_state.trade_history)
    
    # إحصائيات
    total = len(df_history)
    calls = len(df_history[df_history['الإشارة'].str.contains('CALL')])
    puts = len(df_history[df_history['الإشارة'].str.contains('PUT')])
    
    st.sidebar.metric("إجمالي الإشارات", total)
    col1, col2 = st.sidebar.columns(2)
    col1.metric("CALL 📈", calls)
    col2.metric("PUT 📉", puts)
    
    with st.sidebar.expander("عرض الجدول"):
        st.dataframe(df_history, use_container_width=True)
        
    if st.sidebar.button("📸 تحميل السجل كصورة", use_container_width=True):
        with st.spinner("جاري تصميم الصورة..."):
            img_buf = create_report_image(df_history.tail(10)) # آخر 10 صفقات
            st.sidebar.download_button(
                label="⬇️ اضغط هنا للتحميل",
                data=img_buf,
                file_name="The_Candle_Report.png",
                mime="image/png"
            )
else:
    st.sidebar.info("لا توجد إشارات مسجلة بعد. اضغط على 'بحث عن صفقة' للبدء.")