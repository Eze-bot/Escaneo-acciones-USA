import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os
import altair as alt  # IMPORTANTE: Necesario para el nuevo gráfico

# --- CONFIGURACIÓN ESTÉTICA ---
st.set_page_config(page_title="Scanner USA", layout="wide")

# CSS personalizado para las tarjetas y gráficos pequeños
st.markdown("""
    <style>
    .ticker-card {
        background-color: #ffffff;
        border: 1px solid #e6e9ef;
        border-radius: 8px;
        padding: 12px;
        margin-bottom: 12px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        color: #1f1f1f;
    }
    h3 { margin: 0 0 5px 0; color: #007bff; font-size: 1.2rem; }
    p { margin: 0; font-size: 0.9rem; }
    .stChart { height: 80px !important; margin-top: 5px; } /* Reduce la altura del gráfico */
    </style>
    """, unsafe_allow_html=True)

st.title("📈 Dashboard Top 6 Momentum")

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

# --- SIDEBAR CONFIGURACIÓN ---
with st.sidebar:
    st.header("⚙️ Configuración")
    p_min = st.number_input("Precio Mín ($)", 0.01, 1000.0, 0.50)
    p_max = st.number_input("Precio Máx ($)", 0.01, 1000.0, 17.0)
    gap_min = st.slider("GAP Mínimo (%)", 0.0, 20.0, 2.0)
    st.divider()
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# --- LÓGICA DE ANÁLISIS ---
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
            # Preparamos los datos históricos para el gráfico
            hist_data = df['Close'].reset_index()
            hist_data.columns = ['Fecha', 'Precio']
            
            return {
                "Ticker": ticker, 
                "Precio": round(cierre, 2), 
                "GAP": round(gap, 2), 
                "Hist": hist_data
            }
    except: return None
    return None

# --- EJECUCIÓN ---
if os.path.exists(RUTA_CSV):
    tickers = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
    st.sidebar.success(f"📂 {len(tickers)} Activos cargados")
    
    if st.button("🔍 ESCANEAR AHORA"):
        with st.spinner("Analizando mercado..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                res = [r for r in list(executor.map(analizar, tickers)) if r is not None]
            
            if res:
                top_6 = sorted(res, key=lambda x: x['GAP'], reverse=True)[:6]
                cols = st.columns(2)
                
                for i, r in enumerate(top_6):
                    with cols[i % 2]:
                        st.markdown(f'<div class="ticker-card"><h3>🚀 {r["Ticker"]}</h3><p>Precio: ${r["Precio"]} | GAP: +{r["GAP"]}%</p></div>', unsafe_allow_html=True)
                        
                        # --- NUEVO GRÁFICO DE ÁREA REDUCIDO ---
                        # Creamos un gráfico de área sombreada usando Altair
                        chart = alt.Chart(r["Hist"]).mark_area(
                            line={'color':'#28a745'}, # Línea verde
                            color=alt.Gradient(
                                gradient='linear',
                                stops=[alt.GradientStop(color='#d4edda', offset=0), # Sombreado verde suave
                                       alt.GradientStop(color='white', offset=1)],
                                x1=1, y1=1, x2=1, y2=0
                            )
                        ).encode(
                            x=alt.X('Fecha', axis=None), # Ocultar eje X
                            y=alt.Y('Precio', axis=None, scale=alt.Scale(domain=[r["Hist"]['Precio'].min() * 0.95, r["Hist"]['Precio'].max() * 1.05])) # Escalar eje Y y ocultar
                        ).properties(
                            height=70  # Altura reducida del gráfico
                        ).configure_view(
                            strokeWidth=0 # Quitar bordes del gráfico
                        )
                        st.altair_chart(chart, use_container_width=True) # Mostrar gráfico en Streamlit
                
                # WhatsApp
                ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                msg = f"🔔 TOP 6 TENDENCIAS ({ahora.strftime('%H:%M')})\n━━━━━━━━━━━━━━━━━━\n"
                for r in top_6:
                    msg += f"📈 *{r['Ticker']}* | ${r['Precio']} | +{r['GAP']}%\n"
                
                try:
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                    st.success("📱 Reporte enviado por WhatsApp")
                except: st.error("Error al enviar WhatsApp. Revisa los datos de API.")
            else:
                st.warning("No se encontraron activos que cumplan los filtros hoy.")
else:
    st.error(f"No se encontró el archivo '{RUTA_CSV}' en GitHub. Asegúrate de subirlo.")
