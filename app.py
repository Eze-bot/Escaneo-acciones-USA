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
       padding: 15px;
       border-left: 6px solid #1A73E8;
       margin-bottom: 15px;
       box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
    }
   .type-label { font-size: 0.8em; color: #5f6368; font-weight: normal; }
   .pos-label { color: #1E8E3E; font-weight: bold; }
   .neg-label { color: #D93025; font-weight: bold; }
   .exit-label { color: #f29900; font-weight: bold; }
   </style>
   """, unsafe_allow_html=True)

# --- MOTOR DE ANÁLISIS ---
def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        
        # Detectar Tipo de Activo (ETF o ACCIÓN)
        info = stock.info
        tipo_raw = info.get('quoteType', 'EQUITY')
        tipo = "ETF" if tipo_raw == "ETF" else "ACCIÓN"

        df = stock.history(period="1y") 
        if df.empty or len(df) < 50: return None

        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        if not (p_min <= precio_act <= p_max) or gap < gap_min: return None

        # Indicadores Técnicos
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi_serie = 100 - (100 / (1 + (gain / loss)))
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        
        # Gráfico (Últimos 30 días)
        last_30 = df.tail(30).copy()
        p_min_v, p_max_v = last_30['Close'].min(), last_30['Close'].max()
        rsi_norm = ((rsi_serie.tail(30) - 0) / 100) * (p_max_v - p_min_v) + p_min_v
        
        last_30.index = last_30.index.strftime('%d %b')
        chart_df = pd.DataFrame({
            'Precio ($)': last_30['Close'],
            'RSI (Rojo)': rsi_norm
        })

        # Puntaje de Confianza
        score = 50
        if rsi_serie.iloc[-1] > 50: score += 20
        if gap > 1: score += 10

        return {
            "Ticker": ticker,
            "Tipo": tipo,
            "Precio": round(precio_act, 2),
            "Gap": round(gap, 2),
            "Confianza": int(score),
            "RSI": round(rsi_serie.iloc[-1], 1),
            "SL": round(precio_act - (2 * atr), 2),
            "TP": round(precio_act + (3 * atr), 2),
            "Chart": chart_df
        }
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración USA")
    p_min_in = st.number_input("Precio Mín ($)", 0.0, 5000.0, 5.0)
    p_max_in = st.number_input("Precio Máx ($)", 0.0, 5000.0, 1500.0)
    gap_min_in = st.slider("GAP Mínimo (%)", -5.0, 10.0, 0.5)
    st.divider()
    id_ins = st.text_input("ID Green API", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# --- PANEL PRINCIPAL ---
st.title("🇺🇸 Escáner USA: Acciones & ETFs")
RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

if st.button("🔍 ANALIZAR MERCADO"):
    if os.path.exists(RUTA_CSV):
        tickers = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
        with st.spinner("Clasificando y analizando activos..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                res = [r for r in list(ex.map(lambda x: analizar_activo(x, p_min_in, p_max_in, gap_min_in), tickers)) if r is not None]
            st.session_state['resultados'] = sorted(res, key=lambda x: x['Confianza'], reverse=True)[:6]
    else:
        st.error("Archivo CSV no detectado.")

# --- RESULTADOS ---
if 'resultados' in st.session_state and st.session_state['resultados']:
    cols = st.columns(2)
    for i, r in enumerate(st.session_state['resultados']):
        with cols[i % 2]:
            st.markdown(f"""
                <div class="ticker-card">
                    <h3 style='margin:0;'>{r['Ticker']} <span class="type-label">({r['Tipo']})</span> — ${r['Precio']}</h3>
                    <p style='margin:5px 0;'>🎯 Confianza: <b>{r['Confianza']}/100</b> | GAP: +{r['Gap']}%</p>
                    <p style='margin:5px 0;'>🛑 SL: <span class="neg-label">${r['SL']}</span> | 🚀 <b>EXIT: <span class="exit-label">${r['TP']}</span></b></p>
                </div>
                """, unsafe_allow_html=True)
            st.line_chart(r['Chart'], height=200, color=["#1A73E8", "#D93025"])

    if st.button("📲 ENVIAR ALERTAS WHATSAPP"):
        ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
        msg = f"🇺🇸 *OPORTUNIDADES USA*\n_{ahora.strftime('%d/%m %H:%M')}_\n━━━━━━━━━━━━━━━━━━\n"
        for r in st.session_state['resultados']:
            msg += f"🚀 *{r['Ticker']} ({r['Tipo']})* | ${r['Precio']}\n   - SL: ${r['SL']} | EXIT: ${r['TP']}\n\n"
        try:
            greenAPI = API.GreenApi(id_ins, token_ins)
            greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
            st.success("Enviado.")
        except: st.error("Error API.")
