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
    p_min = st.number_input("Precio Mín ($)", 0.0, 1000.0, 0.10)
    p_max = st.number_input("Precio Máx ($)", 0.0, 2000.0, 500.0)
    gap_min_input = st.slider("GAP Mínimo (%)", -10.0, 20.0, -2.0)
    st.divider()
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# 4. MOTOR DE BÚSQUEDA ULTRA-SIMPLE
def analizar_ticker(symbol):
    try:
        symbol = str(symbol).strip().upper()
        t = yf.Ticker(symbol)
        
        # Intentamos obtener info básica primero
        info = t.basic_info
        precio_actual = info['last_price']
        cierre_previo = info['previous_close']
        
        if not precio_actual or not cierre_previo:
            return None
            
        gap = ((precio_actual - cierre_previo) / cierre_previo) * 100
        
        # Filtro de Precio y GAP
        if p_min <= precio_actual <= p_max and gap >= gap_min_input:
            # Solo si pasa el filtro, buscamos el historial para el gráfico
            hist = t.history(period="1mo")
            df_plot = hist[['Close']].reset_index()
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
    st.sidebar.write(f"📊 {len(tickers)} activos en lista.")
    
    if st.button("🔍 INICIAR ESCANEO"):
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        with st.spinner("Escaneando..."):
            resultados = []
            # Escaneamos en grupos pequeños para evitar bloqueos
            with ThreadPoolExecutor(max_workers=5) as executor:
                for i, res in enumerate(executor.map(analizar_ticker, tickers)):
                    if res:
                        resultados.append(res)
                    # Actualizar barra de progreso cada 10 tickers
                    if i % 10 == 0:
                        progress_bar.progress(min((i + 1) / len(tickers), 1.0))
            
            progress_bar.empty()
            
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
                    ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                    msg = f"🔔 *REPORT* ({ahora.strftime('%H:%M')})\n"
                    for r in top_6: msg += f"📈 {r['Ticker']} | ${r['Precio']} | {r['GAP']}%\n"
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                except: pass
            else:
                st.warning("Sin resultados. Intenta ampliar el rango de precio o bajar el GAP.")
else:
    st.error("CSV no encontrado.")
