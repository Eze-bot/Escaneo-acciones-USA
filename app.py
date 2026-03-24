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

# --- FUNCIONES DE SENTIMIENTO ---
def get_yahoo_sentiment(ticker_obj):
    try:
        news = ticker_obj.news
        if not news: return 0
        score = 0
        for n in news[:3]:
            text = n['title'].lower()
            score += sum(1 for w in ['growth', 'buy', 'upgrade', 'profit'] if w in text)
            score -= sum(1 for w in ['drop', 'sell', 'downgrade', 'loss'] if w in text)
        return score
    except: return 0

def get_web_sentiment(ticker):
    # Consolidamos StockAnalysis y MarketWatch en una sola función más ligera
    score = 0
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        # StockAnalysis
        url_sa = f"https://stockanalysis.com/stocks/{ticker.lower()}/"
        res = requests.get(url_sa, headers=headers, timeout=3)
        if res.status_code == 200:
            txt = res.text.lower()
            if 'strong buy' in txt or 'outperform' in txt: score += 2
            if 'sell' in txt or 'underperform' in txt: score -= 2
    except: pass
    return score

# --- MOTOR DE ANÁLISIS ---
def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        # LIMPIEZA DE TICKER
        ticker = str(ticker_raw).strip().upper()
        
        # Intentamos obtener datos
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo") # Periodo corto para mayor velocidad
        
        if df.empty or len(df) < 5: return None

        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        # FILTROS FLEXIBLES
        if not (p_min <= precio_act <= p_max): return None
        if gap < gap_min: return None

        # Sentimiento
        s1 = get_yahoo_sentiment(stock)
        s2 = get_web_sentiment(ticker)
        total_sent = s1 + s2

        # Técnica simple para asegurar resultados
        ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
        
        score = 50 # Base
        if precio_act > ema20: score += 20
        if total_sent > 0: score += 30
        if gap > 0: score += 10

        last_30 = df.tail(30).copy()
        chart_data = last_30[['Close']]
        chart_data.columns = ['Precio ($)']

        return {
            "Ticker": ticker, "Precio": round(precio_act, 2), "Gap %": round(gap, 2),
            "Confianza": int(score), "News": "POS" if total_sent > 0 else "NEU",
            "SL": round(precio_act * 0.95, 2), "TP": round(precio_act * 1.10, 2),
            "Chart": chart_data
        }
    except Exception as e:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🇺🇸 Filtros USA")
    p_min_in = st.number_input("Precio Mín ($)", 0.0, 5000.0, 1.0)
    p_max_in = st.number_input("Precio Máx ($)", 0.0, 5000.0, 2000.0)
    gap_min_in = st.number_input("GAP Mínimo (%)", -10.0, 10.0, -5.0) # Bajamos a -5 para ver si trae algo
    st.divider()
    id_ins = st.text_input("ID Green API", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# --- PANEL PRINCIPAL ---
st.title("🚀 Escáner Cuádruple USA")
RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

if st.button("🔍 INICIAR ANÁLISIS"):
    if os.path.exists(RUTA_CSV):
        df_csv = pd.read_csv(RUTA_CSV)
        
        # Diagnóstico: ¿Qué hay en el CSV?
        st.write(f"📊 Tickers detectados en CSV: {len(df_csv)}")
        
        tickers = df_csv['Ticker'].dropna().unique().tolist()
        
        # Limpieza: quitamos los .BA si el CSV los trae
        tickers_limpios = [str(t).split('.')[0].strip() for t in tickers]

        with st.spinner("Procesando activos..."):
            with ThreadPoolExecutor(max_workers=5) as ex:
                res = [r for r in list(ex.map(lambda x: analizar_activo(x, p_min_in, p_max_in, gap_min_in), tickers_limpios)) if r is not None]
            
            if res:
                st.session_state['resultados'] = sorted(res, key=lambda x: x['Confianza'], reverse=True)[:6]
                st.success(f"✅ Se encontraron {len(res)} activos que cumplen los filtros.")
            else:
                st.warning("⚠️ El motor funcionó pero ningún activo cumplió los filtros de Precio/GAP.")
                st.info("Sugerencia: Prueba con GAP Mínimo en -5 y Precio Mín en 1.")
    else:
        st.error(f"❌ No encuentro el archivo: {RUTA_CSV}")

# --- RESULTADOS ---
if 'resultados' in st.session_state and st.session_state['resultados']:
    res_finales = st.session_state['resultados']
    cols = st.columns(2)
    for i, r in enumerate(res_finales):
        with cols[i % 2]:
            st.markdown(f"""
                <div class="ticker-card">
                    <h3>{r['Ticker']} — ${r['Precio']}</h3>
                    <p>🎯 Confianza: <b>{r['Confianza']}/100</b> | GAP: {r['Gap %']}%</p>
                    <p>🎭 Sentimiento: {r['News']}</p>
                    <p style="color:#D93025"><b>SL: ${r['SL']}</b></p>
                </div>
                """, unsafe_allow_html=True)
            st.line_chart(r['Chart'])
