import yfinance as yf
import pandas as pd

ACTIVOS_USA = [
    "AAPL", "NVDA", "TSLA", "MSFT", "AMD", "AMZN", "GOOGL", "META", 
    "AVGO", "ORCL", "NFLX", "CRM", "ADBE", "INTC", "MU",           
    "UNH", "LLY", "JPM", "V", "MA", "WMT", "COST", "PG",          
    "XOM", "CVX", "TSM", "ASML", "BRK-B", "BA", "DIS"              
]

def get_real_sentiment(ticker):
    try:
        t = yf.Ticker(ticker)
        news = t.news
        if not news: return 0
        pos = ['growth', 'buy', 'upgrade', 'beat', 'ai', 'dividend', 'success', 'bullish']
        neg = ['drop', 'sell', 'downgrade', 'miss', 'risk', 'lawsuit', 'loss', 'bearish']
        score = 0
        for n in news[:5]:
            text = n['title'].lower()
            score += sum(1 for w in pos if w in text)
            score -= sum(1 for w in neg if w in text)
        return score
    except: return 0

def scan_bullmarket_extended():
    results = []
    print(f"--- Iniciando Escaneo de {len(ACTIVOS_USA)} Activos USA ---")

    for ticker in ACTIVOS_USA:
        try:
            # Descarga de datos
            data = yf.download(ticker, period="1y", interval="1d", progress=False)
            
            # Validación de datos suficientes (necesitamos al menos 200 para SMA200)
            if data is None or data.empty or len(data) < 200:
                continue

            # --- INDICADORES ---
            data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
            data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()
            data['SMA200'] = data['Close'].rolling(window=200).mean()
            
            delta = data['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            data['RSI'] = 100 - (100 / (1 + (gain / loss)))

            high_low = data['High'] - data['Low']
            high_close = abs(data['High'] - data['Close'].shift())
            low_close = abs(data['Low'] - data['Close'].shift())
            ranges = pd.concat([high_low, high_close, low_close], axis=1)
            data['ATR'] = ranges.max(axis=1).rolling(14).mean()

            last = data.iloc[-1]
            precio_act = float(last['Close'])
            sentimiento = get_real_sentiment(ticker)
            
            # --- SCORE DE CONFIANZA ---
            score = 0
            if precio_act > last['SMA200']: score += 30
            if last['EMA20'] > last['EMA50']: score += 25
            if 40 < last['RSI'] < 65: score += 25
            if sentimiento > 0: score += 20
            
            # --- GESTIÓN DE RIESGO ---
            distancia_sl = 2.5 * float(last['ATR'])
            stop_loss = precio_act - distancia_sl
            take_profit = precio_act + (distancia_sl * 2.2)
            
            results.append({
                "Ticker": ticker,
                "Precio": f"${precio_act:.2f}",
                "Confianza": int(score),
                "SL": f"${stop_loss:.2f}",
                "TP": f"${take_profit:.2f}",
                "Plazo": "7-14 días" if score > 75 else "2-5 días",
                "News": "POS" if sentimiento > 0 else ("NEG" if sentimiento < 0 else "NEU")
            })
        except Exception as e:
            print(f"Error analizando {ticker}: {e}")
            continue

    # --- VALIDACIÓN CRÍTICA ---
    if not results:
        return pd.DataFrame(columns=["Ticker", "Precio", "Confianza", "SL", "TP", "Plazo", "News"])

    df = pd.DataFrame(results)
    # Filtramos y ordenamos solo si hay datos
    df = df[df['Confianza'] >= 40].sort_values(by="Confianza", ascending=False)
    
    return df

# Ejecución
reporte = scan_bullmarket_extended()

if reporte.empty:
    print("\nNo se encontraron oportunidades que cumplan los criterios mínimos hoy.")
else:
    print("\n" + "="*95)
    print(f" RESULTADOS: {len(reporte)} OPORTUNIDADES DETECTADAS ")
    print("="*95)
    print(reporte.to_string(index=False))
    print("="*95)
