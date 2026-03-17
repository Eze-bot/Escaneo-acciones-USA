import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Trading Momentum", layout="wide", page_icon="📈")

# Estilos CSS para mejorar la visualización
st.markdown("""
    <style>
    .metric-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 2px 2px 10px rgba(0,0,0,0.05);
    }
    .sentiment-pos { color: #28a745; font-weight: bold; }
    .sentiment-neg { color: #dc3545; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE SENTIMIENTO (CÓDIGO 2) ---
def get_real_sentiment(ticker_obj):
    try:
        news = ticker_obj.news
        if not news: return 0
        pos = ['growth', 'buy', 'upgrade', 'beat', 'ai', 'dividend', 'success', 'bullish', 'profit']
        neg = ['drop', 'sell', 'downgrade', 'miss', 'risk', 'lawsuit', 'loss', 'bearish']
        score = 0
        for n in news[:5]:
            text = n['title'].lower()
            score += sum(1 for w in pos if w in text)
            score -= sum(1 for w in neg if w in text)
        return score
    except: return 0

# --- PROCESAMIENTO TÉCNICO ---
def analizar_activo(ticker_raw):
    try:
        ticker = str(ticker_raw).split('.')[0].strip().upper()
        stock = yf.Ticker(ticker)
        # Traemos historial para indicadores (Código 2 utiliza SMA200)
        df = stock.history(period="1y")
        
        if len(df) < 200: return None

        # Indicadores Técnicos
        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        # Filtros de Dashboard (Sidebar)
        if not (p_min <= precio_act <= p_max) or gap < gap_min:
            return None

        # Medias Móviles y RSI
        ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
        ema50 = df['Close'].ewm(span=50).mean().iloc[-1]
        sma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rsi = (100 - (100 / (1 + (gain / loss)))).iloc[-1]

        # ATR para Riesgo
        high_low = df['High'] - df['Low']
        atr = high_low.rolling(14).mean().iloc[-1]
        
        sentimiento = get_real_sentiment(stock)

        # Score de Confianza (Fusionado)
        score = 0
        if precio_act > sma200: score += 30
        if ema20 > ema50: score += 20
        if 40 < rsi < 65: score += 20
        if sentimiento > 0: score += 20
        if gap > 3: score += 10

        # Gestión de Riesgo (ATR)
        distancia_sl = 2.5 * atr
        return {
            "Ticker": ticker,
            "Precio": round(precio_act, 2),
            "Gap %": round(gap, 2),
            "Confianza": int(score),
            "RSI": round(rsi, 1),
            "News": "POS" if sentimiento > 0 else ("NEG" if sentimiento < 0 else "NEU"),
            "SL": round(precio_act - distancia_sl, 2),
            "TP": round(precio_act + (distancia_sl * 2.2), 2),
            "Hist": df['Close'].tail(30)
        }
    except: return None

# --- INTERFAZ SIDEBAR ---
with st.sidebar:
    st.header("🔍 Filtros de Escaneo")
    p_min = st.number_input("Precio Mín ($)", 0.0, 1000.0, 1.0)
    p_max = st.number_input("Precio Máx ($)", 0.0, 3000.0, 100.0)
    gap_min = st.slider("GAP Mínimo (%)", 0.0, 15.0, 2.0)
    st.divider()
    st.header("📲 WhatsApp Config")
    id_ins = st.text_input("ID Instancia", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp", "5492664300161")

# --- CUERPO PRINCIPAL ---
st.title("📊 AI Trading Dashboard")
st.write("Escaneo en tiempo real: Momentum + Tendencia + Sentimiento")

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

if st.button("🚀 INICIAR ANÁLISIS"):
    if os.path.exists(RUTA_CSV):
        tickers_lista = pd.read_csv(RUTA_CSV)['Ticker'].tolist()
        
        with st.spinner("Analizando activos y noticias..."):
            with ThreadPoolExecutor(max_workers=10) as executor:
                resultados = [r for r in list(executor.map(analizar_activo, tickers_lista)) if r is not None]
            
            if resultados:
                # Ordenar por Score de Confianza
                top_final = sorted(resultados, key=lambda x: x['Confianza'], reverse=True)[:6]
                
                cols = st.columns(2)
                for i, res in enumerate(top_final):
                    with cols[i % 2]:
                        sent_class = "sentiment-pos" if res['News'] == "POS" else "sentiment-neg"
                        st.markdown(f"""
                        <div class="metric-card">
                            <h3>{res['Ticker']} - ${res['Precio']}</h3>
                            <p><b>GAP:</b> {res['Gap %']}% | <b>Confianza:</b> {res['Confianza']}/100</p>
                            <p><b>Noticias:</b> <span class="{sent_class}">{res['News']}</span> | <b>RSI:</b> {res['RSI']}</p>
                            <p style="color:red"><b>SL: ${res['SL']}</b></p>
                        </div>
                        """, unsafe_allow_html=True)
                        st.line_chart(res['Hist'], height=150)

                # --- ENVÍO DE WHATSAPP ---
                ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
                msg = f"🎯 *OPORTUNIDADES DE LA JORNADA*\n_{ahora.strftime('%d/%m %H:%M')}_\n━━━━━━━━━━━━━━━━━━\n"
                for r in top_final:
                    emoji = "🚀" if r['Confianza'] > 75 else "📈"
                    msg += f"{emoji} *{r['Ticker']}* | ${r['Precio']} | Gap: +{r['Gap %']}%\n"
                    msg += f"   - Confianza: {r['Confianza']}/100 | News: {r['News']}\n"
                    msg += f"   - SL: ${r['SL']} | TP: ${r['TP']}\n\n"
                
                try:
                    greenAPI = API.GreenApi(id_ins, token_ins)
                    greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
                    st.success("📱 Alertas enviadas a WhatsApp.")
                except: st.error("Error al conectar con Green API.")
            else:
                st.warning("No se encontraron activos que cumplan los filtros.")
    else:
        st.error(f"No se encontró el archivo {RUTA_CSV}")
