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
st.set_page_config(page_title="AI Trading Quad-Scan", layout="wide", page_icon="🇺🇸")

# --- ESTILOS CSS ---
st.markdown("""
   <style>
   .ticker-card {
       background-color: #ffffff;
       border-radius: 12px;
       padding: 20px;
       border-left: 6px solid #1A73E8;
       margin-bottom: 25px;
       box-shadow: 0px 4px 10px rgba(0,0,0,0.08);
    }
   .pos-label { color: #1E8E3E; font-weight: bold; }
   .neg-label { color: #D93025; font-weight: bold; }
   .neu-label { color: #70757a; font-weight: bold; }
   </style>
   """, unsafe_allow_html=True)

# --- FUENTE 1: YAHOO FINANCES ---
def get_yahoo_sentiment(ticker_obj):
    try:
        news = ticker_obj.news
        if not news: return 0
        score = 0
        for n in news[:5]:
            text = n['title'].lower()
            score += sum(1 for w in ['growth', 'buy', 'upgrade', 'beat', 'profit'] if w in text)
            score -= sum(1 for w in ['drop', 'sell', 'downgrade', 'miss', 'loss'] if w in text)
        return score
    except: return 0

# --- FUENTE 2: TS2.TECH ---
def get_ts2_sentiment(ticker):
    try:
        url = "https://ts2.tech/en/category/stock-market/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = soup.find_all(['h2', 'h3'])
        score = 0
        t_clean = str(ticker).lower()
        for h in headlines:
            text = h.get_text().lower()
            if t_clean in text:
                score += sum(1 for w in ['surge', 'bullish', 'ai', 'growth'] if w in text)
                score -= sum(1 for w in ['fall', 'bearish', 'risk', 'drop'] if w in text)
        return score
    except: return 0

# --- FUENTE 3: STOCKANALYSIS ---
def get_stockanalysis_sentiment(ticker):
    try:
        url = f"https://stockanalysis.com/stocks/{ticker.lower()}/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        if response.status_code != 200: return 0
        soup = BeautifulSoup(response.text, 'html.parser')
        text = soup.get_text().lower()
        score = 0
        score += 2 if 'strong buy' in text or 'outperform' in text else 0
        score -= 2 if 'sell' in text or 'underperform' in text else 0
        return score
    except: return 0

# --- FUENTE 4: MARKETWATCH ---
def get_marketwatch_sentiment(ticker):
    try:
        url = f"https://www.marketwatch.com/investing/stock/{ticker.lower()}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = soup.find_all('h3', class_='article__headline')
        score = 0
        for h in headlines[:5]:
            text = h.get_text().lower()
            score += sum(1 for w in ['upgrade', 'positive', 'strong', 'rise'] if w in text)
            score -= sum(1 for w in ['downgrade', 'weak', 'debt', 'fall'] if w in text)
        return score
    except: return 0

# --- MOTOR DE ANÁLISIS ---
def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        ticker = str(ticker_raw).strip().upper()
        if "." in ticker: return None # Solo USA Directo

        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if len(df) < 150: return None

        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        if not (p_min <= precio_act <= p_max) or gap < gap_min: return None

        # --- CUÁDRUPLE ANÁLISIS DE SENTIMIENTO ---
        s1 = get_yahoo_sentiment(stock)
        s2 = get_ts2_sentiment(ticker)
        s3 = get_stockanalysis_sentiment(ticker)
        s4 = get_marketwatch_sentiment(ticker)
        total_sent = s1 + s2 + s3 + s4

        # Indicadores Técnicos
        ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
        sma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss))).iloc[-1]
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]

        # Puntaje de Confianza
        score = 0
        if precio_act > sma200: score += 30
        if precio_act > ema20: score += 20
        if 40 < rsi < 70: score += 20
        if total_sent > 0: score += 20
        if gap > 2.5: score += 10

        # Datos para gráfico
        last_30 = df.tail(30).copy()
        p_min_v, p_max_v = last_30['Close'].min(), last_30['Close'].max()
        # Normalizar RSI para que entre en el gráfico de precio
        rsi_hist = 100 - (100 / (1 + (gain / loss))).tail(30)
        last_30['RSI_Norm'] = ((rsi_hist - 0) / 100) * (p_max_v - p_min_v) + p_min_v
        
        chart_data = last_30[['Close', 'RSI_Norm']]
        chart_data.columns = ['Precio ($)', 'RSI (Norm)']

        return {
            "Ticker": ticker,
            "Precio": round(precio_act, 2),
            "Gap %": round(gap, 2),
            "Confianza": int(score),
            "RSI": round(rsi, 1),
            "News": "POS" if total_sent > 0 else ("NEG" if total_sent < 0 else "NEU"),
            "SL": round(precio_act - (2.2 * atr), 2),
            "TP": round(precio_act + (4.0 * atr), 2),
            "Chart": chart_data
        }
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🇺🇸 Configuración USA")
    p_min_in = st.number_input("Precio Mín ($)", 0.0, 5000.0, 5.0)
    p_max_in = st.number_input("Precio Máx ($)", 0.0, 5000.0, 1000.0)
    gap_min_in = st.slider("GAP Mínimo (%)", -2.0, 15.0, 1.0)
    st.divider()
    id_ins = st.text_input("ID Green API", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# --- PANEL PRINCIPAL ---
st.title("🚀 Escáner Cuádruple: USA Direct")
st.info("Fuentes: Yahoo | TS2 | StockAnalysis | MarketWatch")

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

if st.button("🔍 INICIAR MEGA-ANÁLISIS"):
    if os.path.exists(RUTA_CSV):
        tickers = pd.read_csv(RUTA_CSV)['Ticker'].tolist()
        with st.spinner("Analizando con 4 fuentes de noticias y datos técnicos..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                res = [r for r in list(ex.map(lambda x: analizar_activo(x, p_min_in, p_max_in, gap_min_in), tickers)) if r is not None]
            st.session_state['resultados'] = sorted(res, key=lambda x: x['Confianza'], reverse=True)[:6]
    else:
        st.error("Falta el archivo CSV.")

# --- RESULTADOS ---
if 'resultados' in st.session_state and st.session_state['resultados']:
    cols = st.columns(2)
    for i, r in enumerate(st.session_state['resultados']):
        with cols[i % 2]:
            lbl = "pos-label" if r['News'] == "POS" else ("neg-label" if r['News'] == "NEG" else "neu-label")
            st.markdown(f"""
                <div class="ticker-card">
                    <h3>{r['Ticker']} — ${r['Precio']}</h3>
                    <p>🎯 Confianza: <b>{r['Confianza']}/100</b> | GAP: +{r['Gap %']}%</p>
                    <p>🎭 Sentimiento: <span class="{lbl}">{r['News']}</span> |
