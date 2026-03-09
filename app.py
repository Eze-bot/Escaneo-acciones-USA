import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import os
import altair as alt

# 1. CONFIGURACIÓN Y ESTILOS
st.set_page_config(page_title="Scanner Quantum 3.6", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
    .stApp { background: #0d1117; color: #e6edf3; }
    div.stButton > button { width: 100%; border-radius: 8px; font-weight: 700; height: 3.5em; }
    .btn-usa > div > button { background-color: #007bff !important; color: white !important; border: none !important; }
    .btn-cedear > div > button { background-color: #f39c12 !important; color: white !important; border: none !important; }
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

# 2. MOTOR DE ANÁLISIS (CON LIMPIEZA DE TICKER)
def analizar_activo(symbol):
    try:
        # Limpieza profunda del ticker
        s = str(symbol).strip().upper()
        if not s: return None
        
        tk = yf.Ticker(s)
        # Bajamos a 1mo para asegurar rapidez y evitar errores de data faltante
        df = tk.history(period="1mo", interval="1d")
        
        if df.empty or len(df) < 5: return None

        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        precio = df['Close'].iloc[-1]
        ayer = df['Close'].iloc[-2]
        gap = ((precio - ayer) / ayer) * 100
        
        return {
            "Ticker": s, 
            "Precio": round(precio, 2), 
            "GAP": round(gap, 2),
            "EsCedear": ".BA" in s, 
            "Data": df.tail(15).reset_index()
        }
    except: return None

# 3. SIDEBAR
with st.sidebar:
    st.title("📡 Panel de Control")
    tab_usa, tab_cedear = st.tabs(["🇺🇸 USA", "🇦🇷 CEDEAR"])
    
    with tab_usa:
        p_min_usa = st.number_input("Precio Mín (USD)", 0.0, 5000.0, 0.1) # Bajé el mínimo
        p_max_usa = st.number_input("Precio Máx (USD)", 0.0, 10000.0, 5000.0) # Subí el máximo
        gap_usa = st.slider("GAP Mín USA %", -10.0, 15.0, 0.0, key="g_usa") # Bajé a 0.0 para ver todo
        
    with tab_cedear:
        p_min_arg = st.number_input("Precio Mín ($)", 0, 10000000, 100)
        p_max_arg = st.number_input("Precio Máx ($)", 0, 10000000, 1000000)
        gap_arg = st.slider("GAP Mín CEDEAR %", -10.0, 15.0, 0.0, key="g_arg")

    st.divider()
    celular = st.text_input("WhatsApp", "5492664300161")
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")

# 4. LÓGICA DE EJECUCIÓN
if os.path.exists(RUTA_CSV):
    df_csv = pd.read_csv(RUTA_CSV)
    # Detectar columna de ticker dinámicamente
    col_t = [c for c in df_csv.columns if 'tick' in c.lower()][0]
    tickers_all = df_csv[col_t].dropna().unique().tolist()
    
    list_cedear = [t for t in tickers_all if ".BA" in str(t)]
    list_usa = [t for t in tickers_all if ".BA" not in str(t)]

    if 'resultados' not in st.session_state: st.session_state.resultados = []

    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="btn-usa">', unsafe_allow_html=True)
        if st.button(f"🇺🇸 ESCANEAR USA ({len(list_usa)})"):
            with st.spinner("Analizando Wall Street..."):
                with ThreadPoolExecutor(max_workers=15) as ex:
                    res = [r for r in list(ex.map(analizar_activo, list_usa)) if r is not None]
                    # Filtro aplicado
                    st.session_state.resultados = [r for r in res if p_min_usa <= r['Precio'] <= p_max_usa and r['GAP'] >= gap_usa]
                    if not st.session_state.resultados: st.warning("No hay activos USA que cumplan los filtros.")
        st.markdown('</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="btn-cedear">', unsafe_allow_html=True)
        if st.button(f"🇦🇷 ESCANEAR CEDEARs ({len(list_cedear)})"):
            with st.spinner("Analizando BYMA..."):
                with ThreadPoolExecutor(max_workers=15) as ex:
                    res = [r for r in list(ex.map(analizar_activo, list_cedear)) if r is not None]
                    st.session_state.resultados = [r for r in res if p_min_arg <= r['Precio'] <= p_max_arg and r['GAP'] >= gap_arg]
                    if not st.session_state.resultados: st.warning("No hay CEDEARs que cumplan los filtros.")
        st.markdown('</div>', unsafe_allow_html=True)

    # MOSTRAR RESULTADOS
    if st.session_state.resultados:
        st.divider()
        # Botón WhatsApp solo aparece si hay resultados
        if st.button("📱 ENVIAR SELECCIÓN A WHATSAPP", type="secondary"):
            try:
                msg = "🚀 *SCANNER QUANTUM 3.6*\n"
                for r in st.session_state.resultados[:8]:
                    msg += f"🔹 *{r['Ticker']}*: {r['Precio']} ({r['GAP']}%)\n"
                greenAPI = API.GreenApi(id_ins, token_ins)
                greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                st.toast("Enviado!")
            except: st.error("Error WhatsApp")

        cols = st.columns(4) # 4 columnas para ver más
        for i, res in enumerate(st.session_state.resultados[:12]):
