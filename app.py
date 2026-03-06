import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os
import altair as alt

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
    p_max = st.number_input("Precio Máx ($)", 0.0, 5000.0, 1000.0)
    gap_min_input = st.slider("GAP Mínimo (%)", -10.0, 20.0, -5.0)
    st.divider()
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# 4. MOTOR DE ESCANEO ROBUSTO (Usa historial de 5 días para evitar errores de fecha)
def analizar_ticker(symbol):
    try:
        symbol = str(symbol).strip().upper()
        t = yf.Ticker(symbol)
        
        # Pedimos 5 días para asegurar que siempre haya datos previos
        hist = t.history(period="5d")
        if hist.empty or len(hist) < 2:
            return None
            
        # Tomamos el último precio y el precio inmediatamente anterior
        precio_actual = hist['Close'].iloc[-1]
        cierre_previo = hist['Close'].iloc[-2]
        
        # Si el mercado está cerrado, esto comparará Cierre vs Cierre anterior
        # Si el mercado está en pre-market/abierto, comparará Actual vs Cierre de ayer
        gap = ((precio_actual - cierre_previo) / cierre_previo) * 100
        
        if p_min <= precio_actual <= p_max and gap >= gap_min_input:
            # Reutilizamos el historial para el gráfico (últimos 30 días para estética)
            hist_full = t.history(period="1mo")
            df_plot = hist_full[['Close']].reset_index()
            df_plot.columns = ['x', 'y']
            
            return {
                "Ticker": symbol,
                "Precio": round(precio_actual, 2),
                "GAP": round(gap, 2),
                "Data": df_plot
            }
    except:
        return None
    return None

# 5. EJECUCIÓN
if os.path.exists(RUTA_CSV):
    tickers = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
    st.sidebar.write(f"📊 {len(tickers)} activos detectados.")
    
    if st.button("🔍 EJECUTAR ESCANEO"):
        bar = st.progress(0)
        resultados = []
        
        with st.spinner("Analizando..."):
            # Usamos 5 workers para balancear velocidad y evitar bloqueos
            with ThreadPoolExecutor(max_workers=5) as executor:
                for i, res in enumerate(executor.map(analizar_ticker, tickers)):
                    if res:
                        resultados.append(res)
                    bar.progress((i + 1) / len(tickers))
            
            if resultados:
                top_6 = sorted(resultados, key=lambda x: x['GAP'], reverse=True)[:6]
                cols = st.columns(3)
                for i, res in enumerate(top_6):
                    with cols[i % 3]:
                        st.markdown(f"""
                            <div class="ticker-card">
                                <div class="ticker-name">{res['Ticker']}</div>
                                <div class="ticker-price">${res['Precio']}</div>
                                <div class="ticker-gap">GAP: {res['GAP']}%</div>
                            </div>
                        """, unsafe_allow_html=True)
                        
                        chart = alt.Chart(res['Data']).mark_area(
                            line={'color': '#28a745', 'strokeWidth': 2},
                            color=alt.Gradient(
                                gradient='linear',
                                stops=[alt.GradientStop(color='#d4edda', offset=0), alt.GradientStop(color='white', offset=1)],
                                x1=1, y1=1, x2=1, y2=0
                            ),
                            opacity=0.4
                        ).encode(
                            x=alt.X('x:T', axis=None),
                            y=alt.Y('y:Q', axis=None, scale=alt.Scale(zero=False))
                        ).properties(height=70)
                        st.altair_chart(chart, use_container_width=True)
                
                # WhatsApp
                try:
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    msg = "🔔 *TOP 6 MOMENTUM*\n" + "\n".join([f"📈 {r['Ticker']} | ${r['Precio']} | {r['GAP']}%" for r in top_6])
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                except: pass
            else:
                st.error("No se encontraron resultados con los filtros actuales.")
else:
    st.error("Archivo CSV no encontrado.")
