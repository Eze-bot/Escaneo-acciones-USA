import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime
import os

# Configuración de la página
st.set_page_config(page_title="Screener Bullmarket USA - CSV", layout="wide")

# --- CARGA DINÁMICA DEL ARCHIVO ESPECÍFICO ---
def cargar_activos_desde_archivo(nombre_csv="ACTIVOS_BULLMARKET_USA.csv"):
    if not os.path.exists(nombre_csv):
        st.error(f"❌ Error: No se encontró el archivo '{nombre_csv}' en la carpeta del proyecto.")
        return []
    try:
        df_csv = pd.read_csv(nombre_csv)
        # Normalizamos nombres de columnas para encontrar el Ticker
        df_csv.columns = [c.strip().upper() for c in df_csv.columns]
        
        posibles_cols = ['TICKER', 'SYMBOL', 'ACTIVO', 'SIMBOLO', 'ACCION']
        col_encontrada = next((c for c in posibles_cols if c in df_csv.columns), None)
        
        if col_encontrada:
            # Limpiamos los tickers (quitar espacios y pasar a mayúsculas)
            lista = df_csv[col_encontrada].dropna().astype(str).str.strip().str.upper().tolist()
            return sorted(list(set(lista))) # Eliminar duplicados y ordenar
        else:
            st.error(f"❌ El archivo debe tener una columna llamada 'Ticker' o 'Activo'. Columnas detectadas: {list(df_csv.columns)}")
            return []
    except Exception as e:
        st.error(f"❌ Error crítico al leer el CSV: {e}")
        return []

# --- MOTOR DE CÁLCULO ---
def fetch_and_analyze(ticker):
    try:
        # Descargamos 1 año para tener la SMA200 estable
        data = yf.download(ticker, period="1y", interval="1d", progress=False)
        if data.empty or len(data) < 200: return None
        
        # Indicadores Técnicos
        data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
        data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
        data['SMA200'] = data['Close'].rolling(window=200).mean()
        
        # RSI
        delta = data['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        data['RSI'] = 100 - (100 / (1 + (gain / loss)))

        # ATR (2.5 para un Stop Loss más profesional)
        high_low = data['High'] - data['Low']
        high_close = abs(data['High'] - data['Close'].shift())
        low_close = abs(data['Low'] - data['Close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        data['ATR'] = ranges.max(axis=1).rolling(14).mean()
        
        return data
    except: return None

def get_sentiment_score(ticker):
    try:
        tk = yf.Ticker(ticker)
        news = tk.news
        if not news: return 0
        score = 0
        palabras_pos = ['buy', 'growth', 'ai', 'beat', 'bullish', 'dividend', 'upgrade']
        palabras_neg = ['sell', 'risk', 'miss', 'bearish', 'drop', 'lawsuit', 'downgrade']
        for n in news[:5]:
            titulo = n['title'].lower()
            score += sum(1 for w in palabras_pos if w in titulo)
            score -= sum(1 for w in palabras_neg if w in titulo)
        return score
    except: return 0

# --- INTERFAZ ---
st.title("📈 Analizador de Activos - Bullmarket USA")
st.markdown("---")

activos = cargar_activos_desde_archivo()

if activos:
    st.sidebar.success(f"📂 {len(activos)} activos cargados desde el CSV.")
    
    if st.button("🚀 Iniciar Escaneo de Mercado"):
        results = []
        bar = st.progress(0)
        
        for idx, ticker in enumerate(activos):
            bar.progress((idx + 1) / len(activos))
            df_hist = fetch_and_analyze(ticker)
            
            if df_hist is not None:
                last = df_hist.iloc[-1]
                precio = float(last['Close'])
                sentimiento = get_sentiment_score(ticker)
                
                # Sistema de Puntos (Confianza)
                score = 0
                if precio > last['SMA200']: score += 30
                if last['EMA20'] > last['EMA50']: score += 25
                if 42 < last['RSI'] < 68: score += 25 # Ajuste de rango RSI
                if sentimiento > 0: score += 20
                
                # Riesgo/Beneficio
                riesgo = 2.5 * float(last['ATR'])
                sl = precio - riesgo
                tp = precio + (riesgo * 2.1) # Ratio ligeramente superior a 2
                
                results.append({
                    "Ticker": ticker,
                    "Precio": precio,
                    "Confianza": int(score),
                    "Stop Loss": sl,
                    "Take Profit": tp,
                    "Tendencia": "ALCISTA" if precio > last['SMA200'] else "BAJISTA",
                    "News": "POS" if sentimiento > 0 else ("NEG" if sentimiento < 0 else "NEU"),
                    "FullData": df_hist
                })

        if results:
            df_final = pd.DataFrame(results).drop(columns=['FullData'])
            # Filtro de seguridad para solo mostrar lo que vale la pena
            df_final = df_final[df_final['Confianza'] >= 45].sort_values(by="Confianza", ascending=False)
            
            st.subheader("📋 Ranking de Oportunidades")
            st.dataframe(df_final.style.format({
                "Precio": "${:.2f}", "Stop Loss": "${:.2f}", "Take Profit": "${:.2f}", "Confianza": "{}%"
            }), use_container_width=True)
            
            st.divider()
            
            # Gráficos de las mejores señales
            tops = [r for r in results if r['Confianza'] >= 75]
            if tops:
                st.subheader("🔥 Análisis Detallado (Top Picks)")
                for item in tops:
                    ticker = item['Ticker']
                    df_p = item['FullData'].tail(60)
                    
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(x=df_p.index, open=df_p['Open'], high=df_p['High'], 
                                                low=df_p['Low'], close=df_p['Close'], name=ticker))
                    fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA20'], name="EMA 20", line=dict(width=1.5)))
                    fig.add_trace(go.Scatter(x=df_p.index, y=df_p['EMA50'], name="EMA 50", line=dict(width=1.5)))
                    
                    fig.update_layout(title=f"{ticker} - Confianza: {item['Confianza']}%", 
                                      xaxis_rangeslider_visible=False, height=400)
                    
                    # ID único para evitar el error anterior
                    st.plotly_chart(fig, use_container_width=True, key=f"graph_{ticker}")
            else:
                st.info("No hay activos con confianza extrema (>75%), pero puedes ver el ranking arriba.")
        else:
            st.warning("El escaneo terminó pero no hay señales claras hoy.")
