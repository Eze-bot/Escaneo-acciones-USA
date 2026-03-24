import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="AI Trading Quad-Scan", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
   <style>
   .ticker-card {
       background-color: #1e1e1e;
       border-radius: 12px;
       padding: 15px;
       border: 1px solid #333;
       color: white !important;
       margin-bottom: 5px;
    }
   .price-text { font-size: 1.3em; font-weight: bold; color: #1A73E8; }
   .profit-tag { background-color: #00c85322; color: #00c853; padding: 2px 6px; border-radius: 4px; font-weight: bold; }
   .trend-label { font-size: 0.85em; font-weight: bold; }
   </style>
   """, unsafe_allow_html=True)

def analizar_activo(ticker_raw, p_min_val, p_max_val, g_min_val):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if df.empty or len(df) < 200: 
            return None

        # --- TENDENCIA SMA 200 ---
        sma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        precio_act = df['Close'].iloc[-1]
        tendencia = "ALCISTA 🟢" if precio_act > sma200 else "BAJISTA 🔴"
        t_color = "#00c853" if precio_act > sma200 else "#ff4b4b"

        # --- GAP Y TÉCNICOS ---
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        if not (p_min_val <= precio_act <= p_max_val) or gap < g_min_val: 
            return None

        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        
        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_serie = 100 - (100 / (1 + (gain / loss)))

        # --- LÓGICA 2:1 + COMISIÓN ---
        riesgo = atr * 1.5
        sl = precio_act - riesgo
        exit_p = (precio_act + (riesgo * 2)) * 1.01
        ganancia_neta = ((exit_p / (precio_act * 1.005)) - 1) * 100

        # Datos gráfico (25 días)
        last_25 = df.tail(25).copy()
        last_25.index = last_25.index.strftime('%d %b')

        return {
            "Ticker": ticker, 
            "Tipo": "ETF" if stock.info.get('quoteType') == "ETF" else "ACCIÓN",
            "Precio": round(precio_act, 2), 
            "Gap": round(gap, 2),
            "SL": round(sl, 2), 
            "TP": round(exit_p, 2),
            "Neto": round(ganancia_neta, 1), 
            "Tendencia": tendencia, 
            "T_Color": t_color,
            "df_plot": last_25, 
            "rsi_plot": rsi_serie.tail(25)
        }
    except: 
        return None

# --- UI SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    p_min_in = st.number_input("Precio Mín", 0.0, 5000.0, 5.0)
    p_max_in = st.number_input("Precio Máx", 0.0, 5000.0, 1500.0)
    g_min_in = st.slider("GAP Mín %", -5.0, 10.0, 0.5)
    st.divider()
    id_ins = st.text_input("ID Green API", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

st.title("🚀 Escáner USA: Estrategia 2:1")

# --- BOTÓN DE ANÁLISIS ---
if st.button("🔍 ANALIZAR MERCADO"):
    if os.path.exists("ACTIVOS_BULLMARKET_USA.csv"):
        tickers = pd.read_csv("ACTIVOS_BULLMARKET_USA.csv")['Ticker'].tolist()
        with st.spinner("Escaneando activos..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                res = [r for r in list(ex.map(lambda x: analizar_activo(x, p_min_in, p_max_in, g_min_in), tickers)) if r is not None]
            st.session_state['res'] = sorted(res, key=lambda x: x['Neto'], reverse=True)[:6]
    else: 
        st.error("Archivo CSV no encontrado.")

# --- MOSTRAR RESULTADOS ---
if 'res' in st.session_state:
    finales = st.session_state['res']
    for r in finales:
        st.markdown(f"""
            <div class="ticker-card">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <span class="price-text">{r['Ticker']} — ${r['Precio']}</span>
                    <span style="color:{r['T_Color']};" class="trend-label">{r['Tendencia']}</span>
                </div>
                <div style="margin-top:8px;">
                    <span class="type-label">({r['Tipo']})</span> | 📈 GAP: {r['Gap']}% | <span class="profit-tag">+{r['Neto']}% Neto</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Gráfico Plotly con líneas de niveles
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=r['df_plot'].index, y=r['df_plot']['Close'], name="Precio", line=dict(color='#1A73E8', width=3)))
        fig.add_trace(go.Scatter(x=r['df_plot'].index, y=r['rsi_plot'], name="RSI", line=dict(color='#ff4b4b', width=1.5, dash='dot'), yaxis="y2"))
        
        fig.add_hline(y=r['TP'], line_dash="dash", line_color="#00c853", annotation_text=f"EXIT: ${r['TP']}")
        fig.add_hline(y=r['SL'], line_dash="dash", line_color="#ff4b4b", annotation_text=f"SL: ${r['SL']}")

        fig.update_layout(
            height=280, 
            margin=dict(l=0, r=0, t=20, b=0), 
            paper_bgcolor='rgba(0,0,0,0)', 
            plot_bgcolor='rgba(0,0,0,0)', 
            showlegend=False,
            yaxis2=dict(overlaying='y', side='right', range=[0, 100], showgrid=False)
        )
        st.plotly_chart(fig, use_container_width=True)

    # --- BOTÓN WHATSAPP ---
    if st.button("📲 ENVIAR ALERTAS WHATSAPP"):
        msg = f"🇺🇸 *OPORTUNIDADES USA*\n━━━━━━━━━━━━━━━━━━\n"
        for r in finales:
            msg += f"🚀 *{r['Ticker']}* | ${r['Precio']}\n   • Tendencia: {r['Tendencia']}\n   • EXIT: ${r['TP']} (+{r['Neto']}%)\n   • SL: ${r['SL']}\n\n"
        try:
            greenAPI = API.GreenApi(id_ins, token_ins)
            greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
            st.success("Alertas enviadas.")
        except: 
            st.error("Error en el envío.")
