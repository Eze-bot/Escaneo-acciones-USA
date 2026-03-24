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
       margin-bottom: 10px;
    }
   .price-text { font-size: 1.4em; font-weight: bold; color: #1A73E8; }
   .profit-tag { background-color: #00c85322; color: #00c853; padding: 3px 8px; border-radius: 5px; font-weight: bold; }
   </style>
   """, unsafe_allow_html=True)

def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        if df.empty or len(df) < 50: return None

        # Datos actuales
        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        if not (p_min <= precio_act <= p_max) or gap < gap_min: return None

        # Técnicos
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_serie = 100 - (100 / (1 + (gain / loss)))

        # Lógica 2:1 + Comisiones
        riesgo = atr * 1.5
        sl = precio_act - riesgo
        exit_p = (precio_act + (riesgo * 2)) * 1.01
        ganancia_neta = ((exit_p / (precio_act * 1.005)) - 1) * 100

        # Preparar datos gráfico (últimos 25 días)
        last_25 = df.tail(25).copy()
        # Forzar fechas limpias para evitar el error de la imagen
        last_25.index = last_25.index.strftime('%d %b')

        return {
            "Ticker": ticker, "Tipo": "ETF" if stock.info.get('quoteType') == "ETF" else "ACCIÓN",
            "Precio": round(precio_act, 2), "Gap": round(gap, 2),
            "SL": round(sl, 2), "TP": round(exit_p, 2),
            "Neto": round(ganancia_neta, 1),
            "df_plot": last_25, "rsi_plot": rsi_serie.tail(25)
        }
    except: return None

# --- UI PRINCIPAL ---
st.title("🚀 Escáner USA Momentum")

with st.sidebar:
    p_min = st.number_input("Precio Mín", 0.0, 5000.0, 5.0)
    p_max = st.number_input("Precio Máx", 0.0, 5000.0, 1500.0)
    g_min = st.slider("GAP Mín %", -5.0, 10.0, 0.5)

if st.button("🔍 ANALIZAR MERCADO"):
    if os.path.exists("ACTIVOS_BULLMARKET_USA.csv"):
        tickers = pd.read_csv("ACTIVOS_BULLMARKET_USA.csv")['Ticker'].tolist()
        with st.spinner("Procesando..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                res = [r for r in list(ex.map(lambda x: analizar_activo(x, p_min, p_max, g_min), tickers)) if r is not None]
            st.session_state['res'] = sorted(res, key=lambda x: x['Neto'], reverse=True)[:6]
    else: st.error("Falta CSV")

if 'res' in st.session_state:
    for r in st.session_state['res']:
        st.markdown(f"""
            <div class="ticker-card">
                <div style="display: flex; justify-content: space-between;">
                    <span class="price-text">{r['Ticker']} ({r['Tipo']}) — ${r['Precio']}</span>
                    <span class="profit-tag">+{r['Neto']}% Neto</span>
                </div>
                <div style="margin-top:10px; font-size: 0.9em;">
                    📈 GAP: {r['Gap']}% | 🛑 SL: <span style="color:#ff4b4b">${r['SL']}</span> | 🚀 EXIT: <span style="color:#00c853">${r['TP']}</span>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # --- GRÁFICO PROFESIONAL CON DOBLE EJE ---
        fig = go.Figure()
        # Línea de Precio (Eje Y1)
        fig.add_trace(go.Scatter(x=r['df_plot'].index, y=r['df_plot']['Close'], name="Precio", line=dict(color='#1A73E8', width=2)))
        # Línea de RSI (Eje Y2)
        fig.add_trace(go.Scatter(x=r['df_plot'].index, y=r['rsi_plot'], name="RSI", line=dict(color='#ff4b4b', width=1.5, dash='dot'), yaxis="y2"))

        fig.update_layout(
            height=250, margin=dict(l=0, r=0, t=10, b=0),
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            hovermode="x unified", showlegend=False,
            xaxis=dict(showgrid=False, tickangle=0, tickfont=dict(size=10, color="grey")),
            yaxis=dict(title="Precio $", showgrid=False, tickfont=dict(color="#1A73E8")),
            yaxis2=dict(title="RSI", overlaying='y', side='right', range=[0, 100], showgrid=False, tickfont=dict(color="#ff4b4b"))
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
