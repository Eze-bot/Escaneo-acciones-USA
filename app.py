import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Trading Quad-Scan", layout="wide", page_icon="🚀")

# --- ESTILOS CSS PERSONALIZADOS ---
st.markdown("""
    <style>
    .ticker-card {
        background-color: #1e1e1e;
        border-radius: 12px;
        padding: 18px;
        border: 1px solid #333;
        color: white !important;
        margin-bottom: 10px;
    }
    .price-text { font-size: 1.4em; font-weight: bold; color: #1A73E8; }
    .profit-tag { background-color: #00c85322; color: #00c853; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
    .trend-label { font-size: 0.9em; font-weight: bold; }
    .sma-info { font-size: 0.8em; color: #888888; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE ANÁLISIS TÉCNICO ---
def analizar_activo(ticker_raw, p_min_val, p_max_val, g_min_val):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        # Validación de historial suficiente para SMA 200
        if df.empty or len(df) < 200: 
            return None

        # --- CÁLCULO DE MEDIAS MÓVILES (Filtro Dual) ---
        precio_act = df['Close'].iloc[-1]
        sma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        sma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        
        # Determinación de Tendencia
        if precio_act > sma200 and precio_act > sma50:
            tendencia = "ALCISTA FUERTE 🚀"
            t_color = "#00c853"
        elif precio_act > sma200:
            tendencia = "ALCISTA (Largo Plazo) 🟢"
            t_color = "#b2ff59"
        elif precio_act > sma50:
            tendencia = "RECUPERACIÓN (Corto Plazo) 🟡"
            t_color = "#ffd600"
        else:
            tendencia = "BAJISTA 🔴"
            t_color = "#ff4b4b"

        # --- FILTROS DE PRECIO Y GAP ---
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        if not (p_min_val <= precio_act <= p_max_val) or gap < g_min_val: 
            return None

        # --- GESTIÓN DE RIESGO 2:1 ---
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        riesgo = atr * 1.5
        sl = precio_act - riesgo
        exit_p = (precio_act + (riesgo * 2)) * 1.01 # Ajuste comisión salida
        ganancia_neta = ((exit_p / (precio_act * 1.005)) - 1) * 100 # Neto tras comisión entrada

        # --- RSI (14) ---
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_serie = 100 - (100 / (1 + (gain / loss)))

        # Datos para gráfico (último mes)
        last_25 = df.tail(25).copy()
        last_25.index = last_25.index.strftime('%d %b')

        return {
            "Ticker": ticker, 
            "Tipo": "ETF" if stock.info.get('quoteType') == "ETF" else "ACCIÓN",
            "Precio": round(precio_act, 2), 
            "Gap": round(gap, 2),
            "SL": round(sl, 2), 
            "TP": round(exit_p, 2),
            "Neto": round(ganancia_neta, 1), 
            "Tendencia": tendencia, 
            "T_Color": t_color,
            "sma50": round(
