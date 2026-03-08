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

# 1. CONFIGURACIÓN Y ESTILOS
st.set_page_config(page_title="Scanner Quantum 3.5", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
    .stApp { background: #0d1117; color: #e6edf3; }
    
    /* Botones de Alto Contraste */
    div.stButton > button { width: 100%; border-radius: 8px; font-weight: 700; height: 3.5em; }
    
    /* Botón USA (Azul) */
    .btn-usa > div > button { background-color: #007bff !important; color: white !important; border: none !important; }
    
    /* Botón CEDEAR (Naranja/Dorado) */
    .btn-cedear > div > button { background-color: #f39c12 !important; color: white !important; border: none !important; }
    
    /* Botón WhatsApp (Verde) */
    div.stButton > button[kind="secondary"] { background-color: #238636 !important; color: white !important; border: none !important; }

    .ticker-card {
        background: #161b22;
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 10px;
    }
    .t-symbol { font-family: 'Space Mono', monospace; font-size: 1.2rem; color: #58a6ff; font-weight:700; }
    .t-market-tag { font-size: 0.6rem; padding: 2px 5px; border-radius: 4px; background: #21262d; color: #8b949e; float: right; }
</style>
""", unsafe_allow_html=True)

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

# 2. MOTOR DE ANÁLISIS
def analizar_activo(symbol):
    try:
        tk = yf.Ticker(symbol)
        df = tk.history(period="60d", interval="1d")
        if len(df) < 20: return None

        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        precio = df['Close'].iloc[-1]
        gap = ((precio - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = 100 - (100 / (1 + (gain / loss)))

        return {
            "Ticker": symbol, "Precio": round(precio, 2), "GAP": round(gap, 2),
            "RSI": round(rsi.iloc[-1], 1), "EMA9": round(df['EMA9'].iloc[-1], 2),
            "EsCedear": ".BA" in symbol, "Data": df.tail(20).reset_index()
        }
    except: return None

# 3. SIDEBAR CON FILTROS SEPARADOS
with st.sidebar:
    st.title("📡 Panel de Control")
    
    tab_usa, tab_cedear = st.tabs(["🇺🇸 USA", "🇦🇷 CEDEAR"])
    
    with tab_usa:
        p_min_usa = st.number_input("Precio Mín (USD)", 0.0, 5000.0, 1.0)
        p_max_usa = st.number_input("Precio Máx (USD)", 0.0, 5000.0, 200.0)
        gap_usa = st.slider("GAP Mín USA %", -5.0, 15.0, 1.0, key="g_usa")
        
    with tab_cedear:
        p_min_arg = st.number_input("Precio Mín ($)", 0, 1000000, 500)
        p_max_arg = st.number_input("Precio Máx ($)", 0, 5000000, 500000)
        gap_arg = st.slider("GAP Mín CEDEAR %", -5.0, 15.0, 1.0, key="g_arg")

    st.divider()
    celular = st.text_input("WhatsApp", "5492664300161")
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")

# 4. LÓGICA DE EJECUCIÓN
if os.path.exists(RUTA_CSV):
    df_csv = pd.read_csv(RUTA_CSV)
    tickers_all = df_csv['Ticker'].dropna().unique().tolist()
    
    # Separar listas
    list_cedear = [t for t in tickers_all if ".BA" in str(t)]
    list_usa = [t for t in tickers_all if ".BA" not in str(t)]

    if 'resultados' not in st.session_state: st.session_state.resultados = []

    # FILA DE BOTONES DE ESCANEO
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="btn-usa">', unsafe_allow_html=True)
        if st.button(f"🇺🇸 ESCANEAR USA ({len(list_usa)})"):
            with st.spinner("Analizando Wall Street..."):
                with ThreadPoolExecutor(max_workers=10) as ex:
                    res = [r for r in list(ex.map(analizar_activo, list_usa)) if r is not None]
                    st.session_state.resultados = [r for r in res if p_min_usa <= r['Precio'] <= p_max_usa and r['GAP'] >= gap_usa]
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="btn-cedear">', unsafe_allow_html=True)
        if st.button(f"🇦🇷 ESCANEAR CEDEARs ({len(list_cedear)})"):
            with st.spinner("Analizando BYMA..."):
                with ThreadPoolExecutor(max_workers=10) as ex:
                    res = [r for r in list(ex.map(analizar_activo, list_cedear)) if r is not None]
                    st.session_state.resultados = [r for r in res if p_min_arg <= r['Precio'] <= p_max_arg and r['GAP'] >= gap_arg]
        st.markdown('</div>', unsafe_allow_html=True)

    # BOTÓN WHATSAPP Y RESULTADOS
    if st.session_state.resultados:
        st.divider()
        if st.button("📱 ENVIAR SELECCIÓN A WHATSAPP", type="secondary"):
            try:
                msg = "🚀 *SCANNER QUANTUM 3.5*\n"
                for r in st.session_state.resultados[:6]:
                    mon = "$" if r['EsCedear'] else "u$d"
                    msg += f"🔹 *{r['Ticker']}*: {mon}{r['Precio']} ({r['GAP']}%)\n"
                greenAPI = API.GreenApi(id_ins, token_ins)
                greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                st.toast("Enviado con éxito")
            except: st.error("Error envío")

        cols = st.columns(3)
        for i, res in enumerate(st.session_state.resultados[:9]): # Top 9
            with cols[i % 3]:
                mon = "$" if res['EsCedear'] else "u$d"
                tag = "CEDEAR" if res['EsCedear'] else "USA"
                st.markdown(f"""
                <div class="ticker-card">
                    <span class="t-market-tag">{tag}</span>
                    <div class="t-symbol">{res['Ticker']}</div>
                    <div style="font-size:1.4rem; font-weight:700;">{mon} {res['Precio']}</div>
                    <div style="color:{'#3fb950' if res['GAP']>0 else '#f85149'}; font-weight:700;">
                        {"+" if res['GAP']>0 else ""}{res['GAP']}%
                    </div>
                </div>
                """, unsafe_allow_html=True)
                # Gráfico sutil
                chart = alt.Chart(res['Data']).mark_line(color='#58a6ff').encode(
                    x=alt.X('Date:T', axis=None),
                    y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=None)
                ).properties(height=60)
                st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Selecciona qué mercado deseas escanear hoy.")
