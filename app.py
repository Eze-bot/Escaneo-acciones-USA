import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os
import altair as alt
import time

# ─────────────────────────────────────────────────────────────
# 1. CONFIGURACIÓN Y ESTILOS (DARK MODE)
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Scanner Quantum 2.0", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
    .stApp { background: #0d1117; color: #e6edf3; }
    .ticker-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 15px;
        transition: transform 0.2s;
    }
    .ticker-card:hover { border-color: #58a6ff; transform: translateY(-2px); }
    .t-symbol { font-family: 'Space Mono', monospace; font-size: 1.5rem; font-weight: 700; color: #58a6ff; }
    .t-price { font-size: 1.8rem; font-weight: 700; color: #ffffff; }
    .t-gap { font-size: 1.1rem; font-weight: 600; }
    .t-metrics { font-size: 0.85rem; color: #8b949e; margin-top: 8px; font-family: 'Space Mono', monospace; }
</style>
""", unsafe_allow_html=True)

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

# ─────────────────────────────────────────────────────────────
# 2. MOTOR DE ANÁLISIS TÉCNICO
# ─────────────────────────────────────────────────────────────
def analizar_pro(symbol):
    try:
        symbol = str(symbol).split('.')[0].strip().upper()
        tk = yf.Ticker(symbol)
        # Pedimos 60 días para calcular medias móviles correctamente
        df = tk.history(period="60d", interval="1d")
        
        if len(df) < 25: return None

        # INDICADORES
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # RSI (14)
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        precio = df['Close'].iloc[-1]
        ayer = df['Close'].iloc[-2]
        gap = ((precio - ayer) / ayer) * 100
        rsi_val = df['RSI'].iloc[-1]
        
        # Lógica de señales
        bullish = precio > df['EMA9'].iloc[-1] > df['EMA21'].iloc[-1]
        
        return {
            "Ticker": symbol, "Precio": round(precio, 2), "GAP": round(gap, 2),
            "RSI": round(rsi_val, 1), "EMA9": round(df['EMA9'].iloc[-1], 2),
            "Tendencia": "Alcista" if bullish else "Neutral/Bajista",
            "Color": "#3fb950" if gap > 0 else "#f85149",
            "Data": df.tail(30).reset_index() # Solo últimos 30 días para el gráfico
        }
    except: return None

# ─────────────────────────────────────────────────────────────
# 3. INTERFAZ Y SIDEBAR
# ─────────────────────────────────────────────────────────────
st.title("📡 Analisis activos / Oportunidades")

with st.sidebar:
    st.header("🛠️ Filtros Técnicos")
    p_min = st.number_input("Precio Mín ($)", 0.1, 5000.0, 1.0)
    p_max = st.number_input("Precio Máx ($)", 0.1, 5000.0, 100.0)
    gap_min = st.slider("GAP Mínimo %", -10.0, 20.0, 1.5)
    st.divider()
    st.subheader("📱 WhatsApp Config")
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("Número destino", "5492664300161")

if os.path.exists(RUTA_CSV):
    tickers = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
    
    if 'resultados_v2' not in st.session_state:
        st.session_state.resultados_v2 = []

    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("🚀 ESCANEO"):
            with st.spinner("Analizando indicadores..."):
                with ThreadPoolExecutor(max_workers=10) as executor:
                    res = [r for r in list(executor.map(analizar_pro, tickers)) if r is not None]
                    # Filtro de usuario aplicado aquí
                    res = [r for r in res if p_min <= r['Precio'] <= p_max and r['GAP'] >= gap_min]
                    st.session_state.resultados_v2 = sorted(res, key=lambda x: x['GAP'], reverse=True)[:6]

    if st.session_state.resultados_v2:
        with c2:
            if st.button("📱 ENVIAR SEÑALES A WHATSAPP"):
                try:
                    msg = f"🚀 *SCANN QUANTUM 2.0*\n"
                    for r in st.session_state.resultados_v2:
                        msg += f"🔹 *{r['Ticker']}*: ${r['Precio']} ({r['GAP']}%)\n   RSI: {r['RSI']} | {r['Tendencia']}\n"
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                    st.toast("Reporte enviado con éxito")
                except: st.error("Error en WhatsApp")

        # RENDERIZADO DE TARJETAS
        st.divider()
        cols = st.columns(3)
        for i, res in enumerate(st.session_state.resultados_v2):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="ticker-card">
                    <div class="t-symbol">{res['Ticker']}</div>
                    <div class="t-price">${res['Precio']}</div>
                    <div class="t-gap" style="color:{res['Color']}">{"+" if res['GAP']>0 else ""}{res['GAP']}%</div>
                    <div class="t-metrics">
                        RSI: {res['RSI']} | {res['Tendencia']}<br>
                        EMA9: ${res['EMA9']}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # GRÁFICO AVANZADO CON EMA
                base = alt.Chart(res['Data']).encode(x=alt.X('Date:T', axis=None))
                linea_precio = base.mark_line(color='#58a6ff', strokeWidth=2).encode(y=alt.Y('Close:Q', scale=alt.Scale(zero=False)))
                linea_ema9 = base.mark_line(color='#f0c040', strokeDash=[4,2]).encode(y='EMA9:Q')
                
                chart = alt.layer(linea_precio, linea_ema9).properties(height=100)
                st.altair_chart(chart, use_container_width=True)
                st.markdown("<p style='font-size:0.7rem; color:#8b949e; margin-top:-15px'>━ Precio | ╌ EMA9</p>", unsafe_allow_html=True)
    else:
        st.info("Sistema listo. Pulsa 'Escaneo Pro' para procesar indicadores técnicos.")
else:
    st.error("CSV no encontrado.")
