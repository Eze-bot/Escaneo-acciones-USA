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
st.set_page_config(page_title="Scanner Momentum USA", layout="wide", page_icon="📊")

# 2. ESTILO CSS
st.markdown("""
    <style>
    .ticker-card {
        background-color: #ffffff;
        border: 1px solid #e6e9ef;
        border-radius: 10px;
        padding: 10px 15px;
        margin-bottom: 2px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        color: #1f1f1f;
    }
    .ticker-name { color: #007bff; font-size: 1.1rem; font-weight: bold; margin-bottom: 0px; }
    .ticker-metrics { font-size: 0.85rem; color: #444; }
    .block-container { padding-top: 2rem; }
    </style>
    """, unsafe_allow_html=True)

# 3. RUTA DEL ARCHIVO
RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

st.title("📈 Top 6 Momentum")

# 4. SIDEBAR
with st.sidebar:
    st.header("⚙️ Parámetros")
    p_min = st.number_input("Precio Mín ($)", 0.01, 1000.0, 0.50)
    p_max = st.number_input("Precio Máx ($)", 0.01, 1000.0, 17.0)
    gap_min = st.slider("GAP Mínimo (%)", 0.0, 20.0, 2.0)
    st.divider()
    st.subheader("📱 WhatsApp API")
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("Número", "5492664300161")

# 5. LÓGICA DE PROCESAMIENTO
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
            vol_rel = df['Volume'].iloc[-1] / df['Volume'].iloc[-11:-1].mean()
            
            # Formateo de datos exclusivo para Altair 4.2.2
            df_plot = df[['Close']].reset_index()
            df_plot.columns = ['x', 'y'] # Nombres de columnas simples para evitar errores
            
            return {
                "Ticker": ticker, 
                "Precio": round(precio, 2), 
                "GAP": round(gap, 2), 
                "Vol": round(vol_rel, 2), 
                "Data": df_plot
            }
    except:
        return None
    return None

# 6. INTERFAZ Y RENDERIZADO
if os.path.exists(RUTA_CSV):
    tickers_list = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
    st.sidebar.success(f"📂 {len(tickers_list)} Activos")
    
    if st.button("🔍 INICIAR ESCANEO"):
        with st.spinner("Analizando..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                resultados = [r for r in list(executor.map(obtener_datos, tickers_list)) if r is not None]
            
            if resultados:
                top_6 = sorted(resultados, key=lambda x: x['GAP'], reverse=True)[:6]
                
                for res in top_6:
                    # Tarjeta de información
                    st.markdown(f"""
                        <div class="ticker-card">
                            <div class="ticker-name">🚀 {res['Ticker']}</div>
                            <div class="ticker-metrics">Precio: <b>${res['Precio']}</b> | GAP: <span style="color:green"><b>+{res['GAP']}%</b></span> | Vol: <b>{res['Vol']}x</b></div>
                        </div>
                    """, unsafe_allow_html=True)
                    
                    # Gráfico de Área Simplificado al máximo
                    chart = alt.Chart(res['Data']).mark_area(
                        line={'color': '#28a745', 'strokeWidth': 2},
                        color=alt.Gradient(
                            gradient='linear',
                            stops=[alt.GradientStop(color='#d4edda', offset=0), 
                                   alt.GradientStop(color='white', offset=1)],
                            x1=1, y1=1, x2=1, y2=0
                        )
                    ).encode(
                        x=alt.X('x:T', axis=None), # x:T indica tiempo
                        y=alt.Y('y:Q', axis=None, scale=alt.Scale(zero=False)) # y:Q indica cantidad, zero=False ajusta el zoom
                    ).properties(height=80)
                    
                    st.altair_chart(chart, use_container_width=True)
                
                # WHATSAPP
                ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                msg = f"🔔 *TOP 6 MOMENTUM* ({ahora.strftime('%H:%M')})\n━━━━━━━━━━━━━━━━━━\n"
                for r in top_6:
                    msg += f"📈 *{r['Ticker']}* | ${r['Precio']} | +{r['GAP']}%\n"
                
                try:
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                    st.success("📱 WhatsApp enviado")
                except:
                    st.error("Error API WhatsApp")
            else:
                st.warning("Sin resultados.")
else:
    st.error("Archivo CSV no encontrado.")
