import streamlit as st
import yfinance as yf
import pandas as pd
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os
import requests
from bs4 import BeautifulSoup

# --- CONFIGURACIÓN DE PÁGINA ---
st.set_page_config(page_title="AI Trading Pro", layout="wide", page_icon="📈")

# --- ESTILOS CSS REFORZADOS ---
st.markdown("""
    <style>
    .ticker-card {
        background-color: #FFFFFF !important; 
        border-radius: 12px;
        padding: 20px;
        border-left: 8px solid #007bff;
        margin-bottom: 25px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.2);
    }
    .ticker-card h3 {
        color: #121212 !important;
        margin-top: 0;
        margin-bottom: 12px;
        font-size: 1.5rem;
        font-weight: bold;
    }
    .ticker-card p {
        color: #333333 !important;
        font-size: 1.05rem;
        margin: 6px 0;
        line-height: 1.2;
    }
    .label-data {
        font-weight: bold;
        color: #000000 !important;
    }
    .sl-text {
        color: #D32F2F !important;
        font-weight: bold;
        font-size: 1.15rem;
        margin-top: 12px !important;
        border-top: 1px solid #eee;
        padding-top: 8px;
    }
    </style>
    """, unsafe_allow_html=True)

# --- LÓGICA DE SENTIMIENTO TS2 TECH ---
def get_ts2_sentiment(ticker):
    try:
        url = "https://ts2.tech/en/category/stock-market/"
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=5)
        soup = BeautifulSoup(response.text, 'html.parser')
        headlines = soup.find_all(['h2', 'h3'])
        ts2_score = 0
        pos_keywords = ['surge', 'bullish', 'buy', 'growth', 'ai', 'record', 'profit', 'up']
        neg_keywords = ['fall', 'bearish', 'sell', 'risk', 'loss', 'drop', 'crash', 'down']
        count = 0
        ticker_clean = str(ticker).split('.')[0].lower()
        for h in headlines:
            text = h.get_text().lower()
            if ticker_clean in text:
                count += 1
                ts2_score += sum(1 for w in pos_keywords if w in text)
                ts2_score -= sum(1 for w in neg_keywords if w in text)
        return ts2_score if count > 0 else 0
    except:
        return 0

# --- LÓGICA DE SENTIMIENTO YAHOO ---
def get_yahoo_sentiment(ticker_obj):
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

# --- MOTOR DE ANÁLISIS ---
def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        ticker = str(ticker_raw).strip().upper()
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y")
        
        if df is None or len(df) < 200: 
            return None

        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        # Filtro de precio y gap
        if not (p_min <= precio_act <= p_max) or gap < gap_min:
            return None

        # Indicadores
        ema20 = df['Close'].ewm(span=20).mean()
        sma200 = df['Close'].rolling(window=200).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        high_low = df['High'] - df['Low']
        atr = high_low.rolling(14).mean().iloc[-1]
        
        sentimiento_total = get_yahoo_sentiment(stock) + get_ts2_sentiment(ticker)

        # Scoring de confianza
        score = 0
        if precio_act > sma200.iloc[-1]: score += 30
        if ema20.iloc[-1] > df['Close'].iloc[-20]: score += 20
        if 40 < df['RSI'].iloc[-1] < 70: score += 20
        if sentimiento_total > 0: score += 20
        if gap >= 2.0: score += 10

        # Gráfico
        last_30 = df.tail(30).copy()
        p_min_30, p_max_30 = last_30['Close'].min(), last_30['Close'].max()
        last_30['RSI_Visual'] = ((last_30['RSI'] - 0) / (100 - 0)) * (p_max_30 - p_min_30) + p_min_30
        chart_df = last_30[['Close', 'RSI_Visual']].copy()
        chart_df.columns = ['Precio', 'RSI (Norm)']

        tipo = "CEDEAR" if ticker.endswith(".BA") else "USA"

        return {
            "Ticker": ticker,
            "Precio": round(precio_act, 2),
            "Gap %": round(gap, 2),
            "Confianza": int(score),
            "RSI": round(df['RSI'].iloc[-1], 1),
            "News": "🚀 POS" if sentimiento_total > 0 else ("🔴 NEG" if sentimiento_total < 0 else "⚪ NEU"),
            "SL": round(precio_act - (2.5 * atr), 2),
            "TP": round(precio_act + (atr * 5), 2),
            "ChartData": chart_df,
            "Tipo": tipo
        }
    except:
        return None

