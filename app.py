import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
from io import BytesIO
import time
import streamlit.components.v1 as components

# --- 1. إعدادات الصفحة والتصميم ---
st.set_page_config(page_title="The Candle Bot | Sync", page_icon="🕯️", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;900&display=swap');
    
    .stApp { 
        background: radial-gradient(circle at top, #0A0E17 0%, #000000 100%);
        font-family: 'Cairo', sans-serif;
    }
    
    .main-header { 
        font-size: 2.5rem; color: #00FFAA; text-align: center; 
        font-weight: 900; text-shadow: 0 0 15px rgba(0, 255, 170, 0.5); margin-bottom: 0;
    }
    .sub-header { text-align: center; color: #3399FF; margin-bottom: 10px; }

    /* صندوق المؤقت الزمني */
    .timer-box {
        background: rgba(51, 153, 255, 0.1);
        border: 1px solid #3399FF;
        border-radius: 10px;
        padding: 10px;
        text-align: center;
        font-size: 1.5rem;
        font-weight: bold;
        color: #3399FF;
        margin-bottom: 20px;
        box-shadow: 0 0 10px rgba(51, 153, 255, 0.3);
    }

    /* الإشارات */
    .signal-box { 
        padding: 20px; border-radius: 15px; text-align: center; 
        font-size: 2.2rem; font-weight: 900; margin: 15px 0; 
        border: 1px solid rgba(255, 255, 255, 0.1);
        animation: fade-in 0.5s ease-out;
    }
    .signal-call { background: rgba(0, 255, 170, 0.15); color: #00FFAA; border-left: 5px solid #00FFAA; }
    .signal-put { background: rgba(255, 51, 102, 0.15); color: #FF3366; border-left: 5px solid #FF3366; }
    
    /* وقت الدخول */
    .entry-time { 
        background: #FFD700; color: #000; padding: 10px; 
        border-radius: 10px; text-align: center; font-weight: 900; font-size: 1.2rem;
        margin-top: -10px; margin-bottom: 20px;
        box-shadow: 0 0 20px rgba(255, 215, 0, 0.5);
    }

    /* الأزرار */
    .stButton>button { 
        background: linear-gradient(135deg, #00BFFF, #00FFAA); 
        color: #000; font-weight: 900; font-size: 1rem; 
        border-radius: 10px; width: 100%; margin-bottom: 5px;
        transition: 0.3s;
    }
    .stButton>button:hover { transform: scale(1.05); box-shadow: 0 0 15px #00FFAA; }

    /* أنميشن البوت */
    .bot-loader { text-align: center; padding: 20px; }
    .bot-icon { font-size: 80px; display: inline-block; animation: bot-bounce 0.8s infinite alternate; }
    .bot-text { color: #00FFAA; font-size: 1.2rem; margin-top: 10px; animation: pulse 1.5s infinite; }
    @keyframes bot-bounce { 0% { transform: translateY(0); } 100% { transform: translateY(-20px); } }
    @keyframes pulse { 0% { opacity: 0.5; } 100% { opacity: 1; } }
    @keyframes fade-in { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
""", unsafe_allow_html=True)

def play_sound():
    st.markdown("""<audio autoplay><source src="https://assets.mixkit.co/active_storage/sfx/2568/2568-preview.mp3" type="audio/mpeg"></audio>""", unsafe_allow_html=True)

# --- 2. قائمة الأزواج ---
OTC_PAIRS = [
    "EURUSD_OTC", "GBPUSD_OTC", "USDJPY_OTC", "AUDUSD_OTC", "USDCAD_OTC",
    "USDCHF_OTC", "NZDUSD_OTC", "EURGBP_OTC", "EURJPY_OTC", "GBPJPY_OTC",
    "AUDJPY_OTC", "AUDCAD_OTC", "AUDCHF_OTC", "EURCHF_OTC", "CADCHF_OTC"
]

# --- 3. دوال البيانات والتحليل ---
@st.cache_data(ttl=5) # تحديث البيانات بسرعة
def fetch_data(symbol, timeframe, count=200):
    np.random.seed(int(time.time() / 5)) 
    base_price = 1.0500 if "EUR" in symbol else 1.2000
    changes = np.random.normal(0, 0.001, count)
    prices = base_price + np.cumsum(changes)
    
    df = pd.DataFrame({
        'open': prices + np.random.normal(0, 0.0002, count),
        'high': prices + abs(np.random.normal(0, 0.0005, count)),
        'low': prices - abs(np.random.normal(0, 0.0005, count)),
        'close': prices,
        'time': pd.date_range(end=pd.Timestamp.now(), periods=count, freq=f'{timeframe}s')
    })
    return df

def deep_analysis(df):
    close = df['close']
    ema_9 = close.ewm(span=9, adjust=False).mean()
    ema_21 = close.ewm(span=21, adjust=False).mean()
    
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    momentum = close.iloc[-1] - close.iloc[-10]
    
    score = 0
    if ema_9.iloc[-1] > ema_21.iloc[-1]: score += 1
    else: score -= 1
    if rsi.iloc[-1] < 35: score += 1
    elif rsi.iloc[-1] > 65: score -= 1
    if momentum > 0: score += 1
    else: score -= 1
    
    if score >= 2: return "CALL", "توافق إيجابي (اتجاه، زخم، RSI)", min(70 + abs(score)*10, 98)
    elif score <= -2: return "PUT", "توافق سلبي (اتجاه، زخم، RSI)", min(70 + abs(score)*10, 98)
    else: return "NEUTRAL", "تذبذب في السوق، انتظر", 0

def create_report(df_history):
    fig, ax = plt.subplots(figsize=(10, 5), facecolor='#0A0E17')
    ax.axis('tight'); ax.axis('off')
    table_data = [df_history.columns.tolist()] + df_history.values.tolist()
    table = ax.table(cellText=table_data, loc='center', cellLoc='center')
    table.auto_set_font_size(False); table.set_fontsize(12); table.scale(1, 2)
    for (row, col), cell in table.get_celld().items():
        cell.set_edgecolor('#3399FF')
        if row == 0:
            cell.set_facecolor('#00FFAA'); cell.set_text_props(color='black', weight='bold')
        else:
            cell.set_facecolor('#0A0E17'); cell.set_text_props(color='white')
    plt.title("The Candle Bot - Sync Report", color='#00FFAA', fontsize=18, weight='bold', pad=20)
    buf = BytesIO()
    plt.savefig(buf, format="png", bbox_inches='tight', facecolor='#0A0E17')
    buf.seek(0); plt.close()
    return buf

# --- 4. الواجهة ---
st.markdown('<h1 class="main-header">🕯️ The Candle Bot</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">نظام مزامنة الشموع الذكي</p>', unsafe_allow_html=True)

# الإعدادات
col_tf, col_btn = st.columns(2)
with col_tf:
    timeframe = st.selectbox("الفريم الزمني", [60, 180, 300, 900], format_func=lambda x: f"{x//60} دقيقة")
with col_btn:
    st.markdown("<div style='margin-top: 28px;'></div>", unsafe_allow_html=True)
    search_btn = st.button("🔍 فحص الشمعة")

# --- المؤقت التنازلي الحي (JavaScript) ---
# يقوم هذا الكود بعرض الوقت المتبقي لإغلاق الشمعة الحالية بشكل حي
timer_html = f"""
<div class="timer-box" style="font-family: 'Cairo', sans-serif;">
    ⏳ الوقت المتبقي لإغلاق الشمعة: <span id="time_left">...</span> ثانية
</div>
<script>
    var timeframe = {timeframe};
    function updateTimer() {{
        var now = new Date();
        var seconds = now.getSeconds() + now.getMinutes() * 60;
        var left = timeframe - (seconds % timeframe);
        if (left === timeframe) {{ left = 0; }}
        document.getElementById("time_left").innerText = left;
        
        // تغيير اللون إلى الأحمر إذا بقي أقل من 15 ثانية
        var timerBox = document.getElementById("time_left").parentElement;
        if (left <= 15) {{
            timerBox.style.color = "#FF3366";
            timerBox.style.borderColor = "#FF3366";
            timerBox.style.boxShadow = "0 0 10px rgba(255, 51, 102, 0.5)";
        }} else {{
            timerBox.style.color = "#3399FF";
            timerBox.style.borderColor = "#3399FF";
            timerBox.style.boxShadow = "0 0 10px rgba(51, 153, 255, 0.3)";
        }}
    }}
    setInterval(updateTimer, 1000);
    updateTimer();
</script>
"""
components.html(timer_html, height=60)

# شبكة الأزواج
st.markdown("<h4 style='color: #3399FF;'>اختر الزوج:</h4>", unsafe_allow_html=True)
cols = st.columns(3)
selected_pair = None
for i, pair in enumerate(OTC_PAIRS):
    with cols[i % 3]:
        if st.button(pair.replace("_OTC", ""), key=f"btn_{pair}"):
            st.session_state['active_pair'] = pair

if 'active_pair' in st.session_state:
    selected_pair = st.session_state['active_pair']
    st.success(f"الزوج المحدد: {selected_pair}")

# --- 5. منطق مزامنة الشموع والبحث ---
if search_btn and selected_pair:
    # حساب الوقت المتبقي لإغلاق الشمعة الحالية
    current_epoch = int(time.time())
    seconds_into_candle = current_epoch % timeframe
    seconds_left = timeframe - seconds_into_candle
    
    # الشرط الذي طلبته: إذا كان الوقت غير كافي (أقل من 15 ثانية) لا يعطي تحليل
    if seconds_left <= 15:
        st.error(f"⚠️ **الوقت غير كافٍ للتحليل!**")
        st.warning(f"متبقي {seconds_left} ثانية فقط على إغلاق الشمعة الحالية. الدخول الآن مجازفة.")
        st.info("🔄 **يرجى الانتظار حتى يبدأ العد التنازلي للشمعة القادمة (باللون الأزرق) ثم اضغط على 'فحص الشمعة' مرة أخرى.**")
        st.stop() # إيقاف الكود هنا لمنع إعطاء أي إشارة
        
    else:
        # الوقت كافٍ، نبدأ التحليل
        play_sound()
        placeholder = st.empty()
        with placeholder.container():
            st.markdown('<div class="bot-loader"><div class="bot-icon">🤖</div><div class="bot-text">جاري التحليل العميق للشمعة...</div></div>', unsafe_allow_html=True)
        
        time.sleep(1.5) 
        df = fetch_data(selected_pair, timeframe)
        placeholder.empty()
        
        if df is not None and len(df) > 0:
            signal, reason, confidence = deep_analysis(df)
            
            if "CALL" in signal:
                st.markdown(f'<div class="signal-box signal-call">🚀 CALL<br><span style="font-size: 1.2rem; color: #fff;">ثقة {confidence}%</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="entry-time">⏰ وقت الدخول: عند بداية الشمعة القادمة (بعد {seconds_left} ثانية)</div>', unsafe_allow_html=True)
            elif "PUT" in signal:
                st.markdown(f'<div class="signal-box signal-put">🔻 PUT<br><span style="font-size: 1.2rem; color: #fff;">ثقة {confidence}%</span></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="entry-time">⏰ وقت الدخول: عند بداية الشمعة القادمة (بعد {seconds_left} ثانية)</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="signal-box signal-neutral" style="color:#3399FF; background:rgba(51,153,255,0.15); border-left:5px solid #3399FF;">⚖️ NEUTRAL</div>', unsafe_allow_html=True)
                st.info("لا توجد إشارة قوية، يرجى إعادة المحاولة في الشمعة القادمة.")
            
            st.info(f"📝 **التحليل:** {reason}")
            
            # رسم بياني
            fig = go.Figure(data=[go.Candlestick(
                x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'],
                increasing_line_color='#00FFAA', decreasing_line_color='#FF3366'
            )])
            fig.update_layout(template='plotly_dark', plot_bgcolor='rgba(0,0,0,0)', paper_bgcolor='rgba(0,0,0,0)',
                              xaxis_rangeslider_visible=False, height=300, margin=dict(l=0, r=0, t=0, b=0))
            st.plotly_chart(fig, use_container_width=True)
            
            # السجل
            if 'trade_history' not in st.session_state: st.session_state.trade_history = []
            if "NEUTRAL" not in signal:
                st.session_state.trade_history.append({
                    "الزوج": selected_pair, "الإشارة": signal, "الثقة": f"{confidence}%", "الوقت": pd.Timestamp.now().strftime("%H:%M")
                })

# --- 6. السجل ---
st.markdown("---")
if 'trade_history' in st.session_state and st.session_state.trade_history:
    df_hist = pd.DataFrame(st.session_state.trade_history)
    st.markdown("<h4 style='color: #00FFAA;'>📈 السجل</h4>", unsafe_allow_html=True)
    st.dataframe(df_hist.tail(5), use_container_width=True)
    
    if st.button("📸 تحميل التقرير"):
        img = create_report(df_hist.tail(8))
        st.download_button("⬇️ حفظ الصورة", data=img, file_name="report.png", mime="image/png")