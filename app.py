import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os
import altair as alt

# 1. CONFIGURACIÓN DE PÁGINA
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
    .vol-info { font-size: 0.75rem; color: #666; margin-top: 4px; }
    </style>
    """, unsafe_allow_html=True)

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

st.title("🚀 Scanner Momentum Real-Time")

# 3. SIDEBAR
with st.sidebar:
    st.header("⚙️ Filtros")
    p_min = st.number_input("Precio Mín ($)", 0.01, 1000.0, 0.50)
    p_max = st.number_input("Precio Máx ($)", 0.01, 1000.0, 50.0)
    gap_min_input = st.slider("GAP Mínimo (%)", -2.0, 20.0, 0.0)
    st.divider()
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# 4. LÓGICA DE ANÁLISIS (SIN FILTRO DE VOLUMEN DE HOY)
def obtener_datos(ticker_raw):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        
        # Traemos historial de 1 mes (esto es muy estable)
        df = stock.history(period="1mo")
        if df.empty or len(df) < 2: return None
        
        cierre_previo = df['Close'].iloc[-1]
        vol_promedio = df['Volume'].tail(5).mean() # Promedio de los últimos 5 días
        
        # Intentamos obtener el precio actual. Si falla, usamos el último cierre.
        try:
            precio_actual = stock.fast_info['last_price']
        except:
            precio_actual = cierre_previo
        
        # Si el precio actual es 0 o None, usamos el cierre previo
        if not precio_actual or precio_actual == 0:
            precio_actual = cierre_previo

        # Cálculo de GAP: (Actual / Cierre de Ayer)
        gap_real = ((precio_actual - cierre_previo) / cierre_previo) * 100
        
        # FILTROS: Solo Precio y GAP (El volumen se muestra pero no bloquea)
        if p_min <= precio_actual <= p_max and gap_real >= gap_min_input:
            df_plot = df[['Close']].reset_index()
            df_plot.columns = ['x', 'y']
            return {
                "Ticker": ticker, 
                "Precio": round(precio_actual, 2), 
                "GAP": round(gap_real, 2), 
                "VolProm": f"{int(vol_promedio):,}", 
                "Data": df_plot
            }
    except:
        return None
    return None

# 5. EJECUCIÓN
if os.path.exists(RUTA_CSV):
    tickers_list = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
    
    if st.button("🔍 INICIAR ESCANEO"):
        with st.spinner("Buscando GAPs..."):
            # Aumentamos trabajadores para ir más rápido
            with ThreadPoolExecutor(max_workers=25) as executor:
                resultados = [r for r in list(executor.map(obtener_datos, tickers_list)) if r is not None]
            
            if resultados:
                # Top 6 por mayor GAP
                top_6 = sorted(resultados, key=lambda x: x['GAP'], reverse=True)[:6]
                cols = st.columns(3)
                
                for i, res in enumerate(top_6):
                    with cols[i % 3]:
                        st.markdown(f"""
                            <div class="ticker-card">
                                <div class="ticker-name">{res['Ticker']}</div>
                                <div class="ticker-price">${res['Precio']}</div>
                                <div class="ticker-gap">GAP: {res['GAP']}%</div>
                                <div class="vol-info">Vol Prom: {res['VolProm']}</div>
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
                
                # Reporte WhatsApp
                ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                msg = f"🔔 *REPORT* ({ahora.strftime('%H:%M')})\n"
                for r in top_6: msg += f"📈 {r['Ticker']} | ${r['Precio']} | {r['GAP']}% | Vol: {r['VolProm']}\n"
                
                try:
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                    st.success("📱 WhatsApp enviado")
                except: st.error("Error API WhatsApp")
            else:
                st.warning("No se encontraron activos. Prueba bajar el GAP a 0.")
else:
    st.error("CSV no encontrado.")
