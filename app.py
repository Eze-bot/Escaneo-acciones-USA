def analizar_activo(ticker_raw, p_min, p_max, gap_min):
    try:
        ticker = str(ticker_raw).strip().upper()
        stock = yf.Ticker(ticker)
        # Usamos period="1y" pero aseguramos que traiga datos actuales
        df = stock.history(period="1y")
        
        if df is None or len(df) < 200: 
            return None

        # Obtenemos precio actual y cierre previo de forma segura
        precio_act = df['Close'].iloc[-1]
        cierre_ayer = df['Close'].iloc[-2]
        
        # Calculamos el GAP
        gap = ((precio_act - cierre_ayer) / cierre_ayer) * 100
        
        # --- EL FILTRO CRÍTICO ---
        # Si gap_min es muy alto (ej 2.0) y la acción subió 1.8, queda fuera.
        if not (p_min <= precio_act <= p_max) or gap < gap_min:
            return None

        # Indicadores Técnicos
        ema20 = df['Close'].ewm(span=20).mean()
        sma200 = df['Close'].rolling(window=200).mean()
        
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        
        # Evitar división por cero en RSI
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        high_low = df['High'] - df['Low']
        atr = high_low.rolling(14).mean().iloc[-1]
        
        sentimiento_total = get_yahoo_sentiment(stock) + get_ts2_sentiment(ticker)

        # Scoring
        score = 0
        if precio_act > sma200.iloc[-1]: score += 30
        if ema20.iloc[-1] > df['Close'].iloc[-20]: score += 20
        if 40 < df['RSI'].iloc[-1] < 70: score += 20
        if sentimiento_total > 0: score += 20
        if gap >= 2.0: score += 10 # Bajamos el umbral del bono por GAP

        # Preparación de gráfico
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
    except Exception as e:
        return None
