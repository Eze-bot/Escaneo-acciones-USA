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
st.set_page_config(page_title="Scanner GAP & Volumen", layout="wide")

# 2. ESTILO CSS
st.markdown("""
    <style>
    .ticker-card {
        background-color: #ffffff;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 12px;
        margin-bottom: 0px;
    }
    .ticker-name { color: #007bff; font-size: 1.1rem; font-weight: bold; }
    .ticker-price { font-size: 1.2rem; font-weight: bold; color: #1f1f1f; }
    .ticker-gap { font-size: 0.95rem; font-weight: bold; }
    .vol-badge { font-size: 0.8rem; background-color: #f1f3f4; padding: 2px 5px; border-radius: 4px; color: #5f6368; }
    </style>
    """, unsafe_allow_html=True)

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"
st.title("🚀 Momentum: GAP + Volumen Pre-Market")

# 3. SIDEBAR
with st.sidebar:
    st.header("⚙️ Filtros")
    p_min = st.number_input("Precio Mín ($)", 0.01, 1000.0, 0.50)
    p_max = st.number_input("Precio Máx ($)", 0.01, 1000.0, 17.0)
    gap_min_input = st.slider("GAP Mínimo (%)", 0.0, 20.0, 2.0)
    vol_min_input = st.number_input("Volumen Mín Pre-market", 0, 1000000, 5000)
    st.divider()
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("Número", "5492664300161")

# 4. LÓGICA DE ANÁLISIS
def obtener_datos(ticker_raw):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        
        # Historial para cierre previo y gráfico
        df = stock.history(period="1mo")
        if len(df) < 2: return None
        cierre_ayer = df['Close'].iloc[-1]
        
        # Datos en tiempo real (Pre-market / Last)
        info = stock.fast_info
        precio_actual = info['last_price']
        vol_actual = info['last_volume'] # Volumen operado hoy (Pre-market)
        
        # Cálculo de GAP
        gap_real = ((precio_actual - cierre_ayer) / cierre_ayer) * 100
        
        # Filtros: Precio, GAP y ahora VOLUMEN MÍNIMO
        if p_min <= precio_actual <= p_max and gap_real >= gap_min_input and vol_actual >= vol_min_input:
            df_plot = df[['Close']].reset_index()
            df_plot.columns = ['x', 'y']
            
            return {
                "Ticker": ticker, 
                "Precio": round(precio_actual, 2), 
                "GAP": round(gap_real, 2), 
                "Vol": f"{vol_actual:,}", 
                "Data": df_plot,
                "RawVol": vol_actual
            }
    except: return None
    return None

# 5. RENDERIZADO
if os.path.exists(RUTA_CSV):
    tickers_list = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
    
    if st.button("🔍 ESCANEAR PRE-MARKET"):
        with st.spinner("Buscando GAPs con volumen..."):
            with ThreadPoolExecutor(max_workers=15) as executor:
                resultados = [r for r in list(executor.map(obtener_datos, tickers_list)) if r is not None]
            
            if resultados:
                # Ordenamos por GAP
                top_6 = sorted(resultados, key=lambda x: x['GAP'], reverse=True)[:6]
                cols = st.columns(3)
                
                for i, res in enumerate(top_6):
                    with cols[i % 3]:
                        st.markdown(f"""
                            <div class="ticker-card">
                                <div class="ticker-name">{res['Ticker']}</div>
                                <div class="ticker-price">${res['Precio']}</div>
                                <div class="ticker-gap" style="color:#28a745;">GAP: +{res['GAP']}%</div>
                                <div class="vol-badge">Vol: {res['Vol']} 📦</div>
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
                
                # WhatsApp con Info de Volumen
                ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                msg = f"🔔 *GAP & VOL* ({ahora.strftime('%H:%M')})\n"
                for r in top_6: 
                    msg += f"📈 *{r['Ticker']}* | ${r['Precio']} | GAP: {r['GAP']}% | Vol: {r['Vol']}\n"
                
                try:
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                    st.success("📱 WhatsApp enviado")
                except: st.error("Error WhatsApp")
            else:
                st.warning("No hay activos que cumplan GAP y Volumen mínimo.")
else:
    st.error("CSV no encontrado.")
