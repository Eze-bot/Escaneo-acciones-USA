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

# ─────────────────────────────────────────────────────────────
# 1. CONFIGURACIÓN Y ESTILOS (DARK MODE PROFESIONAL)
# ─────────────────────────────────────────────────────────────
st.set_page_config(page_title="Quantum Scanner 3.0", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&display=swap');
    .stApp { background: #0d1117; color: #e6edf3; }
    
    /* Botones de Alto Contraste */
    div.stButton > button { width: 100%; border-radius: 8px; font-weight: 700; text-transform: uppercase; }
    
    /* Botón ESCANEO (Azul) */
    div.stButton > button[kind="primary"] {
        background-color: #007bff !important; color: white !important;
        border: none; box-shadow: 0 4px 12px rgba(0, 123, 255, 0.4);
    }
    
    /* Botón WHATSAPP (Verde) */
    div.stButton > button[kind="secondary"] {
        background-color: #238636 !important; color: white !important;
        border: none !important; box-shadow: 0 4px 12px rgba(35, 134, 54, 0.4);
    }

    .ticker-card {
        background: linear-gradient(145deg, #161b22 0%, #0d1117 100%);
        border: 1px solid #30363d;
        border-radius: 12px;
        padding: 18px;
        margin-bottom: 10px;
    }
    .t-symbol { font-family: 'Space Mono', monospace; font-size: 1.3rem; color: #58a6ff; font-weight:700; }
    .t-price { font-size: 1.7rem; font-weight: 700; color: #ffffff; }
    .t-market { font-size: 0.7rem; background: #21262d; padding: 2px 6px; border-radius: 4px; color: #8b949e; }
</style>
""", unsafe_allow_html=True)

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

# ─────────────────────────────────────────────────────────────
# 2. MOTOR TÉCNICO MULTI-MERCADO
# ─────────────────────────────────────────────────────────────
def analizar_activo(symbol):
    try:
        symbol = str(symbol).strip().upper()
        tk = yf.Ticker(symbol)
        # 60 días para EMAs
        df = tk.history(period="60d", interval="1d")
        
        if len(df) < 20: return None

        # Indicadores Técnicos
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))

        precio = df['Close'].iloc[-1]
        ayer = df['Close'].iloc[-2]
        gap = ((precio - ayer) / ayer) * 100
        
        # Detección de Mercado y Moneda
        es_cedear = ".BA" in symbol
        moneda = "$" if es_cedear else "USD"
        mercado = "BYMA (Arg)" if es_cedear else "NYSE/NASDAQ (USA)"

        return {
            "Ticker": symbol, "Precio": round(precio, 2), "GAP": round(gap, 2),
            "Moneda": moneda, "Mercado": mercado, "RSI": round(df['RSI'].iloc[-1], 1),
            "EMA9": round(df['EMA9'].iloc[-1], 2),
            "Data": df.tail(30).reset_index()
        }
    except: return None

# ─────────────────────────────────────────────────────────────
# 3. INTERFAZ Y SIDEBAR
# ─────────────────────────────────────────────────────────────
st.title("📡 Quantum 3.0 | USA & CEDEARs")

with st.sidebar:
    st.header("🔍 Modo de Análisis")
    
    # Cargar lista del CSV para el buscador
    if os.path.exists(RUTA_CSV):
        df_csv = pd.read_csv(RUTA_CSV)
        col_name = [c for c in df_csv.columns if 'tick' in c.lower()][0]
        lista_completa = df_csv[col_name].dropna().unique().tolist()
    else:
        lista_completa = ["AAPL", "TSLA", "GGAL.BA", "AAPL.BA"]

    # Buscador de activos específicos
    activos_manuales = st.multiselect("🎯 Elegir activos específicos:", lista_completa, help="Si eliges activos aquí, se ignorarán los filtros de GAP y Precio.")
    
    st.divider()
    st.header("⚙️ Filtros de Escaneo")
    st.caption("Solo aplican si no eliges activos específicos arriba.")
    p_min = st.number_input("Precio Mín ($/USD)", 0.0, 1000000.0, 1.0)
    p_max = st.number_input("Precio Máx ($/USD)", 0.0, 1000000.0, 500000.0)
    gap_min = st.slider("GAP Mínimo (%)", -10.0, 20.0, 0.5)
    
    st.divider()
    st.subheader("📱 WhatsApp")
    celular = st.text_input("Número", "5492664300161")
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")

# ─────────────────────────────────────────────────────────────
# 4. EJECUCIÓN LÓGICA
# ─────────────────────────────────────────────────────────────
if 'resultados_v3' not in st.session_state:
    st.session_state.resultados_v3 = []

c1, c2 = st.columns([1, 4])

with c1:
    # Cambia el nombre del botón según el modo
    txt_boton = "🎯 ANALIZAR SELECCIÓN" if activos_manuales else "🚀 INICIAR ESCANEO"
    if st.button(txt_boton, type="primary"):
        # Elegir qué lista procesar
        target = activos_manuales if activos_manuales else lista_completa
        
        with st.spinner("Procesando señales técnicas..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                res = [r for r in list(executor.map(analizar_activo, target)) if r is not None]
                
                # Filtrar solo si es escaneo general
                if not activos_manuales:
                    res = [r for r in res if p_min <= r['Precio'] <= p_max and r['GAP'] >= gap_min]
                
                st.session_state.resultados_v3 = sorted(res, key=lambda x: x['GAP'], reverse=True)[:9]

if st.session_state.resultados_v3:
    with c2:
        if st.button("📱 ENVIAR REPORTE SELECCIONADO", type="secondary"):
            try:
                msg = f"🚀 *REPORTE QUANTUM 3.0*\n"
                for r in st.session_state.resultados_v2:
                    msg += f"🔹 *{r['Ticker']}*: {r['Moneda']}{r['Precio']} ({r['GAP']}%)\n   RSI: {r['RSI']} | {r['Mercado']}\n"
                greenAPI = API.GreenApi(id_ins, token_ins)
                greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                st.toast("Enviado correctamente", icon="✅")
            except: st.error("Error WhatsApp")

    # GRID DE RESULTADOS
    st.divider()
    cols = st.columns(3)
    for i, res in enumerate(st.session_state.resultados_v3):
        with cols[i % 3]:
            color_gap = "#3fb950" if res['GAP'] > 0 else "#f85149"
            st.markdown(f"""
            <div class="ticker-card">
                <div style="display:flex; justify-content:space-between;">
                    <span class="t-symbol">{res['Ticker']}</span>
                    <span class="t-market">{res['Mercado']}</span>
                </div>
                <div class="t-price">{res['Moneda']} {res['Precio']}</div>
                <div style="color:{color_gap}; font-weight:700; font-size:1.1rem;">
                    {"+" if res['GAP']>0 else ""}{res['GAP']}%
                </div>
                <div style="font-size:0.8rem; color:#8b949e; margin-top:8px; font-family:monospace;">
                    RSI: {res['RSI']} | EMA9: {res['Moneda']}{res['EMA9']}
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Gráfico de tendencia
            chart = alt.Chart(res['Data']).mark_area(
                line={'color': '#58a6ff'},
                color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#58a6ff', offset=0), alt.GradientStop(color='#0d1117', offset=1)], x1=1, y1=1, x2=1, y2=0),
                opacity=0.3
            ).encode(
                x=alt.X('Date:T', axis=None),
                y=alt.Y('Close:Q', scale=alt.Scale(zero=False), axis=None)
            ).properties(height=80)
            st.altair_chart(chart, use_container_width=True)
else:
    st.info("💡 Consejo: Selecciona activos específicos en la barra lateral para un monitoreo directo, o dale a 'Escaneo' para descubrir oportunidades.")
