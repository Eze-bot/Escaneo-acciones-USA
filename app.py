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
        padding: 15px;
        margin-bottom: 10px;
        border-top: 4px solid #2196F3;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .ticker-name { color: #007bff; font-size: 1.2rem; font-weight: bold; }
    .ticker-price { font-size: 1.4rem; font-weight: bold; color: #1f1f1f; }
    .ticker-gap { font-size: 1rem; color: #28a745; font-weight: bold; }
    .ticker-range { font-size: 0.75rem; color: #777; margin-top: 5px; }
    </style>
    """, unsafe_allow_html=True)

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"
st.title("🚀 Scanner Momentum USA")

# 3. SIDEBAR
with st.sidebar:
    st.header("⚙️ Configuración")
    p_min = st.number_input("Precio Mín ($)", 0.01, 2000.0, 0.50)
    p_max = st.number_input("Precio Máx ($)", 0.01, 2000.0, 50.0)
    gap_min = st.slider("GAP Mínimo (%)", -5.0, 20.0, 1.0)
    st.divider()
    st.subheader("📱 WhatsApp (Manual)")
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("Número destino", "5492664300161")

# 4. FUNCIÓN OBTENER DATOS
def obtener_datos(ticker_raw):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        df = stock.history(period="1mo")
        if len(df) < 5: return None
        
        precio = df['Close'].iloc[-1]
        ayer = df['Close'].iloc[-2]
        gap = ((precio - ayer) / ayer) * 100
        
        if p_min <= precio <= p_max and gap >= gap_min:
            df_plot = df[['Close']].reset_index()
            df_plot.columns = ['x', 'y']
            return {
                "Ticker": ticker, "Precio": round(precio, 2), "GAP": round(gap, 2), 
                "Data": df_plot, "Min": round(df['Close'].min(), 2), "Max": round(df['Close'].max(), 2)
            }
    except: return None
    return None

# 5. LÓGICA DE INTERFAZ
if os.path.exists(RUTA_CSV):
    # Cargar Tickers
    df_csv = pd.read_csv(RUTA_CSV)
    col_ticker = [c for c in df_csv.columns if 'tick' in c.lower()][0]
    tickers_list = df_csv[col_ticker].dropna().unique().tolist()
    
    # Inicializar estado si no existe
    if 'resultados' not in st.session_state:
        st.session_state.resultados = []

    # FILA DE BOTONES
    col_btn1, col_btn2 = st.columns([1, 4])
    
    with col_btn1:
        if st.button("🔍 ESCANEAR"):
            with st.spinner("Analizando..."):
                with ThreadPoolExecutor(max_workers=10) as executor:
                    res = [r for r in list(executor.map(obtener_datos, tickers_list)) if r is not None]
                    st.session_state.resultados = sorted(res, key=lambda x: x['GAP'], reverse=True)[:6]
            if not st.session_state.resultados:
                st.warning("Sin resultados.")

    # Botón de WhatsApp solo si hay datos guardados en la sesión
    if st.session_state.resultados:
        with col_btn2:
            if st.button("📱 ENVIAR A WHATSAPP"):
                try:
                    ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                    msg = f"🔔 *REPORTE MOMENTUM* ({ahora.strftime('%H:%M')})\n"
                    for r in st.session_state.resultados:
                        msg += f"📈 {r['Ticker']} | ${r['Precio']} | {r['GAP']}%\n"
                    
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                    st.toast("✅ ¡Enviado!", icon='🚀')
                except:
                    st.error("Error al enviar.")

        # MOSTRAR TARJETAS
        st.divider()
        cols = st.columns(3)
        for i, res in enumerate(st.session_state.resultados):
            with cols[i % 3]:
                st.markdown(f"""
                    <div class="ticker-card">
                        <div class="ticker-name">{res['Ticker']}</div>
                        <div class="ticker-price">${res['Precio']}</div>
                        <div class="ticker-gap">{"+" if res['GAP'] > 0 else ""}{res['GAP']}%</div>
                        <div class="ticker-range">Rango mes: ${res['Min']} - ${res['Max']}</div>
                    </div>
                """, unsafe_allow_html=True)
                
                chart = alt.Chart(res['Data']).mark_area(
                    line={'color': '#2196F3', 'strokeWidth': 2},
                    color=alt.Gradient(gradient='linear', stops=[alt.GradientStop(color='#bbdefb', offset=0), alt.GradientStop(color='white', offset=1)], x1=1, y1=1, x2=1, y2=0),
                    opacity=0.4
                ).encode(x=alt.X('x:T', axis=None), y=alt.Y('y:Q', axis=None, scale=alt.Scale(zero=False))).properties(height=80)
                st.altair_chart(chart, use_container_width=True)
    else:
        st.info("Haz clic en Escanear para ver las mejores oportunidades del mercado.")

else:
    st.error("No se encontró el archivo CSV.")
