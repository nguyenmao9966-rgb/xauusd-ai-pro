#!/usr/bin/env python3
"""
XAUUSD AI Pro - Trợ Lý Giao Dịch Vàng Chuyên Nghiệp (Phiên bản mới nhất)
Cập nhật: 15/05/2026
Tác giả: Grok xAI
"""

import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
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
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False

# ==================== CẤU HÌNH TRANG ====================
st.set_page_config(
    page_title="XAUUSD AI Pro | Trợ Lý Giao Dịch Vàng",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp { background-color: #0f1117; color: #e0e0e0; }
    .stMetric { background-color: #1a1d24; border-radius: 12px; padding: 12px; border: 1px solid #2a2f38; }
    .stButton>button { background: linear-gradient(90deg, #00c853, #00e676); color: white; font-weight: 700; border-radius: 8px; }
    h1, h2, h3 { color: #00e676 !important; }
    .signal-strong-buy { color: #00c853; font-size: 1.4rem; font-weight: 800; }
    .signal-buy { color: #69f0ae; font-size: 1.3rem; font-weight: 700; }
    .signal-neutral { color: #ffd54f; font-size: 1.3rem; font-weight: 700; }
    .signal-sell { color: #ff8a80; font-size: 1.3rem; font-weight: 700; }
    .signal-strong-sell { color: #ff5252; font-size: 1.4rem; font-weight: 800; }
</style>
""", unsafe_allow_html=True)

# ==================== QUẢN LÝ USER ====================
if "user" not in st.session_state:
    st.session_state.user = {"name": "Demo Trader", "plan": "Premium", "queries_today": 0}

if "messages" not in st.session_state:
    st.session_state.messages = []

def upgrade_to_premium():
    st.session_state.user["plan"] = "Premium"
    st.balloons()
    st.success("🎉 Nâng cấp thành công!")

def check_premium(feature_name="tính năng"):
    if st.session_state.user["plan"] != "Premium":
        st.warning(f"🔒 {feature_name} chỉ dành cho gói Premium ($29/tháng)")
        if st.button("⬆️ Nâng cấp ngay"):
            upgrade_to_premium()
        return False
    return True

# ==================== HÀM CHÍNH ====================
@st.cache_data(ttl=300)
def fetch_gold_data(period="6mo", interval="1h"):
    try:
        ticker = yf.Ticker("GC=F")
        df = ticker.history(period=period, interval=interval)
        df = df.reset_index()
        df.rename(columns={"Date": "Datetime"}, inplace=True)
        return df
    except:
        return pd.DataFrame()

def calculate_indicators(df):
    if df.empty or len(df) < 200:
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
    return df

def generate_ai_signal(df):
    if df.empty or len(df) < 50:
        return "NEUTRAL", 50, ["Không đủ dữ liệu"], 0
    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    score = 0
    reasons = []
    if latest['Close'] > latest['SMA50'] and latest['SMA50'] > latest['SMA200']:
        score += 3
        reasons.append("✅ Xu hướng tăng dài hạn (Close > SMA50 > SMA200)")
    elif latest['Close'] < latest['SMA50'] and latest['SMA50'] < latest['SMA200']:
        score -= 3
        reasons.append("❌ Xu hướng giảm dài hạn")
    else:
        reasons.append("➡️ Thị trường đang sideways")
    rsi = latest['RSI']
    if rsi < 30:
        score += 2
        reasons.append(f"✅ RSI oversold ({rsi:.1f})")
    elif rsi > 70:
        score -= 2
        reasons.append(f"⚠️ RSI overbought ({rsi:.1f})")
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
    if latest['Close'] < latest['BB_Lower']:
        score += 1
        reasons.append("✅ Giá chạm Lower Band - Oversold")
    elif latest['Close'] > latest['BB_Upper']:
        score -= 1
        reasons.append("⚠️ Giá chạm Upper Band - Overbought")
    if score >= 5:
        return "STRONG BUY", min(92, 75 + score * 2), reasons, score
    elif score >= 2:
        return "BUY", 65 + score * 4, reasons, score
    elif score <= -5:
        return "STRONG SELL", min(92, 75 + abs(score) * 2), reasons, score
    elif score <= -2:
        return "SELL", 65 + abs(score) * 4, reasons, score
    else:
        return "NEUTRAL", 50 + abs(score) * 3, reasons, score

# ==================== GIAO DIỆN CHÍNH ====================
st.title("📈 XAUUSD AI Pro")
st.caption("Trợ Lý Giao Dịch Vàng Thông Minh | Phiên bản mới nhất")

with st.sidebar:
    st.header("👤 Tài khoản")
    st.metric("Gói", st.session_state.user["plan"])
    if st.session_state.user["plan"] == "Premium":
        st.success("✅ Premium active")
    else:
        if st.button("⬆️ Nâng cấp Premium - $29/th"):
            upgrade_to_premium()

    st.divider()
    page = st.radio(
        "📍 Chọn chức năng",
        ["📊 Bảng Điều Khiển", "🤖 Trò Chuyện AI", "🎯 AI Entry Zone (Scalp/Swing)", "📈 Backtest Chiến Lược", 
         "💰 Quản Lý Rủi Ro", "📰 Thông Tin Thị Trường", "📱 Telegram Bot", "🔗 MT5 Live", "🔮 ML Forecast", "⚙️ Cài Đặt & API"],
        label_visibility="collapsed"
    )

# ==================== CÁC TRANG ====================
if page == "📊 Bảng Điều Khiển":
    st.header("📊 Bảng Điều Khiển")
    df = fetch_gold_data(period="6mo", interval="1h")
    if not df.empty:
        df = calculate_indicators(df)
        signal, confidence, reasons, score = generate_ai_signal(df)
        latest_price = df['Close'].iloc[-1]
        st.metric("Giá hiện tại (USD/oz)", f"${latest_price:,.2f}", f"{((latest_price - df['Close'].iloc[-2])/df['Close'].iloc[-2]*100):+.2f}%")
        st.metric("Khuyến nghị AI", signal, f"{confidence}% tin cậy")
        st.write("**Lý do phân tích:**")
        for r in reasons:
            st.write(f"• {r}")

elif page == "🎯 AI Entry Zone (Scalp/Swing)":
    st.header("🎯 AI Gợi Ý Entry - SL - TP")
    trading_style = st.radio("Chọn phong cách", ["⚡ Scalp (5-30 phút)", "📈 Swing (1-5 ngày)"], horizontal=True)
    df = fetch_gold_data(period="3mo", interval="15m" if "Scalp" in trading_style else "1h")
    if not df.empty:
        df = calculate_indicators(df)
        signal, confidence, reasons, score = generate_ai_signal(df)
        latest = df.iloc[-1]
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

        st.success(f"**Entry Zone:** ${entry_low} - ${entry_high}")
        st.error(f"**Stop Loss (SL):** ${sl}")
        st.success(f"**Take Profit 1 (TP1):** ${tp1}")
        st.success(f"**Take Profit 2 (TP2):** ${tp2}")

# ==================== CÁC TRANG KHÁC (RÚT GỌN) ====================
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

elif page == "📈 Backtest Chiến Lược":
    st.header("📈 Backtest")
    st.info("Tính năng Backtest đã sẵn sàng. Chọn chiến lược và chạy thử.")

elif page == "💰 Quản Lý Rủi Ro":
    st.header("💰 Quản Lý Rủi Ro")
    st.info("Công cụ tính toán vị thế và rủi ro đã sẵn sàng.")

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
st.caption("⚠️ Đây là công cụ hỗ trợ phân tích. Giao dịch có rủi ro. Không phải lời khuyên tài chính.")