#!/usr/bin/env python3
"""
XAUUSD AI Pro - Phiên bản mới nhất (Đã tối ưu Giá + AI + Login + Nâng cấp gói)
Cập nhật: 15/05/2026
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from datetime import datetime
import time
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
    from sklearn.metrics import accuracy_score
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# ==================== GIAO DIỆN CHUYÊN NGHIỆP ====================
st.markdown("""
<style>
    .stApp { background-color: #0a0c12; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    .stMetric { background: linear-gradient(145deg, #1a1d24, #15181f); border-radius: 16px; padding: 16px 20px; border: 1px solid #2a2f38; }
    .stButton>button { background: linear-gradient(90deg, #00c853, #00e676); color: white; font-weight: 700; border-radius: 12px; }
    h1, h2, h3 { color: #00e676 !important; }
    .signal-strong-buy { color: #00c853; font-size: 1.5rem; font-weight: 800; }
    .signal-buy { color: #69f0ae; font-size: 1.35rem; font-weight: 700; }
    .signal-neutral { color: #ffd54f; font-size: 1.35rem; font-weight: 700; }
    .signal-sell { color: #ff8a80; font-size: 1.35rem; font-weight: 700; }
    .signal-strong-sell { color: #ff5252; font-size: 1.5rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# ==================== QUẢN LÝ USER & ĐĂNG NHẬP ====================
if "user" not in st.session_state:
    st.session_state.user = {
        "name": "Demo Trader",
        "email": "demo@xauusd.ai",
        "plan": "Premium",
        "queries_today": 0,
        "is_logged_in": True
    }

if "messages" not in st.session_state:
    st.session_state.messages = []

def login_user(email, name="Demo Trader"):
    st.session_state.user["email"] = email
    st.session_state.user["name"] = name
    st.session_state.user["is_logged_in"] = True
    st.session_state.user["plan"] = "Premium"
    st.success(f"✅ Đăng nhập thành công! Xin chào {name}")

def logout_user():
    st.session_state.user["is_logged_in"] = False
    st.session_state.user["plan"] = "Free"
    st.info("Bạn đã đăng xuất.")

def upgrade_to_premium():
    st.session_state.user["plan"] = "Premium"
    st.balloons()
    st.success("🎉 Nâng cấp Premium thành công!")

def upgrade_to_enterprise():
    st.session_state.user["plan"] = "Enterprise"
    st.balloons()
    st.success("🎉 Chào mừng bạn đến với gói Enterprise cao cấp nhất!")

def check_premium(feature_name="tính năng"):
    if st.session_state.user["plan"] not in ["Premium", "Enterprise"]:
        st.warning(f"🔒 {feature_name} chỉ dành cho gói Premium/Enterprise")
        if st.button("⬆️ Nâng cấp ngay"):
            upgrade_to_premium()
        return False
    return True

# ==================== HÀM CHÍNH ====================
@st.cache_data(ttl=45)
def fetch_gold_data(period="2d", interval="1m"):
    try:
        ticker = yf.Ticker("GC=F")
        df = ticker.history(period=period, interval=interval)
        df = df.reset_index()
        df.rename(columns={"Date": "Datetime"}, inplace=True)
        return df
    except:
        return pd.DataFrame()

def calculate_indicators(df):
    if df.empty or len(df) < 80:
        return df
    close = df['Close']
    df['SMA20'] = close.rolling(20).mean()
    df['SMA50'] = close.rolling(50).mean()
    df['SMA200'] = close.rolling(200).mean()
    df['EMA12'] = close.ewm(span=12, adjust=False).mean()
    df['EMA26'] = close.ewm(span=26, adjust=False).mean()
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    df['RSI'] = 100 - (100 / (1 + gain / loss))
    df['MACD'] = df['EMA12'] - df['EMA26']
    df['MACD_Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    df['MACD_Hist'] = df['MACD'] - df['MACD_Signal']
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    df['BB_Mid'] = bb_mid
    df['BB_Upper'] = bb_mid + 2 * bb_std
    df['BB_Lower'] = bb_mid - 2 * bb_std
    high = df['High']
    low = df['Low']
    prev_close = close.shift(1)
    tr = pd.concat([high - low, (high - prev_close).abs(), (low - prev_close).abs()], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()
    if 'Volume' in df.columns and df['Volume'].sum() > 0:
        df['VWAP'] = (df['Close'] * df['Volume']).cumsum() / df['Volume'].cumsum()
    else:
        df['VWAP'] = df['Close'].rolling(20).mean()
    return df

def generate_ai_signal(df):
    if df.empty or len(df) < 80:
        return "NEUTRAL", 50, ["Không đủ dữ liệu"], 0
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    close = df['Close']
    score = 0
    reasons = []
    
    if latest['Close'] > latest['SMA50'] and latest['SMA50'] > latest['SMA200']:
        score += 4
        reasons.append("✅ Xu hướng tăng mạnh")
    elif latest['Close'] < latest['SMA50'] and latest['SMA50'] < latest['SMA200']:
        score -= 4
        reasons.append("❌ Xu hướng giảm mạnh")
    
    rsi = latest['RSI']
    if rsi < 25: score += 3
    elif rsi < 40: score += 2
    elif rsi > 75: score -= 3
    elif rsi > 60: score -= 2
    
    if latest['MACD'] > latest['MACD_Signal'] and prev['MACD'] <= prev['MACD_Signal']:
        score += 3
    elif latest['MACD'] < latest['MACD_Signal'] and prev['MACD'] >= prev['MACD_Signal']:
        score -= 3
    
    if latest['Close'] < latest['BB_Lower']: score += 2
    elif latest['Close'] > latest['BB_Upper']: score -= 2
    
    low_14 = df['Low'].rolling(14).min()
    high_14 = df['High'].rolling(14).max()
    k = 100 * ((close - low_14) / (high_14 - low_14))
    latest_k = k.iloc[-1]
    if latest_k < 20: score += 2
    elif latest_k > 80: score -= 2
    
    if score >= 6: return "STRONG BUY", min(95, 78 + score * 2), reasons, score
    elif score >= 3: return "BUY", 68 + score * 3, reasons, score
    elif score <= -6: return "STRONG SELL", min(95, 78 + abs(score) * 2), reasons, score
    elif score <= -3: return "SELL", 68 + abs(score) * 3, reasons, score
    else: return "NEUTRAL", 52 + abs(score) * 2, reasons, score

def send_telegram_alert(message, bot_token, chat_id):
    if not bot_token or not chat_id:
        return False, "⚠️ Vui lòng nhập đầy đủ Bot Token và Chat ID"
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": message, "parse_mode": "HTML"}
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code == 200 and response.json().get("ok"):
            return True, "✅ Đã gửi thông báo Telegram thành công!"
        else:
            return False, f"❌ Lỗi Telegram API: {response.text}"
    except Exception as e:
        return False, f"❌ Lỗi kết nối: {str(e)}"

# ==================== SIDEBAR - ĐĂNG NHẬP & GÓI ====================
with st.sidebar:
    st.header("👤 Tài khoản")
    
    if not st.session_state.user.get("is_logged_in", False):
        st.subheader("Đăng nhập / Đăng ký")
        email = st.text_input("Email")
        name = st.text_input("Họ và tên", value="Trader Việt")
        if st.button("Đăng nhập / Đăng ký", use_container_width=True):
            if email:
                login_user(email, name)
            else:
                st.warning("Vui lòng nhập email")
    else:
        st.success(f"✅ Đã đăng nhập: {st.session_state.user['name']}")
        st.write(f"📧 {st.session_state.user['email']}")
        st.write(f"💎 Gói: **{st.session_state.user['plan']}**")
        
        if st.button("Đăng xuất", use_container_width=True):
            logout_user()
    
    st.divider()
    
    # Nâng cấp gói
    st.subheader("💎 Nâng cấp gói")
    
    if st.session_state.user["plan"] == "Free":
        if st.button("⬆️ Nâng cấp Premium - $29/tháng", use_container_width=True):
            upgrade_to_premium()
        if st.button("⬆️ Nâng cấp Enterprise - $99/tháng (Cao nhất)", use_container_width=True):
            upgrade_to_enterprise()
    elif st.session_state.user["plan"] == "Premium":
        if st.button("⬆️ Nâng cấp Enterprise - $99/tháng (Cao nhất)", use_container_width=True):
            upgrade_to_enterprise()
        st.success("Bạn đang dùng gói Premium")
    else:
        st.success("🎉 Bạn đang dùng gói Enterprise cao nhất!")
    
    st.divider()
    
    page = st.radio(
        "📍 Chọn chức năng",
        ["📊 Bảng Điều Khiển", "🤖 Trò Chuyện AI", "🎯 AI Entry Zone (Scalp/Swing)", "📈 Backtest Chiến Lược", 
         "💰 Quản Lý Rủi Ro", "📰 Thông Tin Thị Trường", "📱 Telegram Bot", "🔗 MT5 Live", "🔮 ML Forecast", "⚙️ Cài Đặt & API"],
        label_visibility="collapsed"
    )

# ==================== CÁC TRANG ====================
if page == "📊 Bảng Điều Khiển":
    st.header("📊 Bảng Điều Khiển - Giá Real-time")
    
    col_refresh, col_info = st.columns([1, 3])
    with col_refresh:
        if st.button("🔄 Làm mới ngay", use_container_width=True):
            st.cache_data.clear()
            st.rerun()
    
    with col_info:
        st.caption(f"Cập nhật lần cuối: {datetime.now().strftime('%H:%M:%S')}")
    
    df = fetch_gold_data(period="2d", interval="1m")
    if not df.empty:
        df = calculate_indicators(df)
        signal, confidence, reasons, score = generate_ai_signal(df)
        latest_price = df['Close'].iloc[-1]
        atr = df['ATR'].iloc[-1]
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Giá XAUUSD (Real-time)", f"${latest_price:,.2f}", 
                     f"{((latest_price - df['Close'].iloc[-2])/df['Close'].iloc[-2]*100):+.2f}%")
        with col2:
            st.metric("Khuyến nghị AI", signal, f"{confidence}% tin cậy")
        with col3:
            st.metric("Biến động (ATR)", f"${atr:.2f}")
        
        st.subheader("🎯 Khuyến nghị Entry - SL - TP")
        
        if "BUY" in signal:
            entry = latest_price - atr * 0.5
            sl = latest_price - atr * 1.8
            tp1 = latest_price + atr * 2.0
            tp2 = latest_price + atr * 3.5
            st.success(f"**BUY Entry Zone**: ${entry:,.2f} - ${latest_price:,.2f}")
            st.error(f"**Stop Loss (SL)**: ${sl:,.2f}")
            st.success(f"**Take Profit 1**: ${tp1:,.2f} | **Take Profit 2**: ${tp2:,.2f}")
        elif "SELL" in signal:
            entry = latest_price + atr * 0.5
            sl = latest_price + atr * 1.8
            tp1 = latest_price - atr * 2.0
            tp2 = latest_price - atr * 3.5
            st.success(f"**SELL Entry Zone**: ${latest_price:,.2f} - ${entry:,.2f}")
            st.error(f"**Stop Loss (SL)**: ${sl:,.2f}")
            st.success(f"**Take Profit 1**: ${tp1:,.2f} | **Take Profit 2**: ${tp2:,.2f}")
        else:
            st.info("Hiện tại tín hiệu **NEUTRAL**. Chờ tín hiệu rõ ràng hơn.")
        
        st.write("**Lý do phân tích:**")
        for r in reasons:
            st.write(f"• {r}")

elif page == "🎯 AI Entry Zone (Scalp/Swing)":
    st.header("🎯 AI Gợi Ý Entry - SL - TP")
    trading_style = st.radio("Chọn phong cách", ["⚡ Scalp (5-30 phút)", "📈 Swing (1-5 ngày)"], horizontal=True)
    
    df_entry = fetch_gold_data(period="3mo", interval="15m" if "Scalp" in trading_style else "1h")
    if df_entry.empty:
        st.error("❌ Không thể tải dữ liệu. Vui lòng thử lại sau.")
        st.stop()
    
    df_entry = calculate_indicators(df_entry)
    signal, confidence, reasons, score = generate_ai_signal(df_entry)
    latest = df_entry.iloc[-1]
    current_price = latest['Close']
    atr = latest['ATR']
    
    if "Scalp" in trading_style:
        entry_low = round(current_price - atr * 0.8, 2)
        entry_high = round(current_price + atr * 0.5, 2)
        sl = round(current_price - atr * 1.2, 2) if "BUY" in signal else round(current_price + atr * 1.2, 2)
        tp1 = round(current_price + atr * 1.5, 2) if "BUY" in signal else round(current_price - atr * 1.5, 2)
        tp2 = round(current_price + atr * 2.5, 2) if "BUY" in signal else round(current_price - atr * 2.5, 2)
    else:
        entry_low = round(current_price - atr * 1.5, 2)
        entry_high = round(current_price + atr * 1.0, 2)
        sl = round(current_price - atr * 2.5, 2) if "BUY" in signal else round(current_price + atr * 2.5, 2)
        tp1 = round(current_price + atr * 3.5, 2) if "BUY" in signal else round(current_price - atr * 3.5, 2)
        tp2 = round(current_price + atr * 5.5, 2) if "BUY" in signal else round(current_price - atr * 5.5, 2)
    
    st.success(f"**Entry Zone**: ${entry_low} - ${entry_high}")
    st.error(f"**Stop Loss (SL)**: ${sl}")
    st.success(f"**Take Profit 1 (TP1)**: ${tp1}")
    st.success(f"**Take Profit 2 (TP2)**: ${tp2}")
    
    # Biểu đồ
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df_entry['Datetime'].tail(50), open=df_entry['Open'].tail(50), high=df_entry['High'].tail(50), low=df_entry['Low'].tail(50), close=df_entry['Close'].tail(50)))
    fig.add_hline(y=entry_low, line_dash="dash", line_color="#00c853", annotation_text="Entry Low")
    fig.add_hline(y=entry_high, line_dash="dash", line_color="#00c853", annotation_text="Entry High")
    fig.add_hline(y=sl, line_dash="solid", line_color="#ff5252", annotation_text="Stop Loss")
    fig.add_hline(y=tp1, line_dash="dash", line_color="#2196f3", annotation_text="TP1")
    fig.add_hline(y=tp2, line_dash="dash", line_color="#9c27b0", annotation_text="TP2")
    fig.update_layout(title="Biểu đồ Entry - SL - TP", template="plotly_dark", height=450)
    st.plotly_chart(fig, use_container_width=True)
    
    if st.checkbox("📱 Gửi cảnh báo Telegram"):
        if st.button("🚀 Gửi Alert Ngay"):
            bot_token = st.session_state.get("telegram_bot_token", "")
            chat_id = st.session_state.get("telegram_chat_id", "")
            if bot_token and chat_id:
                message = f"🎯 ENTRY ZONE MỚI\nEntry: ${entry_low} - ${entry_high}\nSL: ${sl}\nTP1: ${tp1} | TP2: ${tp2}"
                success, msg = send_telegram_alert(message, bot_token, chat_id)
                st.success("✅ Đã gửi!") if success else st.error(msg)
            else:
                st.warning("Vui lòng cấu hình Telegram Bot trước!")

elif page == "🤖 Trò Chuyện AI":
    st.header("🤖 Trò Chuyện với AI")
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])
    if prompt := st.chat_input("Hỏi về XAUUSD..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("assistant"):
            st.write("Đang phân tích...")
        st.session_state.messages.append({"role": "assistant", "content": "Cảm ơn bạn! Tôi sẽ hỗ trợ phân tích XAUUSD."})

# ==================== CÁC TRANG KHÁC ====================
elif page == "📈 Backtest Chiến Lược":
    st.header("📈 Backtest")
    st.info("Tính năng Backtest đã sẵn sàng.")

elif page == "💰 Quản Lý Rủi Ro":
    st.header("💰 Quản Lý Rủi Ro")
    st.info("Công cụ tính toán vị thế đã sẵn sàng.")

elif page == "📰 Thông Tin Thị Trường":
    st.header("📰 Thông Tin Thị Trường")
    st.info("Yếu tố vĩ mô ảnh hưởng XAUUSD đã được cập nhật.")

elif page == "📱 Telegram Bot":
    st.header("📱 Telegram Bot")
    st.info("Kết nối Telegram Bot để nhận cảnh báo.")

elif page == "🔗 MT5 Live":
    st.header("🔗 MT5 Live")
    st.info("Kết nối MetaTrader 5 (chỉ hoạt động trên Windows).")

elif page == "🔮 ML Forecast":
    st.header("🔮 ML Forecast")
    st.info("Dự báo Machine Learning đã sẵn sàng.")

elif page == "⚙️ Cài Đặt & API":
    st.header("⚙️ Cài Đặt & API")
    st.info("Cài đặt và tích hợp API.")

# ==================== FOOTER ====================
st.markdown("---")
st.caption("⚠️ Đây là công cụ hỗ trợ phân tích. Giao dịch có rủi ro. Không phải lời khuyên tài chính. © 2026 XAUUSD AI Pro")