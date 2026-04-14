import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Trading Quad-Scan", layout="wide", page_icon="🇺🇸")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .ticker-card {
        background-color: #ffffff;
        border-radius: 12px;
        padding: 15px;
        border-left: 6px solid #1A73E8;
        margin-bottom: 5px;
        box-shadow: 0px 2px 8px rgba(0,0,0,0.08);
        color: #1e1e1e !important;
    }
    .ticker-card h3 { color: #1A73E8 !important; }
    .type-label { font-size: 0.8em; color: #5f6368; font-weight: normal; }
    .neg-label { color: #D93025; font-weight: bold; }
    .exit-label { color: #1E8E3E; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- MOTOR DE ANÁLISIS ---
def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y") 
        if df.empty or len(df) < 50: return None

        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        if not (p_min <= precio_act <= p_max) or gap < gap_min: return None

        # Indicadores Técnicos
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rsi_serie = 100 - (100 / (1 + (gain / loss)))
        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        
        # Datos para gráfico (Últimos 25 días)
        last_25 = df.tail(25).copy()
        rsi_25 = rsi_serie.tail(25)
        # Formato de fecha corto para ahorrar espacio
        last_25.index = last_25.index.strftime('%d/%m')

        score = 50
        if rsi_serie.iloc[-1] > 50: score += 20
        if gap > 1: score += 10

        return {
            "Ticker": ticker,
            "Tipo": "ETF" if stock.info.get('quoteType') == "ETF" else "ACCIÓN",
            "Precio": round(precio_act, 2),
            "Gap": round(gap, 2),
            "Confianza": int(score),
            "SL": round(precio_act - (2 * atr), 2),
            "TP": round(precio_act + (3 * atr), 2),
            "df_plot": last_25,
            "rsi_plot": rsi_25
        }
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Configuración")
    p_min_in = st.number_input("Precio Mín ($)", 0.0, 5000.0, 5.0)
    p_max_in = st.number_input("Precio Máx ($)", 0.0, 5000.0, 1500.0)
    gap_min_in = st.slider("GAP Mínimo (%)", -5.0, 10.0, 0.5)
    st.divider()
    id_ins = st.text_input("ID Green API", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

st.title("🚀 Escáner USA: Inteligencia de Mercado")
RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

if st.button("🔍 ANALIZAR MERCADO"):
    if os.path.exists(RUTA_CSV):
        tickers = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
        with st.spinner("Escaneando activos..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                res = [r for r in list(ex.map(lambda x: analizar_activo(x, p_min_in, p_max_in, gap_min_in), tickers)) if r is not None]
            st.session_state['resultados'] = sorted(res, key=lambda x: x['Confianza'], reverse=True)[:6]
    else:
        st.error("Archivo CSV no detectado.")

# --- RESULTADOS ---
if 'resultados' in st.session_state and st.session_state['resultados']:
    cols = st.columns(2)
    for i, r in enumerate(st.session_state['resultados']):
        with cols[i % 2]:
            st.markdown(f"""
                <div class="ticker-card">
                    <h3 style='margin:0;'>{r['Ticker']} <span class="type-label">({r['Tipo']})</span> — ${r['Precio']}</h3>
                    <p style='margin:5px 0;'>🎯 Confianza: <b>{r['Confianza']}/100</b> | GAP: +{r['Gap']}%</p>
                    <p style='margin:5px 0;'>🛑 SL: <span class="neg-label">${r['SL']}</span> | 🚀 EXIT: <span class="exit-label">${r['TP']}</span></p>
                </div>
                """, unsafe_allow_html=True)
            
            # --- GRÁFICO PROFESIONAL ---
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=r['df_plot'].index, y=r['df_plot']['Close'], name="Precio", line=dict(color='#1A73E8', width=3)))
            fig.add_trace(go.Scatter(x=r['df_plot'].index, y=r['rsi_plot'], name="RSI", line=dict(color='#D93025', width=1.5, dash='dot'), yaxis="y2"))

            fig.update_layout(
                height=280,
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                showlegend=False,
                xaxis=dict(
                    showgrid=False, 
                    nticks=5, # <--- Limita las fechas mostradas para evitar amontonamiento
                    tickfont=dict(size=10, color="#5f6368")
                ),
                yaxis=dict(showgrid=True, gridcolor='#f0f0f0', tickfont=dict(size=10)),
                yaxis2=dict(overlaying='y', side='right', range=[0, 100], showgrid=False, tickfont=dict(size=10, color='#D93025'))
            )
            st.plotly_chart(fig, use_container_width=True, key=f"plot_{r['Ticker']}_{i}", config={'displayModeBar': False})

    if st.button("📲 ENVIAR ALERTAS WHATSAPP"):
        ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
        msg = f"🇺🇸 *OPORTUNIDADES USA*\n_{ahora.strftime('%d/%m %H:%M')}_\n━━━━━━━━━━━━━━━━━━\n"
        for r in st.session_state['resultados']:
            msg += f"🚀 *{r['Ticker']}* | ${r['Precio']}\n   - SL: ${r['SL']} | EXIT: ${r['TP']}\n\n"
        try:
            greenAPI = API.GreenApi(id_ins, token_ins)
            greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
            st.success("Alertas enviadas con éxito.")
        except: 
            st.error("Error al conectar con la API de WhatsApp.")