# --- SIDEBAR ---
with st.sidebar:
    st.header("🌍 Selección de Mercado")
    opcion_mercado = st.selectbox("Analizar actualmente:", ["Acciones USA (Directas)", "CEDEARs (Argentina)"])
    
    st.header("⚙️ Configuración")
    p_min_in = st.number_input("Precio Mín", 0.0, 3000000.0, 0.0)
    p_max_in = st.number_input("Precio Máx", 0.0, 3000000.0, 1000000.0)
    gap_min_in = st.slider("GAP Mínimo (%)", -5.0, 20.0, 0.0)
    
    st.divider()
    id_ins = st.text_input("ID Green API", "7103533853")
    token_ins = st.text_input("Token API", "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5", type="password")
    celular = st.text_input("WhatsApp destino", "5492664300161")

# --- PANEL PRINCIPAL ---
st.title(f"🚀 Escáner: {opcion_mercado}")

RUTA_CSV = "ACTIVOS_BULLMARKET_USA.csv"

if st.button("🔍 INICIAR ANÁLISIS"):
    if os.path.exists(RUTA_CSV):
        df_csv = pd.read_csv(RUTA_CSV)
        todos_los_tickers = df_csv['Ticker'].tolist()
        
        if opcion_mercado == "CEDEARs (Argentina)":
            tickers_filtrados = [t for t in todos_los_tickers if str(t).upper().endswith('.BA')]
        else:
            tickers_filtrados = [t for t in todos_los_tickers if not str(t).upper().endswith('.BA')]

        if not tickers_filtrados:
            st.warning("No hay tickers de este tipo en el CSV.")
        else:
            with st.spinner("Analizando..."):
                with ThreadPoolExecutor(max_workers=10) as ex:
                    resultados = [r for r in list(ex.map(lambda x: analizar_activo(x, p_min_in, p_max_in, gap_min_in), tickers_filtrados)) if r is not None]
                
                if resultados:
                    st.session_state['resultados'] = sorted(resultados, key=lambda x: x['Confianza'], reverse=True)[:6]
                    st.session_state['mercado_actual'] = opcion_mercado
                else:
                    st.session_state['resultados'] = []
                    st.info("Ningún activo superó los filtros.")
    else:
        st.error(f"No se encontró el archivo {RUTA_CSV}")

# --- MOSTRAR RESULTADOS ---
if 'resultados' in st.session_state and st.session_state['resultados']:
    res_finales = st.session_state['resultados']
    cols = st.columns(2)
    for i, res in enumerate(res_finales):
        with cols[i % 2]:
            st.markdown(f"""
                <div class="ticker-card">
                    <h3>{res['Ticker']} — ${res['Precio']}</h3>
                    <p>🎯 Confianza: <span class="label-data">{res['Confianza']}/100</span></p>
                    <p>📈 GAP: <span class="label-data">+{res['Gap %']}%</span></p>
                    <p>🎭 Sentimiento: <span class="label-data">{res['News']}</span></p>
                    <p>⚡ RSI: <span class="label-data">{res['RSI']}</span></p>
                    <p class="sl-text">🛑 SL Sugerido: ${res['SL']}</p>
                </div>
            """, unsafe_allow_html=True)
            st.line_chart(res['ChartData'], color=["#007bff", "#ff4b4b"])

    st.divider()
    if st.button("📲 ENVIAR ALERTAS A WHATSAPP"):
        ahora = datetime.datetime.now(pytz.timezone('America/Argentina/Buenos_Aires'))
        mercado_tag = st.session_state.get('mercado_actual', 'MERCADO')
        msg = f"🎯 *OPORTUNIDADES {mercado_tag.upper()}*\n_{ahora.strftime('%d/%m %H:%M')}_\n━━━━━━━━━━━━━━━━━━\n"
        for r in res_finales:
            msg += f"🚀 *{r['Ticker']}* ({r['Tipo']}) | ${r['Precio']} | +{r['Gap %']}%\n"
            msg += f"   - Confianza: {r['Confianza']}/100 | News: {r['News']}\n"
            msg += f"   - SL: ${r['SL']} | TP: ${r['TP']}\n\n"
        try:
            greenAPI = API.GreenApi(id_ins, token_ins)
            greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
            st.success("✅ Mensaje enviado.")
        except Exception as e:
            st.error(f"Error: {e}")
