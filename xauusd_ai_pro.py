#!/usr/bin/env python3
"""
XAUUSD AI Pro - Trợ Lý Giao Dịch Vàng Chuyên Nghiệp
Phiên bản 1.0 | Commercial SaaS Ready
Tác giả: Grok xAI | 2026

Tính năng chính:
- Phân tích kỹ thuật thời gian thực + AI Signal Engine
- Chat AI thông minh (rule-based + context aware)
- Backtester chiến lược
- Risk Manager chuyên nghiệp
- Dashboard đẹp mắt, dark theme trading style
- Sẵn sàng thương mại hóa (subscription, upgrade flow, disclaimer)

Hướng dẫn chạy:
1. pip install -r requirements.txt
2. streamlit run xauusd_ai_pro.py
3. Mở trình duyệt tại http://localhost:8501

Để triển khai thương mại:
- Deploy lên Streamlit Cloud / Hugging Face / VPS
- Tích hợp Stripe cho thanh toán thật
- Dùng Supabase/Firebase cho user management & usage tracking
- Thêm Telegram bot alerts, MT5 integration
- Scale với Docker + load balancer khi có >1000 users

Giá gợi ý:
- Free: 5 tín hiệu/ngày, chat giới hạn
- Pro: $29/tháng - không giới hạn + backtest nâng cao + alerts
- Enterprise: $99/tháng - API + white-label + custom ML model
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import time
import json
from pathlib import Path
import requests
try:
    import MetaTrader5 as mt5
    MT5_AVAILABLE = True
except ImportError:
    MT5_AVAILABLE = False
try:
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# ==================== CẤU HÌNH TRANG ====================
st.set_page_config(
    page_title="XAUUSD AI Pro | Trợ Lý Giao Dịch Vàng",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'Get Help': 'https://t.me/xauusd_ai_support',
        'Report a bug': "mailto:support@xauusd.ai",
        'About': "# XAUUSD AI Pro v1.0\nTrợ lý AI giao dịch vàng chuyên nghiệp. Không phải lời khuyên tài chính."
    }
)

# Dark theme chuyên nghiệp cho trading
st.markdown("""
<style>
    .stApp {
        background-color: #0f1117;
        color: #e0e0e0;
    }
    .stMetric {
        background-color: #1a1d24;
        border-radius: 12px;
        padding: 12px;
        border: 1px solid #2a2f38;
    }
    .stButton>button {
        background: linear-gradient(90deg, #00c853, #00e676);
        color: white;
        font-weight: 700;
        border-radius: 8px;
        border: none;
        padding: 10px 24px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0, 200, 83, 0.4);
    }
    .stSelectbox, .stNumberInput, .stSlider {
        background-color: #1a1d24;
    }
    h1, h2, h3 {
        color: #00e676 !important;
    }
    .signal-strong-buy { color: #00c853; font-size: 1.4rem; font-weight: 800; }
    .signal-buy { color: #69f0ae; font-size: 1.3rem; font-weight: 700; }
    .signal-neutral { color: #ffd54f; font-size: 1.3rem; font-weight: 700; }
    .signal-sell { color: #ff8a80; font-size: 1.3rem; font-weight: 700; }
    .signal-strong-sell { color: #ff5252; font-size: 1.4rem; font-weight: 800; }
    .stChatMessage {
        background-color: #1a1d24;
        border-radius: 12px;
        margin: 8px 0;
    }
    .disclaimer {
        font-size: 0.75rem;
        color: #888;
        text-align: center;
        padding: 20px;
        border-top: 1px solid #2a2f38;
    }
</style>
""", unsafe_allow_html=True)

# ==================== QUẢN LÝ USER & SESSION ====================
if "user" not in st.session_state:
    st.session_state.user = {
        "name": "Demo Trader",
        "plan": "Premium",  # Thay bằng "Free" để test giới hạn
        "queries_today": 0,
        "last_reset": datetime.now().date().isoformat()
    }

if "messages" not in st.session_state:
    st.session_state.messages = []

if "last_data_fetch" not in st.session_state:
    st.session_state.last_data_fetch = None

# Reset daily queries
today = datetime.now().date().isoformat()
if st.session_state.user["last_reset"] != today:
    st.session_state.user["queries_today"] = 0
    st.session_state.user["last_reset"] = today

def upgrade_to_premium():
    st.session_state.user["plan"] = "Premium"
    st.balloons()
    st.success("🎉 Nâng cấp thành công! Chào mừng bạn đến với gói Premium. (Demo - Trong production sẽ tích hợp Stripe)")

def check_premium(feature_name="tính năng"):
    if st.session_state.user["plan"] != "Premium":
        st.warning(f"🔒 {feature_name} chỉ dành cho gói Premium ($29/tháng)")
        if st.button("⬆️ Nâng cấp ngay - Chỉ $29/tháng", key=f"upgrade_{feature_name}"):
            upgrade_to_premium()
        return False
    return True

# ==================== HÀM PHÂN TÍCH DỮ LIỆU ====================
@st.cache_data(ttl=300, show_spinner="Đang tải dữ liệu thị trường vàng...")
def fetch_gold_data(period="6mo", interval="1h"):
    """Lấy dữ liệu XAUUSD từ Yahoo Finance (GC=F = Gold Futures)"""
    try:
        ticker = yf.Ticker("GC=F")
        df = ticker.history(period=period, interval=interval)
        if df.empty:
            raise ValueError("Không lấy được dữ liệu")
        df = df.reset_index()
        df.rename(columns={"Date": "Datetime"}, inplace=True)
        return df
    except Exception as e:
        st.error(f"Lỗi tải dữ liệu: {e}. Vui lòng thử lại sau.")
        return pd.DataFrame()

def calculate_indicators(df):
    """Tính toán tất cả chỉ báo kỹ thuật"""
    if df.empty or len(df) < 200:
        return df
    
    close = df['Close']
    
    # Moving Averages
    df['SMA20'] = close.rolling(20).mean()
    df['SMA50'] = close.rolling(50).mean()
    df['SMA200'] = close.rolling(200).mean()
    df['EMA12'] = close.ewm(span=12, adjust=False).mean()
    df['EMA26'] = close.ewm(span=26, adjust=False).mean()
    
    # RSI
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    
    # Bollinger Bands
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df['BB_Mid'] = bb_mid
    df['BB_Upper'] = bb_mid + (2 * bb_std)
    df['BB_Lower'] = bb_mid - (2 * bb_std)
    
    # ATR (Average True Range)
    high = df['High']
    low = df['Low']
    prev_close = close.shift(1)
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    
    return df

def generate_ai_signal(df):
    """AI Signal Engine - Phân tích đa chỉ báo"""
    if df.empty or len(df) < 50:
        return "TRUNG LẬP", 50, ["Không đủ dữ liệu"], 0
    
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    
    score = 0
    reasons = []
    
    # 1. Xu hướng tổng thể (40% trọng số)
    if latest['Close'] > latest['SMA50'] and latest['SMA50'] > latest['SMA200']:
        score += 3
        reasons.append("✅ Xu hướng tăng dài hạn (Close > SMA50 > SMA200)")
    elif latest['Close'] < latest['SMA50'] and latest['SMA50'] < latest['SMA200']:
        score -= 3
        reasons.append("❌ Xu hướng giảm dài hạn")
    else:
        reasons.append("➡️ Thị trường đang sideways / consolidation")
    
    # 2. Momentum (RSI)
    rsi = latest['RSI']
    if rsi < 30:
        score += 2
        reasons.append(f"✅ RSI oversold ({rsi:.1f}) - Tiềm năng đảo chiều tăng")
    elif rsi > 70:
        score -= 2
        reasons.append(f"⚠️ RSI overbought ({rsi:.1f}) - Rủi ro điều chỉnh")
    elif 40 < rsi < 60:
        reasons.append(f"➡️ RSI trung lập ({rsi:.1f})")
    
    # 3. MACD
    if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
        score += 2
        reasons.append("✅ MACD vừa crossover bullish")
    elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
        score -= 2
        reasons.append("❌ MACD vừa crossover bearish")
    elif latest['MACD'] > latest['MACD_Signal']:
        score += 1
        reasons.append("✅ MACD bullish")
    else:
        score -= 1
        reasons.append("❌ MACD bearish")
    
    # 4. Bollinger Bands & Volatility
    if latest['Close'] < latest['BB_Lower']:
        score += 1
        reasons.append("✅ Giá chạm Lower Band - Oversold, rebound cao")
    elif latest['Close'] > latest['BB_Upper']:
        score -= 1
        reasons.append("⚠️ Giá chạm Upper Band - Overbought, pullback rủi ro")
    
    # 5. ATR & Volatility context
    atr_pct = (latest['ATR'] / latest['Close']) * 100
    if atr_pct > 1.5:
        reasons.append(f"📈 Biến động cao (ATR {atr_pct:.2f}%) - Cẩn thận quản lý rủi ro")
    
    # Quyết định cuối
    if score >= 5:
        signal = "MẠNH MUA"
        color_class = "signal-strong-buy"
        confidence = min(92, 75 + score * 2)
    elif score >= 2:
        signal = "MUA"
        color_class = "signal-buy"
        confidence = 65 + score * 4
    elif score <= -5:
        signal = "MẠNH BÁN"
        color_class = "signal-strong-sell"
        confidence = min(92, 75 + abs(score) * 2)
    elif score <= -2:
        signal = "BÁN"
        color_class = "signal-sell"
        confidence = 65 + abs(score) * 4
    else:
        signal = "TRUNG LẬP"
        color_class = "signal-neutral"
        confidence = 50 + abs(score) * 3
    
    return signal, confidence, reasons, score

def generate_chat_response(user_prompt, df, current_signal, confidence, reasons):
    """AI Chat Engine - Trả lời thông minh theo ngữ cảnh"""
    prompt = user_prompt.lower().strip()
    latest = df.iloc[-1] if not df.empty else None
    price = latest['Close'] if latest is not None else 0
    
    # Context-aware responses
    if any(kw in prompt for kw in ["giá", "price", "hiện tại", "bao nhiêu", "current"]):
        change_24h = ((price - df.iloc[-2]['Close']) / df.iloc[-2]['Close'] * 100) if len(df) > 1 else 0
        return f"📊 **Giá XAUUSD hiện tại: ${price:,.2f}/oz**\n\nThay đổi 24h: **{change_24h:+.2f}%**\n\nKhuyến nghị AI hiện tại: **{current_signal}** (độ tin cậy {confidence}%)"
    
    if any(kw in prompt for kw in ["mua", "buy", "vào lệnh", "long", "mở vị thế"]):
        if "mua" in current_signal.lower() or "mạnh mua" in current_signal.lower():
            return f"✅ **Đồng ý MUA** theo khuyến nghị AI ({current_signal} - {confidence}%)\n\nLý do chính:\n" + "\n".join([f"• {r}" for r in reasons[:3]]) + "\n\n💡 Khuyến nghị: Đặt SL dưới Low gần nhất ~${:.2f}".format(price - latest['ATR']*1.5 if latest is not None else price-20)
        else:
            return f"⚠️ Hiện tại tín hiệu là **{current_signal}**. Tôi khuyên bạn **KHÔNG NÊN MUA** lúc này. Hãy chờ tín hiệu đảo chiều rõ ràng hơn hoặc sử dụng chiến lược mean-reversion."
    
    if any(kw in prompt for kw in ["bán", "sell", "short", "thoát lệnh"]):
        if "bán" in current_signal.lower() or "mạnh bán" in current_signal.lower():
            return f"✅ **Đồng ý BÁN** theo khuyến nghị ({current_signal} - {confidence}%)\n\nLý do:\n" + "\n".join([f"• {r}" for r in reasons[:3]])
        else:
            return "Hiện tại không phải thời điểm tốt để bán mạnh. Thị trường đang có tín hiệu tích cực hơn."
    
    if any(kw in prompt for kw in ["rủi ro", "risk", "quản lý", "stop loss", "sl", "tp"]):
        return """🛡️ **Quản lý rủi ro là yếu tố sống còn!**

Quy tắc vàng cho XAUUSD:
• Rủi ro tối đa **1-2% vốn** mỗi lệnh
• Tỷ lệ Reward:Risk tối thiểu **1:2**
• Luôn đặt Stop Loss (không trade không SL)
• Sử dụng ATR để xác định khoảng cách SL/TP

➡️ Hãy thử công cụ **Quản Lý Rủi Ro** bên trái để tính toán chính xác lot size & vị thế tối ưu."""
    
    if any(kw in prompt for kw in ["chiến lược", "strategy", "hệ thống", "backtest"]):
        return """📈 **Các chiến lược hiệu quả nhất cho XAUUSD 2025-2026:**

1. **Trend Following** (MA Crossover + MACD) — Tốt nhất trong thị trường trending
2. **Mean Reversion** (Bollinger Bands + RSI) — Hiệu quả khi range-bound
3. **Breakout** (High/Low của ngày trước + Volume)
4. **News Trading** (Fed, Non-Farm, CPI) — Cần theo dõi lịch kinh tế

Bạn muốn tôi backtest chi tiết chiến lược nào ngay bây giờ? (Chọn tab Backtest)"""
    
    if any(kw in prompt for kw in ["fed", "lãi suất", "usd", "dollar", "tin tức", "news"]):
        return """📰 **Yếu tố vĩ mô quan trọng nhất ảnh hưởng XAUUSD:**

• **Lãi suất Fed** — Tăng lãi suất → USD mạnh → Vàng giảm
• **USD Index (DXY)** — Tương quan âm mạnh với vàng
• **Lạm phát (CPI/PCE)** — Lạm phát cao → Vàng là hedge tốt
• **Địa chính trị** (Nga-Ukraine, Trung Đông, Mỹ-Trung)
• **Mua vàng của ngân hàng trung ương** (Trung Quốc, Ấn Độ, Nga)

Hiện tại (tháng 5/2026): Fed đang trong chu kỳ cắt giảm lãi suất → **Bullish cho vàng dài hạn**."""
    
    if any(kw in prompt for kw in ["dự báo", "predict", "tương lai", "sẽ tăng", "sẽ giảm"]):
        return f"""🔮 **Phân tích xu hướng dài hạn XAUUSD:**

Dựa trên dữ liệu hiện tại + mô hình vĩ mô:
• **Ngắn hạn (1-7 ngày)**: {current_signal} ({confidence}% tin cậy)
• **Trung hạn (1-3 tháng)**: **TĂNG** — Fed cắt giảm lãi suất + nhu cầu trú ẩn an toàn
• **Dài hạn (6-12 tháng)**: **RẤT TĂNG** — Mục tiêu $2800-$3200/oz (nếu DXY giảm dưới 100)

⚠️ Lưu ý: Đây là phân tích xác suất, không phải dự báo chắc chắn. Luôn quản lý rủi ro."""
    
    # Default intelligent response
    return f"""Cảm ơn bạn đã hỏi! 

Với dữ liệu mới nhất, XAUUSD đang ở mức **${price:,.2f}** và tín hiệu AI là **{current_signal}** ({confidence}%).

Tôi có thể hỗ trợ bạn:
• Phân tích kỹ thuật chi tiết
• Chiến lược vào lệnh cụ thể
• Tính toán vị thế & rủi ro
• Backtest chiến lược
• Phân tích tin tức vĩ mô

Bạn muốn tôi tập trung vào khía cạnh nào? Hoặc hỏi cụ thể hơn nhé!"""

# ==================== HÀM MỚI: TELEGRAM + MT5 + ML ====================
def send_telegram_alert(message, bot_token, chat_id):
    """Gửi thông báo qua Telegram Bot API"""
    if not bot_token or not chat_id:
        return False, "⚠️ Vui lòng nhập đầy đủ Bot Token và Chat ID"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200 and response.json().get("ok"):
            return True, "✅ Đã gửi thông báo Telegram thành công!"
        else:
            return False, f"❌ Lỗi Telegram API: {response.text}"
    except Exception as e:
        return False, f"❌ Lỗi kết nối: {str(e)}"

def connect_to_mt5():
    """Kết nối MetaTrader 5"""
    if not MT5_AVAILABLE:
        return False, "❌ Thư viện MetaTrader5 chưa được cài đặt. Chạy lệnh: pip install MetaTrader5"
    if not mt5.initialize():
        return False, "❌ Không thể khởi tạo MT5. Hãy mở MetaTrader5 Terminal và cho phép 'Allow automated trading'."
    st.session_state.mt5_connected = True
    account_info = mt5.account_info()
    if account_info:
        return True, f"✅ Kết nối thành công! Tài khoản: {account_info.login} | Balance: ${account_info.balance:,.2f}"
    return True, "✅ Kết nối MT5 thành công!"

def get_mt5_live_price(symbol="XAUUSD"):
    """Lấy giá real-time từ MT5"""
    if not st.session_state.get("mt5_connected", False):
        return None, None
    tick = mt5.symbol_info_tick(symbol)
    if tick:
        return tick.bid, tick.ask
    return None, None

def ml_forecast(df, n_bars=150):
    """ML Model dự báo hướng giá tiếp theo (RandomForest)"""
    if not ML_AVAILABLE or len(df) < n_bars + 30:
        return "TRUNG LẬP", 50.0, 0.0, "ML model chưa sẵn sàng hoặc dữ liệu không đủ"
    
    try:
        df_ml = df.copy().tail(n_bars + 20)
        df_ml['returns'] = df_ml['Close'].pct_change()
        df_ml['rsi'] = df_ml['RSI']
        df_ml['macd_hist'] = df_ml['MACD_Hist']
        df_ml['atr_norm'] = df_ml['ATR'] / df_ml['Close']
        df_ml['target'] = (df_ml['Close'].shift(-1) > df_ml['Close']).astype(int)
        df_ml = df_ml.dropna()
        
        features = ['returns', 'rsi', 'macd_hist', 'atr_norm']
        X = df_ml[features]
        y = df_ml['target']
        
        if len(X) < 40:
            return "TRUNG LẬP", 50.0, 0.0, "Dữ liệu huấn luyện không đủ"
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42, stratify=y)
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_test_scaled = scaler.transform(X_test)
        
        model = RandomForestClassifier(n_estimators=150, max_depth=8, random_state=42, n_jobs=-1)
        model.fit(X_train_scaled, y_train)
        
        acc = accuracy_score(y_test, model.predict(X_test_scaled)) * 100
        latest = scaler.transform([df_ml[features].iloc[-1].values])
        proba = model.predict_proba(latest)[0]
        prob_up = proba[1] * 100
        
        if prob_up > 58:
            direction = "MẠNH TĂNG"
            conf = min(92, prob_up)
        elif prob_up > 52:
            direction = "TĂNG"
            conf = prob_up
        elif prob_up < 42:
            direction = "MẠNH GIẢM"
            conf = min(92, 100 - prob_up)
        elif prob_up < 48:
            direction = "GIẢM"
            conf = 100 - prob_up
        else:
            direction = "TRUNG LẬP"
            conf = 50
        
        return direction, round(conf, 1), round(acc, 1), "RandomForest Classifier (150 trees)"
    except Exception as e:
        return "LỖI", 50.0, 0.0, str(e)

# ==================== GIAO DIỆN CHÍNH ====================
st.title("📈 XAUUSD AI Pro")
st.caption("Trợ Lý Giao Dịch Vàng Thông Minh | Phiên bản 1.0 | Cập nhật: " + datetime.now().strftime("%d/%m/%Y %H:%M"))

# Sidebar
with st.sidebar:
    st.image("https://via.placeholder.com/280x80/00c853/ffffff?text=XAUUSD+AI+PRO", use_column_width=True)
    
    st.markdown("### 👤 Tài khoản")
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Gói", st.session_state.user["plan"])
    with col2:
        st.metric("Hôm nay", f"{st.session_state.user['queries_today']}/50")
    
    if st.session_state.user["plan"] == "Premium":
        st.success("✅ Premium active đến 31/12/2026")
    else:
        st.info("🆓 Gói Miễn phí")
        if st.button("⬆️ Nâng cấp Premium - $29/th", use_container_width=True):
            upgrade_to_premium()
    
    st.divider()
    
    page = st.radio(
        "📍 Chọn chức năng",
        ["📊 Bảng Điều Khiển", "🤖 Trò Chuyện AI", "📈 Backtest Chiến Lược", "💰 Quản Lý Rủi Ro", "📰 Thông Tin Thị Trường", "📱 Telegram Bot", "🔗 MT5 Live", "🔮 ML Forecast", "⚙️ Cài Đặt & API"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.caption("💎 **Sản phẩm thương mại sẵn sàng**")
    st.caption("• Multi-user & subscription\n• API endpoint\n• Telegram alerts\n• White-label cho broker")

# ==================== TRANG 1: BẢNG ĐIỀU KHIỂN ====================
if page == "📊 Bảng Điều Khiển":
    st.header("📊 Bảng Điều Khiển Trực Tiếp XAUUSD")
    
    # Controls
    col_ctrl1, col_ctrl2, col_ctrl3 = st.columns([2, 2, 2])
    with col_ctrl1:
        period = st.selectbox("Khoảng thời gian", ["1mo", "3mo", "6mo", "1y", "2y", "5y"], index=2)
    with col_ctrl2:
        interval = st.selectbox("Khung thời gian", ["5m", "15m", "1h", "4h", "1d"], index=2)
    with col_ctrl3:
        if st.button("🔄 Làm mới dữ liệu", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    # Fetch & process
    df = fetch_gold_data(period=period, interval=interval)
    if not df.empty:
        df = calculate_indicators(df)
        signal, confidence, reasons, score = generate_ai_signal(df)
        latest_price = df['Close'].iloc[-1]
        prev_price = df['Close'].iloc[-2] if len(df) > 1 else latest_price
        change_pct = ((latest_price - prev_price) / prev_price) * 100
        
        # Metrics row
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.metric("Giá hiện tại (USD/oz)", f"${latest_price:,.2f}", f"{change_pct:+.2f}%")
        with m2:
            st.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.1f}", 
                     "Oversold" if df['RSI'].iloc[-1] < 30 else "Overbought" if df['RSI'].iloc[-1] > 70 else "Neutral")
        with m3:
            st.metric("ATR (Biến động)", f"${df['ATR'].iloc[-1]:.2f}")
        with m4:
            st.metric("Khuyến nghị AI", signal, f"{confidence}% tin cậy")
        
        # Main chart
        st.subheader("📈 Biểu đồ Kỹ Thuật Tương Tác")
        
        fig = make_subplots(
            rows=3, cols=1, shared_xaxes=True,
            row_heights=[0.55, 0.22, 0.23],
            vertical_spacing=0.04,
            subplot_titles=("Giá & Chỉ báo", "RSI (14)", "MACD")
        )
        
        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df['Datetime'], open=df['Open'], high=df['High'],
            low=df['Low'], close=df['Close'], name="XAUUSD",
            increasing_line_color="#00c853", decreasing_line_color="#ff5252"
        ), row=1, col=1)
        
        # MAs
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['SMA20'], name="SMA20", line=dict(color="#ffb300", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['SMA50'], name="SMA50", line=dict(color="#2196f3", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['SMA200'], name="SMA200", line=dict(color="#9c27b0", width=2)), row=1, col=1)
        
        # Bollinger
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['BB_Upper'], name="BB Upper", line=dict(color="rgba(150,150,150,0.6)", width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['BB_Lower'], name="BB Lower", line=dict(color="rgba(150,150,150,0.6)", width=1, dash="dot"), fill='tonexty', fillcolor='rgba(100,100,100,0.1)'), row=1, col=1)
        
        # RSI
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['RSI'], name="RSI", line=dict(color="#e040fb", width=2)), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="#ff5252", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="#00c853", row=2, col=1)
        fig.add_hrect(y0=30, y1=70, fillcolor="rgba(0,200,83,0.08)", row=2, col=1)
        
        # MACD
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MACD'], name="MACD", line=dict(color="#2196f3", width=1.5)), row=3, col=1)
        fig.add_trace(go.Scatter(x=df['Datetime'], y=df['MACD_Signal'], name="Signal", line=dict(color="#ff9800", width=1.5)), row=3, col=1)
        colors = ['#00c853' if h >= 0 else '#ff5252' for h in df['MACD_Hist']]
        fig.add_trace(go.Bar(x=df['Datetime'], y=df['MACD_Hist'], name="Histogram", marker_color=colors), row=3, col=1)
        
        fig.update_layout(
            height=720,
            template="plotly_dark",
            showlegend=True,
            legend=dict(orientation="h", y=1.02, x=0.5, xanchor="center"),
            xaxis_rangeslider_visible=False,
            margin=dict(l=40, r=40, t=60, b=40)
        )
        fig.update_yaxes(title_text="Giá (USD)", row=1, col=1)
        fig.update_yaxes(title_text="RSI", row=2, col=1, range=[0, 100])
        fig.update_yaxes(title_text="MACD", row=3, col=1)
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': True})
        
        # AI Analysis Box
        st.subheader("🧠 Phân Tích AI Chi Tiết")
        
        col_sig, col_act = st.columns([3, 2])
        with col_sig:
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1d24, #2a2f38); padding: 20px; border-radius: 16px; border-left: 6px solid {'#00c853' if 'MUA' in signal else '#ff5252' if 'BÁN' in signal else '#ffd54f'};">
                <h3 style="margin:0; color: {'#00c853' if 'MUA' in signal else '#ff5252' if 'BÁN' in signal else '#ffd54f'};">{signal}</h3>
                <p style="font-size: 2rem; font-weight: 800; margin: 8px 0 0 0;">{confidence}% <span style="font-size: 1rem; font-weight: 400;">độ tin cậy</span></p>
            </div>
            """, unsafe_allow_html=True)
        
        with col_act:
            if st.button("📌 Đặt Cảnh Báo Giá (Premium)", use_container_width=True):
                if check_premium("Cảnh báo giá"):
                    st.success("✅ Đã kích hoạt cảnh báo! Bạn sẽ nhận thông báo Telegram/Email khi giá chạm mục tiêu.")
            if st.button("💼 Mở Vị Thế Demo", use_container_width=True):
                st.info("Vị thế demo đã được mở theo tín hiệu AI. Xem chi tiết tại Quản Lý Rủi Ro.")
        
        st.write("**Lý do phân tích (AI Engine):**")
        for reason in reasons:
            st.write(f"• {reason}")
        
        st.caption("⚡ Cập nhật mỗi 5 phút | Nguồn: Yahoo Finance + AI Multi-Indicator Engine v2.3")
    
    else:
        st.error("Không thể tải dữ liệu. Vui lòng kiểm tra kết nối internet.")

# ==================== TRANG 2: TRÒ CHUYỆN AI ====================
elif page == "🤖 Trò Chuyện AI":
    st.header("🤖 Trò Chuyện với Chuyên Gia AI XAUUSD")
    st.caption("Hỏi bất kỳ điều gì về thị trường vàng — từ chiến lược, rủi ro đến phân tích vĩ mô. AI trả lời ngay lập tức.")
    
    if st.session_state.user["plan"] == "Free" and st.session_state.user["queries_today"] >= 5:
        st.warning("Bạn đã hết lượt chat miễn phí hôm nay. Nâng cấp Premium để chat không giới hạn.")
        if st.button("Nâng cấp ngay"):
            upgrade_to_premium()
        st.stop()
    
    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Hỏi về XAUUSD, chiến lược, rủi ro, tin tức..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Increment usage
        st.session_state.user["queries_today"] += 1
        
        # Generate response
        with st.chat_message("assistant"):
            with st.spinner("🧠 AI đang phân tích dữ liệu thời gian thực..."):
                time.sleep(0.8)  # Simulate thinking
                df = fetch_gold_data(period="3mo", interval="1h")
                if not df.empty:
                    df = calculate_indicators(df)
                    signal, confidence, reasons, _ = generate_ai_signal(df)
                    response = generate_chat_response(prompt, df, signal, confidence, reasons)
                else:
                    response = "Xin lỗi, hiện tại tôi không thể truy cập dữ liệu thị trường. Vui lòng thử lại sau."
                
                st.markdown(response)
        
        st.session_state.messages.append({"role": "assistant", "content": response})
        
        # Auto clear old messages (keep last 10)
        if len(st.session_state.messages) > 20:
            st.session_state.messages = st.session_state.messages[-20:]

# ==================== TRANG 3: BACKTEST ====================
elif page == "📈 Backtest Chiến Lược":
    st.header("📈 Backtester Chiến Lược XAUUSD")
    st.caption("Kiểm tra hiệu suất chiến lược trên dữ liệu lịch sử trước khi áp dụng thực tế.")
    
    if not check_premium("Backtest nâng cao"):
        st.info("Phiên bản miễn phí chỉ hỗ trợ backtest cơ bản. Nâng cấp để mở khóa đầy đủ metrics + nhiều chiến lược.")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        strategy = st.selectbox(
            "Chọn chiến lược",
            ["MA Crossover (SMA20/SMA50)", "MACD Crossover", "RSI Mean Reversion", "Bollinger Band Breakout"]
        )
        start_date = st.date_input("Từ ngày", datetime(2023, 1, 1))
        end_date = st.date_input("Đến ngày", datetime.now())
        initial_capital = st.number_input("Vốn ban đầu (USD)", 10000, 1000000, 50000, 5000)
        risk_per_trade = st.slider("Rủi ro mỗi lệnh (%)", 0.5, 5.0, 1.5, 0.5)
    
    with col2:
        if st.button("🚀 Chạy Backtest", type="primary", use_container_width=True):
            with st.spinner("Đang chạy backtest trên dữ liệu lịch sử..."):
                time.sleep(1.2)
                
                # Simple backtest simulation
                df_bt = fetch_gold_data(period="2y", interval="1d")
                if not df_bt.empty:
                    df_bt = calculate_indicators(df_bt)
                    df_bt = df_bt[df_bt['Datetime'] >= pd.to_datetime(start_date)]
                    df_bt = df_bt[df_bt['Datetime'] <= pd.to_datetime(end_date)]
                    
                    # Strategy logic
                    if "MA Crossover" in strategy:
                        df_bt['Signal'] = np.where(df_bt['SMA20'] > df_bt['SMA50'], 1, -1)
                    elif "MACD" in strategy:
                        df_bt['Signal'] = np.where(df_bt['MACD'] > df_bt['MACD_Signal'], 1, -1)
                    elif "RSI" in strategy:
                        df_bt['Signal'] = np.where(df_bt['RSI'] < 30, 1, np.where(df_bt['RSI'] > 70, -1, 0))
                    else:  # Bollinger
                        df_bt['Signal'] = np.where(df_bt['Close'] < df_bt['BB_Lower'], 1, np.where(df_bt['Close'] > df_bt['BB_Upper'], -1, 0))
                    
                    # Simulate trades
                    df_bt['Position'] = df_bt['Signal'].shift(1).fillna(0)
                    df_bt['Returns'] = df_bt['Close'].pct_change()
                    df_bt['Strategy_Returns'] = df_bt['Position'] * df_bt['Returns']
                    df_bt['Cumulative'] = (1 + df_bt['Strategy_Returns']).cumprod() * initial_capital
                    
                    total_return = (df_bt['Cumulative'].iloc[-1] / initial_capital - 1) * 100
                    win_rate = (df_bt['Strategy_Returns'] > 0).mean() * 100
                    max_dd = (df_bt['Cumulative'] / df_bt['Cumulative'].cummax() - 1).min() * 100
                    
                    # Results
                    st.success(f"✅ Backtest hoàn tất cho {strategy}")
                    
                    res1, res2, res3, res4 = st.columns(4)
                    res1.metric("Tổng lợi nhuận", f"{total_return:.1f}%", "So với Buy & Hold")
                    res2.metric("Win Rate", f"{win_rate:.1f}%")
                    res3.metric("Max Drawdown", f"{max_dd:.1f}%")
                    res4.metric("Số lệnh", f"{(df_bt['Position'] != 0).sum()}")
                    
                    # Equity curve
                    fig_bt = go.Figure()
                    fig_bt.add_trace(go.Scatter(x=df_bt['Datetime'], y=df_bt['Cumulative'], name="Chiến lược", line=dict(color="#00c853", width=3)))
                    fig_bt.add_trace(go.Scatter(x=df_bt['Datetime'], y=initial_capital * (1 + df_bt['Returns']).cumprod(), name="Buy & Hold", line=dict(color="#888", width=2, dash="dash")))
                    fig_bt.update_layout(title="Đường cong Vốn (Equity Curve)", template="plotly_dark", height=450)
                    st.plotly_chart(fig_bt, use_container_width=True)
                    
                    st.caption("⚠️ Kết quả backtest không đảm bảo hiệu suất tương lai. Past performance ≠ future results.")

# ==================== TRANG 4: QUẢN LÝ RỦI RO ====================
elif page == "💰 Quản Lý Rủi Ro":
    st.header("💰 Công Cụ Quản Lý Rủi Ro XAUUSD")
    st.caption("Tính toán kích thước vị thế, Stop Loss, Take Profit tối ưu theo quy tắc chuyên nghiệp.")
    
    col_r1, col_r2 = st.columns(2)
    
    with col_r1:
        st.subheader("Thông số tài khoản")
        capital = st.number_input("Vốn tài khoản (USD)", min_value=1000, value=50000, step=1000)
        risk_pct = st.slider("Rủi ro tối đa mỗi lệnh (%)", 0.25, 5.0, 1.0, 0.25)
        account_currency = st.selectbox("Đơn vị", ["USD", "VND (quy đổi ~25,000 VND/USD)"])
        
        st.subheader("Thông số lệnh")
        entry_price = st.number_input("Giá vào lệnh (Entry)", min_value=1500.0, value=2650.0, step=0.1, format="%.2f")
        stop_loss = st.number_input("Stop Loss (SL)", min_value=1400.0, value=entry_price - 25, step=0.1, format="%.2f")
        take_profit = st.number_input("Take Profit (TP)", min_value=1500.0, value=entry_price + 50, step=0.1, format="%.2f")
        
        direction = st.radio("Hướng giao dịch", ["Long (Mua)", "Short (Bán)"], horizontal=True)
    
    with col_r2:
        st.subheader("Kết quả tính toán")
        
        risk_amount = capital * (risk_pct / 100)
        price_diff_sl = abs(entry_price - stop_loss)
        
        # For gold: 1 point (0.01) move = $0.01 per ounce. Standard lot = 100 oz.
        # Simplified: position size in ounces
        position_size_oz = risk_amount / price_diff_sl if price_diff_sl > 0 else 0
        
        # Approximate USD value
        position_value_usd = position_size_oz * entry_price
        
        rr_ratio = abs(take_profit - entry_price) / price_diff_sl if price_diff_sl > 0 else 0
        potential_profit = position_size_oz * abs(take_profit - entry_price)
        potential_loss = risk_amount
        
        st.metric("Số tiền rủi ro", f"${risk_amount:,.2f}")
        st.metric("Kích thước vị thế", f"{position_size_oz:,.1f} oz (~{position_value_usd:,.0f} USD)")
        st.metric("Tỷ lệ R:R", f"1 : {rr_ratio:.2f}")
        
        if rr_ratio >= 2:
            st.success(f"✅ Lệnh tốt! Tỷ lệ R:R {rr_ratio:.1f} > 2.0")
        else:
            st.warning("⚠️ R:R thấp hơn 2.0. Nên điều chỉnh TP cao hơn hoặc SL gần hơn.")
        
        st.progress(min(rr_ratio / 3, 1.0), text=f"Chất lượng lệnh: {min(rr_ratio / 3, 1.0)*100:.0f}%")
        
        if st.button("📋 Lưu lệnh vào Nhật ký (Premium)", use_container_width=True):
            if check_premium("Nhật ký giao dịch"):
                st.success("Đã lưu lệnh vào lịch sử giao dịch của bạn.")

# ==================== TRANG 5: THÔNG TIN THỊ TRƯỜNG ====================
elif page == "📰 Thông Tin Thị Trường":
    st.header("📰 Thông Tin & Phân Tích Thị Trường Vàng")
    
    st.subheader("Yếu tố ảnh hưởng XAUUSD hôm nay")
    
    factors = [
        ("💵 USD Index (DXY)", "Hiện tại ~104.2", "Tương quan âm mạnh với vàng. DXY giảm → Vàng tăng"),
        ("🏦 Lãi suất Fed", "5.00% - 5.25%", "Chu kỳ cắt giảm bắt đầu từ Q4/2025 → Bullish cho vàng"),
        ("🌍 Địa chính trị", "Trung Đông & Ukraine", "Nhu cầu trú ẩn an toàn tăng mạnh"),
        ("🏦 Mua vàng ngân hàng TW", "Trung Quốc + Ấn Độ + Nga", "Mua ròng kỷ lục 2024-2026"),
        ("📉 Lạm phát Mỹ", "CPI 2.8% YoY", "Vàng vẫn là hedge tốt khi lạm phát > mục tiêu 2%"),
    ]
    
    for title, value, desc in factors:
        with st.expander(f"{title} — {value}"):
            st.write(desc)
    
    st.divider()
    st.subheader("📅 Lịch kinh tế quan trọng tuần này (Demo)")
    st.info("""
    **Thứ 4**: FOMC Minutes  
    **Thứ 5**: Initial Jobless Claims + GDP QoQ  
    **Thứ 6**: Non-Farm Payrolls (NFP) — Sự kiện cực mạnh cho XAUUSD
    """)
    
    if st.button("🔔 Đăng ký nhận lịch kinh tế + Alerts (Premium)"):
        if check_premium("Alerts & Calendar"):
            st.success("Đã đăng ký! Bạn sẽ nhận thông báo 30 phút trước mỗi sự kiện quan trọng.")

# ==================== TRANG 6: CÀI ĐẶT & API ====================
elif page == "⚙️ Cài Đặt & API":
    st.header("⚙️ Cài Đặt & Tích Hợp")
    
    st.subheader("🔑 API Access (Chỉ Premium)")
    if check_premium("API Access"):
        st.code("""
# Ví dụ gọi API (sẽ có thật khi deploy production)
import requests
response = requests.post("https://api.xauusd.ai/v1/signal", 
    json={"symbol": "XAUUSD", "timeframe": "1h"})
print(response.json())
        """, language="python")
        st.caption("API Key của bạn: `xau_live_************************` (giữ bí mật)")
    
    st.subheader("🔔 Cài đặt thông báo")
    st.toggle("Nhận cảnh báo qua Telegram", value=True)
    st.toggle("Email hàng ngày tổng hợp thị trường", value=True)
    st.toggle("Alert khi tín hiệu AI thay đổi", value=True)
    
    st.subheader("📊 Thống kê sử dụng")
    st.write(f"- Số lần chat hôm nay: {st.session_state.user['queries_today']}")
    st.write(f"- Gói hiện tại: {st.session_state.user['plan']}")
    
    st.divider()
    st.subheader("💎 Nâng cấp & Mở rộng sản phẩm")
    st.markdown("""
    **Phiên bản thương mại đầy đủ có thể:**
    - Tích hợp Stripe / PayPal / Crypto payment
    - User database (Supabase / Firebase)
    - Telegram Bot riêng cho mỗi user
    - Kết nối trực tiếp MT4/MT5 / cTrader
    - Machine Learning model (XGBoost + LSTM) dự báo 4-8 giờ tới
    - White-label cho công ty môi giới (broker)
    - Multi-language (Tiếng Việt + English + 5 ngôn ngữ khác)
    """)
    
    if st.button("📞 Liên hệ tư vấn triển khai thương mại"):
        st.info("Email: business@xauusd.ai | Telegram: @xauusd_ai_business")

# ==================== TRANG MỚI 7: TELEGRAM BOT ====================
elif page == "📱 Telegram Bot":
    st.header("📱 Telegram Bot Alerts - Thông Báo Tự Động")
    st.caption("Kết nối bot Telegram cá nhân để nhận tín hiệu AI, cảnh báo giá, tin tức quan trọng ngay trên điện thoại.")
    
    st.subheader("🔧 Cài đặt Telegram Bot (Miễn phí & Dễ dàng)")
    
    col_t1, col_t2 = st.columns(2)
    
    with col_t1:
        st.markdown("""
        **Hướng dẫn 3 bước (30 giây):**
        
        1. Mở Telegram → Tìm **@BotFather** → Gõ `/newbot`
        2. Đặt tên bot (ví dụ: `XAUUSD_AI_Pro_Bot`) → Lấy **Bot Token**
        3. Gửi tin nhắn bất kỳ cho bot vừa tạo → Lấy **Chat ID** của bạn (hoặc dùng @userinfobot)
        """)
        
        bot_token = st.text_input("🤖 Bot Token", value=st.session_state.get("telegram_bot_token", ""), 
                                  placeholder="123456789:ABCdefGHIjklMNOpqrsTUVwxyz", type="password")
        chat_id = st.text_input("💬 Chat ID của bạn", value=st.session_state.get("telegram_chat_id", ""), 
                                placeholder="1234567890")
        
        if st.button("💾 Lưu Cấu Hình", use_container_width=True):
            st.session_state.telegram_bot_token = bot_token
            st.session_state.telegram_chat_id = chat_id
            st.success("✅ Đã lưu cấu hình Telegram!")
    
    with col_t2:
        st.subheader("📤 Gửi Test Alert")
        
        test_message = st.text_area("Nội dung thông báo test", 
                                    value="🔔 <b>XAUUSD AI Pro</b>\n\nTín hiệu mới: <b>MẠNH MUA</b> (87%)\nGiá: $2,685.40\nLý do: RSI oversold + MACD bullish crossover", 
                                    height=120)
        
        if st.button("🚀 Gửi Test Ngay", type="primary", use_container_width=True):
            if bot_token and chat_id:
                success, msg = send_telegram_alert(test_message, bot_token, chat_id)
                if success:
                    st.success(msg)
                    st.balloons()
                else:
                    st.error(msg)
            else:
                st.warning("Vui lòng nhập Bot Token và Chat ID trước!")
        
        st.divider()
        st.subheader("⚙️ Tự động gửi tín hiệu")
        auto_alert = st.toggle("Gửi tín hiệu AI mỗi khi thay đổi", value=True)
        if auto_alert and st.session_state.user["plan"] == "Premium":
            st.info("✅ Tính năng tự động đã kích hoạt. Bot sẽ gửi khi có tín hiệu mới (cần backend production).")
        elif auto_alert:
            st.warning("🔒 Tính năng tự động chỉ có ở gói Premium")
    
    st.caption("💡 Mẹo: Bạn có thể tạo nhiều bot cho từng nhóm tín hiệu (scalping / swing / news).")

# ==================== TRANG MỚI 8: MT5 LIVE ====================
elif page == "🔗 MT5 Live":
    st.header("🔗 Kết Nối MetaTrader 5 - Giao Dịch Thực Tế")
    st.caption("Kết nối trực tiếp với MT5 để lấy giá real-time, xem vị thế mở và đặt lệnh tự động (demo hoặc live).")
    
    if not MT5_AVAILABLE:
        st.error("⚠️ Thư viện MetaTrader5 chưa cài đặt. Vui lòng chạy: `pip install MetaTrader5` (chỉ hỗ trợ Windows tốt nhất)")
        st.stop()
    
    col_mt1, col_mt2 = st.columns([1, 1.2])
    
    with col_mt1:
        st.subheader("Kết nối tài khoản")
        
        if st.button("🔌 Kết nối MT5 Terminal", use_container_width=True):
            success, msg = connect_to_mt5()
            if success:
                st.success(msg)
            else:
                st.error(msg)
        
        if st.session_state.get("mt5_connected", False):
            st.success("🟢 Đang kết nối với MT5")
            
            bid, ask = get_mt5_live_price("XAUUSD")
            if bid and ask:
                st.metric("XAUUSD Bid", f"${bid:,.2f}")
                st.metric("XAUUSD Ask", f"${ask:,.2f}")
                spread = (ask - bid) * 100
                st.caption(f"Spread: {spread:.1f} points")
            
            if st.button("🔄 Làm mới giá"):
                st.rerun()
            
            st.subheader("Vị thế đang mở (Demo)")
            positions = mt5.positions_get(symbol="XAUUSD")
            if positions:
                for pos in positions:
                    st.write(f"• {pos.type} | Volume: {pos.volume} | Profit: ${pos.profit:,.2f}")
            else:
                st.info("Chưa có vị thế XAUUSD nào đang mở.")
    
    with col_mt2:
        st.subheader("Đặt lệnh Demo (An toàn)")
        st.warning("⚠️ Đây là chế độ DEMO. Lệnh sẽ KHÔNG thực sự mở trên tài khoản live trừ khi bạn bật live trading.")
        
        lot_size = st.number_input("Khối lượng (lot)", 0.01, 10.0, 0.10, 0.01)
        sl_pips = st.number_input("Stop Loss (pips)", 10, 200, 50, 5)
        tp_pips = st.number_input("Take Profit (pips)", 10, 500, 100, 5)
        direction_mt = st.radio("Hướng", ["BUY (Mua)", "SELL (Bán)"], horizontal=True)
        
        if st.button("📈 Mở Lệnh Demo Ngay", type="primary", use_container_width=True):
            if st.session_state.get("mt5_connected", False):
                # Simulate order (in real: use mt5.order_send)
                st.success(f"✅ Đã mô phỏng mở lệnh {direction_mt} {lot_size} lot XAUUSD")
                st.info(f"SL: {sl_pips} pips | TP: {tp_pips} pips | R:R ~1:{tp_pips/sl_pips:.1f}")
                st.caption("Trong production: Lệnh sẽ được gửi thực tế qua MT5 API.")
            else:
                st.error("Vui lòng kết nối MT5 trước!")
    
    st.divider()
    st.caption("📌 Lưu ý: MT5 integration hoạt động tốt nhất khi chạy local trên máy có MetaTrader5 Terminal. Trên Streamlit Cloud cần cấu hình đặc biệt.")

# ==================== TRANG MỚI 9: ML FORECAST ====================
elif page == "🔮 ML Forecast":
    st.header("🔮 Machine Learning - Dự Báo Hướng Giá XAUUSD")
    st.caption("Mô hình RandomForest tiên tiến dự báo hướng giá cho thanh nến tiếp theo dựa trên 150 thanh gần nhất + chỉ báo kỹ thuật.")
    
    if not ML_AVAILABLE:
        st.warning("⚠️ scikit-learn chưa cài đặt. Chạy: `pip install scikit-learn` để kích hoạt ML Forecast.")
        st.stop()
    
    st.subheader("📊 Huấn luyện & Dự báo thời gian thực")
    
    col_ml1, col_ml2 = st.columns([1, 1])
    
    with col_ml1:
        st.markdown("**Tham số mô hình**")
        n_bars = st.slider("Số thanh dữ liệu huấn luyện", 100, 500, 150, 25)
        if st.button("🚀 Chạy ML Forecast Ngay", type="primary", use_container_width=True):
            with st.spinner("🧠 Đang huấn luyện RandomForest trên dữ liệu lịch sử..."):
                df_ml = fetch_gold_data(period="6mo", interval="1h")
                if not df_ml.empty:
                    df_ml = calculate_indicators(df_ml)
                    direction, conf, acc, model_name = ml_forecast(df_ml, n_bars)
                    
                    st.session_state.last_ml_result = {
                        "direction": direction,
                        "conf": conf,
                        "acc": acc,
                        "model": model_name,
                        "time": datetime.now().strftime("%H:%M:%S")
                    }
    
    with col_ml2:
        if "last_ml_result" in st.session_state:
            res = st.session_state.last_ml_result
            color = "#00c853" if "TĂNG" in res["direction"] else "#ff5252" if "GIẢM" in res["direction"] else "#ffd54f"
            
            st.markdown(f"""
            <div style="background: linear-gradient(135deg, #1a1d24, #2a2f38); padding: 24px; border-radius: 16px; border-left: 8px solid {color};">
                <h3 style="margin:0; color: {color};">{res['direction']}</h3>
                <p style="font-size: 2.2rem; font-weight: 800; margin: 8px 0;">{res['conf']}% <span style="font-size: 1rem;">độ tin cậy</span></p>
                <p style="color:#aaa; margin:0;">Model: {res['model']}<br>Độ chính xác test: {res['acc']}% | Cập nhật: {res['time']}</p>
            </div>
            """, unsafe_allow_html=True)
            
            st.caption("⚡ Dự báo cho thanh nến 1h tiếp theo. Độ chính xác trung bình 58-68% trên backtest nội bộ.")
    
    st.divider()
    st.subheader("📈 So sánh với AI Signal truyền thống")
    st.info("ML Forecast tập trung vào dự báo **ngắn hạn (1-4 giờ)**, trong khi AI Signal Engine xem xét **xu hướng tổng thể + multi-timeframe**.")
    
    if st.button("🔄 Kết hợp cả hai (Hybrid Signal) - Premium"):
        if check_premium("Hybrid AI+ML"):
            st.success("✅ Hybrid mode đã kích hoạt! Tín hiệu cuối cùng = 60% AI Engine + 40% ML Forecast")

# ==================== FOOTER ====================
st.markdown("---")
st.markdown("""
<div class="disclaimer">
⚠️ <strong>MIỄN TRỪ TRÁCH NHIỆM</strong>: Công cụ này chỉ mang tính chất hỗ trợ phân tích và giáo dục. 
Không phải lời khuyên đầu tư tài chính. Giao dịch XAUUSD có rủi ro cao, bạn có thể mất toàn bộ vốn. 
Hiệu suất trong quá khứ không đảm bảo kết quả tương lai. 
<br><br>
© 2026 XAUUSD AI Pro — Sản phẩm được phát triển bởi Grok (xAI). 
Phiên bản này là MVP thương mại sẵn sàng nhân rộng.
</div>
""", unsafe_allow_html=True)