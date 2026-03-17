import yfinance as yf
import pandas as pd

# Listado Ampliado: "ACTIVOS BULLMARKET USA" (Top 30 Market Caps & Growth)
ACTIVOS_USA = [
    "AAPL", "NVDA", "TSLA", "MSFT", "AMD", "AMZN", "GOOGL", "META", # Big Tech
    "AVGO", "ORCL", "NFLX", "CRM", "ADBE", "INTC", "MU",           # Software/Semis
    "UNH", "LLY", "JPM", "V", "MA", "WMT", "COST", "PG",          # Finanzas/Consumo/Salud
    "XOM", "CVX", "TSM", "ASML", "BRK-B", "BA", "DIS"              # Energía/Industria/Global
]

def get_real_sentiment(ticker):
    try:
        t = yf.Ticker(ticker)
        news = t.news
        if not news: return 0
        pos = ['growth', 'buy', 'upgrade', 'beat', 'ai', 'dividend', 'success', 'partnership', 'bullish']
        neg = ['drop', 'sell', 'downgrade', 'miss', 'risk', 'lawsuit', 'loss', 'bearish']
        score = 0
        for n in news[:5]: # Reducido a 5 para velocidad en listas largas
            text = n['title'].lower()
            score += sum(1 for w in pos if w in text)
            score -= sum(1 for w in neg if w in text)
        return score
    except: return 0

def scan_bullmarket_extended():
    results = []
    total = len(ACTIVOS_USA)
    print(f"--- Iniciando Escaneo de {total} Activos USA ---")

    for i, ticker in enumerate(ACTIVOS_USA):
        # Feedback visual del progreso
        if (i+1) % 5 == 0: print(f"Procesando: {i+1}/{total}...")
        
        try:
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            if data.empty or len(data) < 200: continue

            # --- INDICADORES ---
            data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
            data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
            data['SMA200'] = data['Close'].rolling(window=200).mean()
            
            # RSI
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            data['RSI'] = 100 - (100 / (1 + (gain / loss)))

            # ATR (Volatilidad)
            high_low = data['High'] - data['Low']
            high_close = abs(data['High'] - data['Close'].shift())
            low_close = abs(data['Low'] - data['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            data['ATR'] = ranges.max(axis=1).rolling(14).mean()

            last = data.iloc[-1]
            precio_act = last['Close']
            sentimiento = get_real_sentiment(ticker)
            
            # --- SCORE DE CONFIANZA ---
            score = 0
            if precio_act > last['SMA200']: score += 30      # Tendencia Largo Plazo
            if last['EMA20'] > last['EMA50']: score += 25     # Tendencia Corto Plazo
            if 40 < last['RSI'] < 65: score += 25             # Fuerza sin agotamiento
            if sentimiento > 0: score += 20                   # Noticias positivas
            
            # --- GESTIÓN DE RIESGO ---
            distancia_sl = 2.5 * last['ATR'] # SL un poco más holgado para el listado amplio
            stop_loss = precio_act - distancia_sl
            take_profit = precio_act + (distancia_sl * 2.2) # Ratio 1:2.2 mejorado
            
            plazo = "7-14 días" if score > 75 else "2-5 días"

            results.append({
                "Ticker": ticker,
                "Precio": f"${precio_act:.2f}",
                "Confianza": score,
                "SL": f"${stop_loss:.2f}",
                "TP": f"${take_profit:.2f}",
                "Plazo": plazo,
                "News": "POS" if sentimiento > 0 else ("NEG" if sentimiento < 0 else "NEU")
            })
        except Exception:
            continue

    # Filtrar solo los que tienen confianza mínima para no mostrar "ruido"
    df = pd.DataFrame(results)
    df = df[df['Confianza'] >= 50].sort_values(by="Confianza", ascending=False)
    
    return df

# Ejecución
reporte = scan_bullmarket_extended()
print("\n" + "="*95)
print(f" RESULTADOS: {len(reporte)} OPORTUNIDADES DETECTADAS ")
print("="*95)
print(reporte.to_string(index=False))
print("="*95)
