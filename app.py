import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Trading Quad-Scan", layout="wide", page_icon="🇺🇸")

# --- ESTILOS CSS REFORZADOS ---
st.markdown("""
   <style>
   .ticker-card {
       background-color: #1e1e1e;
       border-radius: 12px;
       padding: 18px;
       border: 1px solid #333;
       margin-bottom: 20px;
       color: white !important;
    }
   .type-label { font-size: 0.85em; color: #aaaaaa; }
   .price-text { font-size: 1.5em; font-weight: bold; color: #1A73E8; margin: 0; }
   .data-row { display: flex; justify-content: space-between; margin: 8px 0; font-size: 0.95em; }
   .sl-label { color: #ff4b4b; font-weight: bold; }
   .exit-label { color: #00c853; font-weight: bold; }
   .profit-tag { background-color: #00c85322; color: #00c853; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; font-weight: bold; }
   </style>
   """, unsafe_allow_html=True)

# --- MOTOR DE ANÁLISIS ---
def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        
        info = stock.info
        tipo = "ETF" if info.get('quoteType') == "ETF" else "ACCIÓN"

        df = stock.history(period="1y") 
        if df.empty or len(df) < 50: return None

        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        if not (p_min <= precio_act <= p_max) or gap < gap_min: return None

        atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1]
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi_serie = 100 - (100 / (1 + (gain / loss)))
        
        riesgo = atr * 1.5
        sl = precio_act - riesgo
        beneficio_objetivo = riesgo * 2
        
        exit_price = (precio_act + beneficio_objetivo) * 1.01 
        ganancia_neta = ((exit_price / (precio_act * 1.005)) - 1) * 100

        last_30 = df.tail(30).copy()
        rsi_30 = rsi_serie.tail(30)
        
        p_min_v, p_max_v = last_30['Close'].min(), last_30['Close'].max()
        rsi_norm = ((rsi_30 - 0) / 100) * (p_max_v - p_min_v) + p_min_v
        
        # Limpieza de fechas para el gráfico
        last_30.index = last_30.index.strftime('%d %b')
        
        chart_data = pd.DataFrame({
            'Precio ($)': last_30['Close'],
            'RSI (Rojo)': rsi_norm
        })

        return {
            "Ticker": ticker, "Tipo": tipo, "Precio": round(precio_act, 2),
            "Gap": round(gap, 2), "Confianza": 80 if rsi_serie.iloc[-1] > 50 else 60,
            "SL": round(sl, 2), "TP": round(exit_price, 2),
            "GananciaPct": round(ganancia_neta, 2), "Chart": chart_data
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
    celular = st.text_input("WhatsApp destino", "5492664300161")

st.title("🚀 Escáner Pro USA")

# --- LÓGICA DE BOTÓN ---
if st.button("🔍 ANALIZAR MERCADO"):
    RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"
    if os.path.exists(RUTA_CSV):
        tickers = pd.read_csv(RUTA_CSV)['Ticker'].dropna().unique().tolist()
        with st.spinner("Escaneando Wall Street..."):
            with ThreadPoolExecutor(max_workers=10) as ex:
                res = [r for r in list(ex.map(lambda x: analizar_activo(x, p_min_in, p_max_in, gap_min_in), tickers)) if r is not None]
            st.session_state['resultados'] = sorted(res, key=lambda x: x['Precio'], reverse=True)[:6]
    else:
        st.error("Archivo CSV no detectado.")

# --- RENDERIZADO DE RESULTADOS ---
if 'resultados' in st.session_state and st.session_state['resultados']:
    res_finales = st.session_state['resultados']
    for r in res_finales:
        with st.container():
            st.markdown(f"""
                <div class="ticker-card">
                    <div style="display: flex; justify-content: space-between; align-items: start;">
                        <div>
                            <p class="price-text">{r['Ticker']} <span class="type-label">({r['Tipo']})</span> — ${r['Precio']}</p>
                        </div>
                        <span class="profit-tag">+{r['GananciaPct']}% Neto</span>
                    </div>
                    <div class="data-row">
                        <span>📈 GAP: +{r['Gap']}%</span>
                        <span class="sl-label">🛑 SL: ${r['SL']}</span>
                        <span class="exit-label">🚀 EXIT: ${r['TP']}</span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
            st.line_chart(r['Chart'], height=200, color=["#1A73E8", "#D93025"])

    if st.button("📲 ENVIAR ALERTAS A WHATSAPP"):
        ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
        msg = f"🇺🇸 *OPORTUNIDADES USA (2:1)*\n_{ahora.strftime('%d/%m %H:%M')}_\n━━━━━━━━━━━━━━━━━━\n"
        for r in res_finales:
            msg += f"🚀 *{r['Ticker']} ({r['Tipo']})* | ${r['Precio']}\n"
            msg += f"   • SL: ${r['SL']} | EXIT: ${r['TP']} (+{r['GananciaPct']}%)\n\n"
        
        try:
            greenAPI = API.GreenApi(id_ins, token_ins)
            greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
            st.success("✅ Alertas enviadas correctamente.")
        except Exception as e:
            st.error(f"❌ Error API: {e}")
