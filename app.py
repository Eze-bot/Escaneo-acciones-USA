import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Trading Pro", layout="wide", page_icon="📈")

# --- ESTILOS CSS REFORZADOS (PARA EVITAR PANTALLA BLANCA EN CELULAR) ---
st.markdown("""
    <style>
    /* Contenedor principal de la tarjeta */
    .ticker-card {
        background-color: #FFFFFF !important; 
        border-radius: 12px;
        padding: 20px;
        border-left: 8px solid #007bff;
        margin-bottom: 25px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.2);
    }
    /* Forzado de color de texto para Modo Oscuro de móviles */
    .ticker-card h3 {
        color: #121212 !important;
        margin-top: 0;
        margin-bottom: 12px;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .ticker-card p {
        color: #333333 !important;
        font-size: 1.05rem;
        margin: 6px 0;
        line-height: 1.2;
    }
    .label-data {
        font-weight: bold;
        color: #000000 !important;
    }
    .sl-text {
        color: #D32F2F !important;
        font-weight: bold;
        font-size: 1.15rem;
        margin-top: 12px !important;
        border-top: 1px solid #eee;
        padding-top: 8px;
    }
    /* Estilo para los labels de noticias */
    .pos-label { color: #28a745 !important; font-weight: bold; }
    .neg-label { color: #dc3545 !important; font-weight: bold; }
    .neu-label { color: #6c757d !important; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE SENTIMIENTO TS2 TECH ---
def get_ts2_sentiment(ticker):
    try:
        url = "https://ts2.tech/en/category/stock-market/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = soup.find_all(['h2', 'h3'])
        ts2_score = 0
        pos_keywords = ['surge', 'bullish', 'buy', 'growth', 'ai', 'record', 'profit', 'up']
        neg_keywords = ['fall', 'bearish', 'sell', 'risk', 'loss', 'drop', 'crash', 'down']
        count = 0
        for h in headlines:
            text = h.get_text().lower()
            if ticker.lower() in text:
                count += 1
                ts2_score += sum(1 for w in pos_keywords if w in text)
                ts2_score -= sum(1 for w in neg_keywords if w in text)
        return ts2_score if count > 0 else 0
    except:
        return 0

# --- LÓGICA DE SENTIMIENTO YAHOO ---
def get_yahoo_sentiment(ticker_obj):
    try:
        news = ticker_obj.news
        if not news: return 0
        pos = ['growth', 'buy', 'upgrade', 'beat', 'ai', 'dividend', 'success', 'bullish', 'profit']
        neg = ['drop', 'sell', 'downgrade', 'miss', 'risk', 'lawsuit', 'loss', 'bearish']
        score = 0
        for n in news[:5]:
            text = n['title'].lower()
            score += sum(1 for w in pos if w in text)
            score -= sum(1 for w in neg if w in text)
        return score
    except: return 0

# --- MOTOR DE ANÁLISIS ---
def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if len(df) < 200: return None

        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        if not (p_min <= precio_act <= p_
