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
    p_min = st.number_input("Precio Mín ($)", 0.0, 1000.0, 0.50)
    p_max = st.number_input("Precio Máx ($)", 0.0, 1000.0, 100.0)
    gap_min_input = st.slider("GAP Mínimo (%)", -5.0, 10.0, 0.0)
    st.divider()
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# 4. MOTOR DE BÚSQUEDA ROBUSTO
def analizar_ticker(ticker_raw):
    try:
        symbol = str(ticker_raw).strip().upper()
        t = yf.Ticker(symbol)
        
        # Usamos period="2d" para asegurar que tenemos el cierre de ayer y el precio de hoy
        df = t.history(period="2d")
        
        if df.empty or len(df) < 2:
            return None
            
        cierre_ayer = df['Close'].iloc[0]
        precio_hoy = df['Close'].iloc[1]
        vol_hoy = df['Volume'].iloc[1]
        
        gap = ((precio_hoy - cierre_ayer) / cierre_ayer) * 100
        
        # Filtro básico: Precio y GAP (Sin filtro de volumen para asegurar que funcione)
        if p_min <= precio_hoy <= p_max and gap >= gap_min_input:
            # Traemos 1 mes solo para el gráfico si pasa el filtro
            hist_grafico = t.history(period="1mo")
            df_plot = hist_grafico[['Close']].reset_index()
            df_plot.columns = ['x', 'y']
            
            return {
                "Ticker": symbol,
                "Precio": round(precio_hoy, 2),
                "GAP": round(gap, 2),
                "Vol": f"{int(vol_hoy):,}",
                "Data": df_plot
            }
    except:
        return None
    return None

# 5. INTERFAZ
if os.path.exists(RUTA_CSV):
    df_csv = pd.read_csv(RUTA_CSV)
    tickers = df_csv['Ticker'].dropna().unique().tolist()
    st.sidebar.write(f"📊 {len(tickers)} activos cargados.")
    
    if st.button("🔍 INICIAR ESCANEO"):
        with st.spinner("Analizando mercado..."):
            # Bajamos workers para evitar bloqueos de Yahoo
            with ThreadPoolExecutor(max_workers=10) as executor:
                resultados = [r for r in list(executor.map(analizar_ticker, tickers)) if r is not None]
            
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
                                <div style="font-size:0.7rem; color:#666;">Vol: {res['Vol']}</div>
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
                ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                msg = f"🔔 *REPORT* ({ahora.strftime('%H:%M')})\n"
                for r in top_6: msg += f"📈 {r['Ticker']} | ${r['Precio']} | {r['GAP']}% | Vol: {r['Vol']}\n"
                try:
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                except: pass
                st.success("✅ Escaneo finalizado.")
            else:
                st.warning("No se encontraron coincidencias. Prueba poner el GAP en -2% para verificar que el sistema lee datos.")
else:
    st.error("⚠️ El archivo CSV no está en GitHub.")
