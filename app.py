import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os

# CONFIGURACIÓN - DEBE SER LO PRIMERO
st.set_page_config(page_title="Scanner USA", layout="wide")

st.title("📈 Dashboard Top 6 Momentum")

# Ruta del archivo
RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

# Sidebar
with st.sidebar:
    st.header("Configuración")
    p_min = st.number_input("Precio Mín ($)", 0.01, 1000.0, 0.50)
    p_max = st.number_input("Precio Máx ($)", 0.01, 1000.0, 17.0)
    gap_min = st.slider("GAP Mínimo (%)", 0.0, 20.0, 2.0)
    st.divider()
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

def analizar(ticker_raw):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo")
        if len(df) < 10: return None
        cierre = df['Close'].iloc[-1]
        ayer = df['Close'].iloc[-2]
        gap = ((cierre - ayer) / ayer) * 100
        if p_min <= cierre <= p_max and gap >= gap_min:
            vol_rel = df['Volume'].iloc[-1] / df['Volume'].iloc[-11:-1].mean()
            return {"Ticker": ticker, "Precio": round(cierre, 2), "GAP": round(gap, 2), "Vol": round(vol_rel, 2), "Hist": df['Close']}
    except: return None

if os.path.exists(RUTA_CSV):
    tickers = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
    st.sidebar.success(f"📂 {len(tickers)} Activos")
    
    if st.button("🔍 ESCANEAR"):
        with st.spinner("Analizando..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                res = [r for r in list(executor.map(analizar, tickers)) if r is not None]
            if res:
                top_6 = sorted(res, key=lambda x: x['GAP'], reverse=True)[:6]
                cols = st.columns(2)
                for i, r in enumerate(top_6):
                    with cols[i % 2]:
                        st.subheader(f"🚀 {r['Ticker']}")
                        st.write(f"Precio: ${r['Precio']} | GAP: {r['GAP']}%")
                        st.line_chart(r["Hist"])
            else:
                st.warning("Sin resultados.")
else:
    st.error("Falta el archivo CSV en GitHub.")
