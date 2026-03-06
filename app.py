import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os
import altair as alt
import requests

# 1. CONFIGURACIÓN
st.set_page_config(page_title="Scanner Momentum USA", layout="wide")

# 2. ESTILO CSS
st.markdown("""
    <style>
    .ticker-card {
        background-color: #ffffff;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 0px;
        border-left: 5px solid #28a745;
    }
    .ticker-name { color: #007bff; font-size: 1.1rem; font-weight: bold; }
    .ticker-price { font-size: 1.2rem; font-weight: bold; color: #1f1f1f; }
    .ticker-gap { font-size: 0.95rem; font-weight: bold; color: #28a745; }
    </style>
    """, unsafe_allow_html=True)

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

st.title("🚀 Scanner Momentum USA")

# 3. SIDEBAR
with st.sidebar:
    st.header("⚙️ Filtros")
    p_min = st.number_input("Precio Mín ($)", 0.0, 5000.0, 0.10)
    p_max = st.number_input("Precio Máx ($)", 0.0, 5000.0, 2000.0)
    gap_min_input = st.slider("GAP Mínimo (%)", -30.0, 30.0, -5.0)
    st.divider()
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# 4. MOTOR CON "USER-AGENT" PARA EVITAR BLOQUEOS
def analizar_ticker(symbol):
    try:
        symbol = str(symbol).strip().upper()
        # Usamos una sesión para que Yahoo crea que somos un navegador
        session = requests.Session()
        session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        
        t = yf.Ticker(symbol, session=session)
        # Pedimos el periodo más corto posible para no saturar
        hist = t.history(period="5d")
        
        if hist.empty or len(hist) < 2: return None
            
        precio_actual = hist['Close'].iloc[-1]
        cierre_previo = hist['Close'].iloc[-2]
        gap = ((precio_actual - cierre_previo) / cierre_previo) * 100
        
        if p_min <= precio_actual <= p_max and gap >= gap_min_input:
            df_plot = hist[['Close']].reset_index()
            df_plot.columns = ['x', 'y']
            return {"Ticker": symbol, "Precio": round(precio_actual, 2), "GAP": round(gap, 2), "Data": df_plot}
    except: return None
    return None

# 5. CARGA Y EJECUCIÓN
if os.path.exists(RUTA_CSV):
    try:
        df_csv = pd.read_csv(RUTA_CSV)
        col_ticker = [c for c in df_csv.columns if 'tick' in c.lower()][0]
        tickers = df_csv[col_ticker].dropna().unique().tolist()
        st.sidebar.success(f"📊 {len(tickers)} activos listos.")
        
        if st.button("🔍 INICIAR ESCANEO SEGURO"):
            bar = st.progress(0)
            resultados = []
            
            # Solo procesamos los primeros 100 para probar si hay bloqueo de IP
            # Si esto funciona, luego lo abrimos a los 739
            tickers_prueba = tickers[:100]
            
            with st.spinner("Bypass de seguridad en curso..."):
                # Bajamos a 2 workers para no levantar sospechas en el servidor
                with ThreadPoolExecutor(max_workers=2) as executor:
                    for i, res in enumerate(executor.map(analizar_ticker, tickers_prueba)):
                        if res: resultados.append(res)
                        bar.progress((i + 1) / len(tickers_prueba))
                
                if resultados:
                    top_6 = sorted(resultados, key=lambda x: x['GAP'], reverse=True)[:6]
                    cols = st.columns(3)
                    for i, res in enumerate(top_6):
                        with cols[i % 3]:
                            st.markdown(f'<div class="ticker-card"><div class="ticker-name">{res["Ticker"]}</div><div class="ticker-price">${res["Precio"]}</div><div class="ticker-gap">GAP: {res["GAP"]}%</div></div>', unsafe_allow_html=True)
                            chart = alt.Chart(res['Data']).mark_area(line={'color': '#28a745'}, color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#d4edda', offset=0), alt.GradientStop(color='white', offset=1)], x1=1, y1=1, x2=1, y2=0), opacity=0.4).encode(x=alt.X('x:T', axis=None), y=alt.Y('y:Q', axis=None, scale=alt.Scale(zero=False))).properties(height=70)
                            st.altair_chart(chart, use_container_width=True)
                else:
                    st.error("Yahoo Finance bloqueó la petición masiva. Intentando otro método...")
                    # Intento desesperado: Probar con un solo ticker conocido
                    test = analizar_ticker("AAPL")
                    if test: st.write("Conexión individual OK (AAPL encontrada). El problema es el volumen de datos.")
    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.error("CSV no encontrado.")
