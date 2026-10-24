import streamlit as st
import pandas as pd
import numpy as np
from otcharts import Client
import pyalbedo
from pyalbedo import MarketDataWindow, EMA, RSI
from pyalbedo.signals import MACrossover, RSIMeanReversion, SignalAggregator
from html2image import Html2Image
import os
import time

# --- إعدادات الصفحة ---
st.set_page_config(page_title="The Candle Bot", page_icon="🕯️", layout="wide")

# --- تصميم مخصص (CSS) لتحسين المظهر ---
st.markdown("""
<style>
    .main-header { font-size: 3rem; color: #FF4B4B; text-align: center; }
    .signal-box { padding: 20px; border-radius: 10px; text-align: center; font-size: 2rem; font-weight: bold; }
    .signal-call { background-color: #d4edda; color: #155724; }
    .signal-put { background-color: #f8d7da; color: #721c24; }
</style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">🕯️ The Candle Bot</h1>', unsafe_allow_html=True)

# --- الشريط الجانبي: المدخلات ---
st.sidebar.header("⚙️ إعدادات الصفقة")

# قائمة الأزواج (يمكنك توسيعها حسب ما يوفره otcharts)
# ملاحظة: free tier يحدد 5 أزواج فقط. ستحتاج لخطة مدفوعة لتغطية جميع الأزواج.
symbols = ["EURUSD_otc", "GBPUSD_otc", "USDJPY_otc", "AUDCAD_otc", "EURGBP_otc"]
selected_symbol = st.sidebar.selectbox("اختر زوج العملات", symbols)

timeframes = {"1 دقيقة": 60, "3 دقائق": 180, "5 دقائق": 300, "15 دقيقة": 900}
selected_tf_name = st.sidebar.radio("اختر الفريم الزمني", list(timeframes.keys()))
timeframe = timeframes[selected_tf_name]

# --- زر البحث ---
search_button = st.sidebar.button("🔍 بحث عن صفقة", use_container_width=True, type="primary")


# --- الدوال المساعدة ---

@st.cache_data(ttl=60) # تخزين مؤقت لتجنب استهلاك الحصة سريعًا
def fetch_candles(symbol, tf, limit=1000):
    """جلب الشموع من OTCharts"""
    try:
        # يتطلب مفتاح API من otcharts.com
        # يمكنك تعيينه كمتغير بيئة: OTCHARTS_API_KEY
        client = Client() 
        # ملاحظة: free tier قد يسمح بـ 300 شمعة فقط. الخطة المدفوعة تسمح بـ 1000+
        bars = client.candles("otc", symbol, tf=tf, limit=limit)
        df = pd.DataFrame([vars(b) for b in bars])
        df['time'] = pd.to_datetime(df['time'], unit='s')
        df = df.sort_values('time').reset_index(drop=True)
        return df
    except Exception as e:
        st.error(f"خطأ في جلب البيانات: {e}")
        return None


def generate_signal(df):
    """توليد إشارة بناءً على استراتيجية مدمجة (EMA + RSI)"""
    if df is None or len(df) < 50:
        return None, "بيانات غير كافية"

    close = df['close'].values

    try:
        # إنشاء نافذة بيانات لـ PyAlbedo
        window = MarketDataWindow.from_arrays(
            symbol=selected_symbol,
            open_=df['open'].values, high=df['high'].values,
            low=df['low'].values, close=close, volume=df.get('volume', np.zeros(len(df))).values,
        )

        # 1. استراتيجية تقاطع المتوسطات (EMA 12/26)
        ma_cross = MACrossover(fast_period=12, slow_period=26)
        
        # 2. استراتيجية RSI (تشبع شراء/بيع)
        rsi_reversion = RSIMeanReversion(period=14, oversold=30, overbought=70)

        # تجميع الإشارات (يمكنك إضافة المزيد من الاستراتيجيات هنا)
        aggregator = SignalAggregator([ma_cross, rsi_reversion])
        bundle = aggregator.generate(window)

        if bundle and bundle.signals:
            # نأخذ الإشارة الأقوى
            strongest = max(bundle.signals, key=lambda s: s.strength)
            direction = "CALL (صعود)" if "bullish" in str(strongest.direction).lower() or "long" in str(strongest.direction).lower() else "PUT (هبوط)"
            return direction, f"قوة الإشارة: {strongest.strength:.2f} (من {strongest.source})"
        else:
            return "NEUTRAL", "لا توجد إشارة واضحة حاليًا"
    except Exception as e:
        return None, f"خطأ في التحليل: {e}"


def export_to_image(df_trades):
    """تصدير جدول الصفقات كصورة جميلة"""
    # تنسيق الجدول بـ HTML/CSS
    html_style = """
    <style>
        table { border-collapse: collapse; width: 100%; font-family: Arial, sans-serif; }
        th { background-color: #4CAF50; color: white; padding: 8px; }
        td { border: 1px solid #ddd; padding: 8px; text-align: center; }
        tr:nth-child(even) { background-color: #f2f2f2; }
    </style>
    """
    html_table = df_trades.to_html(index=False, classes='table', border=0)
    full_html = f"<html><head>{html_style}</head><body>{html_table}</body></html>"
    
    # تحويل HTML إلى صورة
    hti = Html2Image()
    # ملاحظة: قد تحتاج إلى تثبيت متصفح Chrome/Chromium ليعمل html2image
    img_path = "trades_log.png"
    hti.screenshot(html_str=full_html, save_as=img_path, size=(800, 400))
    return img_path


# --- المنطق الرئيسي ---
if search_button:
    # 1. تشغيل الأنميشن (شريط تقدم بسيط)
    with st.spinner("🔄 جاري جلب الشموع وتحليل السوق..."):
        # محاكاة تأخير بسيط لإظهار الأنميشن
        time.sleep(1.5) 
        
        # 2. جلب البيانات
        df = fetch_candles(selected_symbol, timeframe, limit=1000)
        
        if df is not None:
            st.success(f"✅ تم جلب {len(df)} شمعة لـ {selected_symbol} على فريم {selected_tf_name}")
            
            # 3. توليد الإشارة
            signal, reason = generate_signal(df)
            
            # 4. عرض النتيجة
            st.subheader("📊 نتيجة التحليل")
            if signal and "CALL" in signal:
                st.markdown(f'<div class="signal-box signal-call">🚀 إشارة: {signal}</div>', unsafe_allow_html=True)
            elif signal and "PUT" in signal:
                st.markdown(f'<div class="signal-box signal-put">🔻 إشارة: {signal}</div>', unsafe_allow_html=True)
            else:
                st.warning(f"⚠️ {reason}")
            
            if signal:
                st.info(f"📝 {reason}")
            
            # 5. عرض رسم بياني بسيط (اختياري)
            st.line_chart(df.set_index('time')['close'])
            
            # 6. إدارة سجل الصفقات (نموذج بسيط)
            if 'trade_history' not in st.session_state:
                st.session_state.trade_history = []
            
            # إضافة الصفقة الحالية للسجل (لأغراض العرض)
            if signal and "CALL" in signal or "PUT" in signal:
                 st.session_state.trade_history.append({
                     "الزوج": selected_symbol, "الفريم": selected_tf_name,
                     "الإشارة": signal, "السبب": reason, "الوقت": pd.Timestamp.now().strftime("%H:%M:%S")
                 })

# --- عرض سجل الصفقات والإحصائيات ---
st.sidebar.markdown("---")
st.sidebar.header("📈 إحصائيات وسجل")

if 'trade_history' in st.session_state and st.session_state.trade_history:
    df_history = pd.DataFrame(st.session_state.trade_history)
    
    # إحصائيات بسيطة (يمكنك تطويرها لاحقًا لحساب النتائج الفعلية)
    total_trades = len(df_history)
    st.sidebar.metric("إجمالي الإشارات", total_trades)
    
    with st.sidebar.expander("عرض سجل الصفقات"):
        st.dataframe(df_history, use_container_width=True)
    
    # زر تصدير الصورة
    if st.sidebar.button("📸 تحميل السجل كصورة"):
        try:
            img_path = export_to_image(df_history)
            with open(img_path, "rb") as f:
                st.sidebar.download_button(
                    label="⬇️ تحميل الصورة",
                    data=f,
                    file_name="the_candle_trades.png",
                    mime="image/png"
                )
        except Exception as e:
            st.sidebar.error(f"فشل إنشاء الصورة: {e}")
else:
    st.sidebar.info("لا توجد صفقات مسجلة بعد.")