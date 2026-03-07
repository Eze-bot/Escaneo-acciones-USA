import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from whatsapp_api_client_python import API
from concurrent.futures import ThreadPoolExecutor
import datetime
import pytz
import os
import altair as alt
import time

# ─────────────────────────────────────────────────────────────
# 1. CONFIGURACIÓN DE PÁGINA
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Scanner Momentum USA",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ─────────────────────────────────────────────────────────────
# 2. ESTILOS CSS
# ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'DM Sans', sans-serif;
}

/* ── Fondo general ── */
.stApp {
    background: #0d1117;
    color: #e6edf3;
}

/* ── Título principal ── */
h1 {
    font-family: 'Space Mono', monospace !important;
    letter-spacing: -1px;
}

/* ── Tarjeta principal ── */
.ticker-card {
    background: linear-gradient(145deg, #161b22 0%, #1a2030 100%);
    border: 1px solid #30363d;
    border-radius: 12px;
    padding: 18px 20px 12px 20px;
    margin-bottom: 6px;
    position: relative;
    overflow: hidden;
    transition: border-color 0.2s;
}
.ticker-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
    background: var(--accent, #2196F3);
}
.ticker-card:hover {
    border-color: #58a6ff;
}

/* ── Encabezado de tarjeta ── */
.card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;
}
.ticker-symbol {
    font-family: 'Space Mono', monospace;
    font-size: 1.25rem;
    font-weight: 700;
    color: #58a6ff;
    letter-spacing: 1px;
}
.ticker-type-badge {
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 20px;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}
.badge-accion {
    background: rgba(33,150,243,0.15);
    color: #58a6ff;
    border: 1px solid rgba(33,150,243,0.3);
}
.badge-etf {
    background: rgba(139,92,246,0.15);
    color: #c084fc;
    border: 1px solid rgba(139,92,246,0.3);
}

/* ── Precio y GAP ── */
.price-row {
    display: flex;
    align-items: baseline;
    gap: 10px;
    margin-bottom: 10px;
}
.ticker-price {
    font-family: 'Space Mono', monospace;
    font-size: 1.6rem;
    font-weight: 700;
    color: #e6edf3;
    line-height: 1;
}
.gap-positive { color: #3fb950; font-weight: 700; font-size: 1rem; }
.gap-negative { color: #f85149; font-weight: 700; font-size: 1rem; }

/* ── Grilla de métricas ── */
.metrics-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 6px;
    margin-bottom: 10px;
}
.metric-box {
    background: rgba(255,255,255,0.04);
    border-radius: 7px;
    padding: 6px 8px;
    text-align: center;
}
.metric-label {
    font-size: 0.60rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-bottom: 2px;
}
.metric-value {
    font-family: 'Space Mono', monospace;
    font-size: 0.82rem;
    font-weight: 700;
    color: #e6edf3;
}
.metric-value.positive { color: #3fb950; }
.metric-value.negative { color: #f85149; }
.metric-value.warning  { color: #d29922; }
.metric-value.neutral  { color: #8b949e; }

/* ── Barra de señales ── */
.signals-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
}
.signal-bar-bg {
    flex: 1;
    height: 5px;
    background: #21262d;
    border-radius: 3px;
    overflow: hidden;
}
.signal-bar-fill {
    height: 100%;
    border-radius: 3px;
    background: var(--bar-color, #3fb950);
    transition: width 0.5s ease;
}
.signal-score-text {
    font-family: 'Space Mono', monospace;
    font-size: 0.70rem;
    color: #8b949e;
    white-space: nowrap;
}

/* ── Etiquetas de señales ── */
.signal-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-top: 4px;
}
.signal-tag {
    font-size: 0.60rem;
    padding: 2px 6px;
    border-radius: 4px;
    font-weight: 600;
    letter-spacing: 0.3px;
}
.tag-buy  { background: rgba(63,185,80,0.12); color: #3fb950; border: 1px solid rgba(63,185,80,0.25); }
.tag-sell { background: rgba(248,81,73,0.12); color: #f85149; border: 1px solid rgba(248,81,73,0.25); }
.tag-warn { background: rgba(210,153,34,0.12); color: #d29922; border: 1px solid rgba(210,153,34,0.25); }

/* ── Rango del día ── */
.range-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-top: 6px;
}
.range-label { font-size: 0.62rem; color: #8b949e; white-space: nowrap; }
.range-bar-bg {
    flex: 1;
    height: 4px;
    background: #21262d;
    border-radius: 2px;
    position: relative;
}
.range-bar-fill {
    position: absolute;
    height: 100%;
    background: linear-gradient(90deg, #f85149, #d29922, #3fb950);
    border-radius: 2px;
    left: var(--range-left, 0%);
    width: var(--range-width, 100%);
}
.range-dot {
    position: absolute;
    width: 8px; height: 8px;
    background: #fff;
    border-radius: 50%;
    top: -2px;
    left: var(--dot-pos, 50%);
    transform: translateX(-50%);
    box-shadow: 0 0 4px rgba(255,255,255,0.5);
}

/* ── Pre-mercado badge ── */
.premarket-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 0.65rem;
    font-weight: 700;
    padding: 2px 8px;
    border-radius: 4px;
    margin-left: 6px;
}
.pm-up   { background: rgba(63,185,80,0.15); color: #3fb950; border: 1px solid rgba(63,185,80,0.3); }
.pm-down { background: rgba(248,81,73,0.15); color: #f85149; border: 1px solid rgba(248,81,73,0.3); }
.pm-flat { background: rgba(139,148,158,0.15); color: #8b949e; border: 1px solid rgba(139,148,158,0.3); }

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: #161b22;
    border-right: 1px solid #30363d;
}
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 {
    font-family: 'Space Mono', monospace;
    font-size: 0.85rem;
    color: #8b949e;
    letter-spacing: 1px;
    text-transform: uppercase;
}

/* ── Botones ── */
.stButton > button {
    font-family: 'Space Mono', monospace !important;
    font-weight: 700 !important;
    letter-spacing: 1px !important;
    border-radius: 8px !important;
    transition: all 0.2s !important;
}

/* ── Stats bar ── */
.stats-bar {
    display: flex;
    gap: 20px;
    padding: 12px 0;
    margin-bottom: 16px;
}
.stat-item {
    display: flex;
    flex-direction: column;
}
.stat-value {
    font-family: 'Space Mono', monospace;
    font-size: 1.4rem;
    font-weight: 700;
    color: #e6edf3;
    line-height: 1;
}
.stat-label {
    font-size: 0.68rem;
    color: #8b949e;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    margin-top: 2px;
}

/* ── Info box ── */
.info-box {
    background: rgba(33,150,243,0.08);
    border: 1px solid rgba(33,150,243,0.2);
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 0.80rem;
    color: #8b949e;
    margin-bottom: 12px;
}

/* ── Timestamp ── */
.timestamp {
    font-family: 'Space Mono', monospace;
    font-size: 0.68rem;
    color: #484f58;
    text-align: right;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 3. CONSTANTES Y CONFIG
# ─────────────────────────────────────────────────────────────
RUTA_CSV      = "ACTIVOS_BULLMARKET_USA.csv"
ZONA_ARG      = pytz.timezone('America/Argentina/Buenos_Aires')
ZONA_NY       = pytz.timezone('America/New_York')
MAX_WORKERS   = 6       # seguro para Yahoo Finance
CACHE_MINUTOS = 10      # tiempo de caché de datos
MAX_RESULTS   = 7       # máximo de tarjetas a mostrar

# ─────────────────────────────────────────────────────────────
# 4. HELPERS — indicadores técnicos manuales (sin pandas-ta)
# ─────────────────────────────────────────────────────────────
def calc_rsi(series, period=14):
    delta  = series.diff()
    gain   = delta.clip(lower=0).rolling(period).mean()
    loss   = (-delta.clip(upper=0)).rolling(period).mean()
    rs     = gain / loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))

def calc_ema(series, span):
    return series.ewm(span=span, adjust=False).mean()

def calc_bollinger(series, period=20, std=2):
    ma    = series.rolling(period).mean()
    sigma = series.rolling(period).std()
    return ma - std * sigma, ma, ma + std * sigma

def calc_atr(df, period=14):
    h, l, c = df['High'], df['Low'], df['Close']
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    return tr.rolling(period).mean()

def calc_vwap(df):
    """VWAP diario (usa solo la sesión más reciente disponible)"""
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    return (typical * df['Volume']).cumsum() / df['Volume'].cumsum()

# ─────────────────────────────────────────────────────────────
# 5. FUNCIÓN PRINCIPAL DE ANÁLISIS
# ─────────────────────────────────────────────────────────────
def limpiar_ticker(ticker_raw):
    """Limpia el ticker eliminando caracteres inválidos que vienen del CSV"""
    t = str(ticker_raw).strip()
    t = t.replace('$', '')      # quitar signo $ (ej: $BF → BF)
    t = t.replace(' ', '')      # quitar espacios internos
    t = t.split('.')[0]         # quitar sufijos como .B en BRK.B
    t = t.split('/')[0]         # quitar sufijos como /B en BRK/B
    t = t.upper()
    return t if len(t) >= 1 else None

def obtener_datos(ticker_raw):
    try:
        ticker = limpiar_ticker(ticker_raw)
        if not ticker:
            return None
        stock  = yf.Ticker(ticker)

        # ── A) Datos diarios (1 mes) para indicadores de tendencia ──
        df_d = stock.history(period="1mo", interval="1d")
        if len(df_d) < 10:
            return None

        precio_actual = df_d['Close'].iloc[-1]

        # Filtro de precio
        if not (p_min <= precio_actual <= p_max):
            return None

        cierre_ayer   = df_d['Close'].iloc[-2]
        gap_dia       = round(((precio_actual - cierre_ayer) / cierre_ayer) * 100, 2)

        if gap_dia < gap_min:
            return None

        # ── B) Datos intradía con pre-mercado (5 días, 15 minutos) ──
        df_15 = stock.history(period="5d", interval="15m", prepost=True)

        # ── C) INDICADORES TÉCNICOS ──────────────────────────────

        # RSI (14) sobre datos diarios
        rsi_series = calc_rsi(df_d['Close'], 14)
        rsi_raw    = rsi_series.iloc[-1]
        rsi        = round(float(rsi_raw), 1) if pd.notna(rsi_raw) else None

        # EMAs sobre datos diarios
        ema9  = float(calc_ema(df_d['Close'], 9).iloc[-1])
        ema21 = float(calc_ema(df_d['Close'], 21).iloc[-1])
        ema50_raw = calc_ema(df_d['Close'], 50).iloc[-1]
        ema50 = float(ema50_raw) if pd.notna(ema50_raw) else None

        # Bollinger Bands (requiere >= 20 velas)
        bb_lower, bb_upper = None, None
        if len(df_d) >= 20:
            bb_low, _, bb_up = calc_bollinger(df_d['Close'])
            bl = bb_low.iloc[-1]; bu = bb_up.iloc[-1]
            bb_lower = float(bl) if pd.notna(bl) else None
            bb_upper = float(bu) if pd.notna(bu) else None

        # ATR (14) — volatilidad esperada
        atr_raw = calc_atr(df_d).iloc[-1]
        atr_pct = round((float(atr_raw) / precio_actual) * 100, 2) if pd.notna(atr_raw) and precio_actual > 0 else None

        # Volumen vs promedio (ventana adaptable según datos disponibles)
        vol_actual = float(df_d['Volume'].iloc[-1])
        vol_window = min(20, len(df_d) - 1)
        vol_avg    = float(df_d['Volume'].rolling(vol_window).mean().iloc[-1])
        vol_ratio  = round(vol_actual / vol_avg, 1) if pd.notna(vol_avg) and vol_avg > 0 else 1.0

        # VWAP (sobre datos de 15m)
        vwap_val = None
        if not df_15.empty and len(df_15) > 5:
            try:
                v = calc_vwap(df_15).iloc[-1]
                vwap_val = round(float(v), 4) if pd.notna(v) else None
            except Exception:
                vwap_val = None

        # Variación semanal (5 días)
        idx_5d     = min(5, len(df_d) - 1)
        precio_5d  = float(df_d['Close'].iloc[-(idx_5d + 1)])
        var_semana = round(((precio_actual - precio_5d) / precio_5d) * 100, 2) if precio_5d > 0 else 0.0

        # Rango del día
        min_dia = round(float(df_d['Low'].iloc[-1]),  4)
        max_dia = round(float(df_d['High'].iloc[-1]), 4)
        min_mes = round(float(df_d['Low'].min()),  4)
        max_mes = round(float(df_d['High'].max()), 4)

        # ── D) PRE-MERCADO REAL ───────────────────────────────────
        premarket_pct = None
        premarket_px  = None
        ahora_ny      = datetime.datetime.now(ZONA_NY)
        es_premarked  = 4 <= ahora_ny.hour < 9

        if not df_15.empty and es_premarked:
            try:
                hoy_str = ahora_ny.strftime('%Y-%m-%d')
                idx_ny  = df_15.index.tz_convert(ZONA_NY)
                mask    = (idx_ny.strftime('%Y-%m-%d') == hoy_str) & (idx_ny.hour < 9)
                df_pm   = df_15[mask]
                if not df_pm.empty:
                    premarket_px  = round(float(df_pm['Close'].iloc[-1]), 4)
                    premarket_pct = round(((premarket_px - cierre_ayer) / cierre_ayer) * 100, 2)
            except Exception:
                pass

        # ── E) SEÑALES TÉCNICAS ──────────────────────────────────
        señales_compra = []
        señales_venta  = []
        score          = 0

        # RSI
        if rsi is not None:
            if rsi < 35:
                señales_compra.append(f"RSI sob.vendido {rsi}")
                score += 1
            elif rsi > 65:
                señales_venta.append(f"RSI sob.comprado {rsi}")
                score -= 1

        # MACD aproximado (diferencia EMA9 - EMA21)
        if pd.notna(ema9) and pd.notna(ema21):
            diff_actual = ema9 - ema21
            ema9_prev   = calc_ema(df_d['Close'], 9).iloc[-2]
            ema21_prev  = calc_ema(df_d['Close'], 21).iloc[-2]
            diff_prev   = ema9_prev - ema21_prev
            if diff_actual > 0 and diff_prev <= 0:
                señales_compra.append("MACD cruce alcista ↑")
                score += 2
            elif diff_actual < 0 and diff_prev >= 0:
                señales_venta.append("MACD cruce bajista ↓")
                score -= 2

        # EMAs alineadas
        if pd.notna(ema9) and pd.notna(ema21):
            if ema50 is not None and pd.notna(ema50):
                if precio_actual > ema9 > ema21 > ema50:
                    señales_compra.append("EMAs alineadas alcistas")
                    score += 1
                elif precio_actual < ema9 < ema21 < ema50:
                    señales_venta.append("EMAs alineadas bajistas")
                    score -= 1
            else:
                if precio_actual > ema9 > ema21:
                    señales_compra.append("Precio > EMA9 > EMA21")
                    score += 1

        # Volumen elevado
        if vol_ratio >= 1.5 and gap_dia > 0:
            señales_compra.append(f"Vol. alto {vol_ratio}x promedio")
            score += 1
        elif vol_ratio >= 1.5 and gap_dia < 0:
            señales_venta.append(f"Vol. alto con caída {vol_ratio}x")
            score -= 1

        # Bollinger
        if pd.notna(bb_lower) and precio_actual <= bb_lower * 1.01:
            señales_compra.append("Precio en BB inferior")
            score += 1
        elif pd.notna(bb_upper) and precio_actual >= bb_upper * 0.99:
            señales_venta.append("Precio en BB superior")
            score -= 1

        # VWAP
        if vwap_val and precio_actual > vwap_val * 1.005:
            señales_compra.append(f"Precio > VWAP ({vwap_val:.3f})")
            score += 1
        elif vwap_val and precio_actual < vwap_val * 0.995:
            señales_venta.append(f"Precio < VWAP ({vwap_val:.3f})")
            score -= 1

        # Pre-mercado
        if premarket_pct is not None:
            if premarket_pct > 1.5:
                señales_compra.append(f"Pre-mkt sube {premarket_pct}% 🌅")
                score += 2
            elif premarket_pct < -1.5:
                señales_venta.append(f"Pre-mkt baja {premarket_pct}% 🌅")
                score -= 2

        total_señales = len(señales_compra) + len(señales_venta)

        # ── F) DATOS PARA EL GRÁFICO (15m, enriquecido) ──────────
        df_graf = df_d[['Close', 'Volume', 'High', 'Low']].copy().tail(22)
        df_graf = df_graf.reset_index()
        df_graf.columns = ['x', 'close', 'volume', 'high', 'low']
        df_graf['ema9']  = calc_ema(df_d['Close'], 9).tail(22).values
        df_graf['ema21'] = calc_ema(df_d['Close'], 21).tail(22).values

        # Tendencia de la EMA
        tendencia = "ALCISTA" if ema9 > ema21 else "BAJISTA"
        color_tendencia = "#3fb950" if tendencia == "ALCISTA" else "#f85149"

        # Tipo desde el CSV (se enriquece después)
        return {
            "Ticker"         : ticker,
            "Tipo"           : "—",
            "Precio"         : round(precio_actual, 4),
            "GAP"            : gap_dia,
            "VarSemana"      : var_semana,
            "RSI"            : rsi,
            "VolRatio"       : vol_ratio,
            "ATR_pct"        : atr_pct,
            "VWAP"           : vwap_val,
            "EMA9"           : round(ema9, 4),
            "EMA21"          : round(ema21, 4),
            "EMA50"          : round(ema50, 4) if ema50 is not None else None,
            "BBLower"        : round(bb_lower, 4) if bb_lower is not None else None,
            "BBUpper"        : round(bb_upper, 4) if bb_upper is not None else None,
            "PremarketPct"   : premarket_pct,
            "PremarketPx"    : premarket_px,
            "MinDia"         : min_dia,
            "MaxDia"         : max_dia,
            "MinMes"         : min_mes,
            "MaxMes"         : max_mes,
            "Tendencia"      : tendencia,
            "ColorTendencia" : color_tendencia,
            "SenalesCompra"  : señales_compra,
            "SenalesVenta"   : señales_venta,
            "Score"          : score,
            "TotalSenales"   : total_señales,
            "Data"           : df_graf,
        }

    except Exception as e:
        return None

# ─────────────────────────────────────────────────────────────
# 6. HELPERS DE RENDERIZADO
# ─────────────────────────────────────────────────────────────
def color_rsi(rsi):
    if rsi is None:       return "neutral"
    if rsi < 35:          return "positive"
    if rsi > 65:          return "negative"
    if 45 <= rsi <= 55:   return "neutral"
    return "warning"

def color_gap(gap):
    return "positive" if gap >= 0 else "negative"

def rsi_label(rsi):
    if rsi is None: return "N/D"
    if rsi < 30:    return f"{rsi} 🔵"
    if rsi < 40:    return f"{rsi} ↘"
    if rsi > 70:    return f"{rsi} 🔴"
    if rsi > 60:    return f"{rsi} ↗"
    return str(rsi)

def badge_tipo(tipo):
    t = str(tipo).strip().upper()
    if "ETF" in t:
        return f'<span class="ticker-type-badge badge-etf">ETF</span>'
    return f'<span class="ticker-type-badge badge-accion">ACCIÓN</span>'

def bar_score(score, max_score=7):
    pct    = max(0, min(100, int((score / max_score) * 100)))
    color  = "#3fb950" if score > 0 else "#f85149" if score < 0 else "#8b949e"
    return pct, color

def premarket_badge(pct):
    if pct is None: return ""
    if pct > 0:     return f'<span class="premarket-badge pm-up">▲ PM {pct:+.2f}%</span>'
    if pct < 0:     return f'<span class="premarket-badge pm-down">▼ PM {pct:+.2f}%</span>'
    return f'<span class="premarket-badge pm-flat">PM {pct:.2f}%</span>'

def rango_dia_pct(precio, min_d, max_d):
    """Posición del precio actual dentro del rango del día (0-100%)"""
    rango = max_d - min_d
    if rango <= 0: return 50
    return round(((precio - min_d) / rango) * 100, 1)

def build_chart(df_graf, tendencia):
    """Construye gráfico Altair enriquecido con EMAs y volumen"""
    color_linea = "#3fb950" if tendencia == "ALCISTA" else "#f85149"
    color_ema9  = "#f0c040"
    color_ema21 = "#c084fc"

    # Área de precio
    area = alt.Chart(df_graf).mark_area(
        line={'color': color_linea, 'strokeWidth': 1.5},
        color=alt.Gradient(
            gradient='linear',
            stops=[
                alt.GradientStop(color=color_linea + "40", offset=0),
                alt.GradientStop(color=color_linea + "05", offset=1),
            ],
            x1=1, y1=0, x2=1, y2=1
        )
    ).encode(
        x=alt.X('x:T', axis=None),
        y=alt.Y('close:Q', axis=None, scale=alt.Scale(zero=False))
    )

    # EMA 9
    ema9_line = alt.Chart(df_graf).mark_line(
        color=color_ema9, strokeWidth=1.2, strokeDash=[3, 2]
    ).encode(
        x='x:T',
        y=alt.Y('ema9:Q', scale=alt.Scale(zero=False), axis=None)
    )

    # EMA 21
    ema21_line = alt.Chart(df_graf).mark_line(
        color=color_ema21, strokeWidth=1.2, strokeDash=[5, 3]
    ).encode(
        x='x:T',
        y=alt.Y('ema21:Q', scale=alt.Scale(zero=False), axis=None)
    )

    # Barras de volumen (normalizadas para aparecer en la base)
    vol_max = df_graf['volume'].max()
    df_graf = df_graf.copy()
    df_graf['vol_norm'] = (df_graf['volume'] / vol_max).fillna(0) if vol_max > 0 else 0
    df_graf['ema9']  = pd.to_numeric(df_graf['ema9'],  errors='coerce').ffill()
    df_graf['ema21'] = pd.to_numeric(df_graf['ema21'], errors='coerce').ffill()

    # Precio mínimo y máximo para escalar volumen en eje Y del precio
    p_min_g = df_graf['close'].min()
    p_max_g = df_graf['close'].max()
    p_range = p_max_g - p_min_g if (p_max_g - p_min_g) > 0 else 1
    df_graf['vol_y']    = p_min_g
    df_graf['vol_y2']   = p_min_g + df_graf['vol_norm'] * p_range * 0.25

    vol_bars = alt.Chart(df_graf).mark_bar(
        color="#8b949e", opacity=0.25
    ).encode(
        x='x:T',
        y=alt.Y('vol_y:Q', scale=alt.Scale(zero=False), axis=None),
        y2='vol_y2:Q'
    )

    chart = (vol_bars + area + ema9_line + ema21_line).properties(
        height=90,
        background='transparent'
    ).configure_view(
        strokeWidth=0
    )
    return chart

# ─────────────────────────────────────────────────────────────
# 7. SIDEBAR
# ─────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ FILTROS")
    p_min    = st.number_input("Precio Mín ($)",  0.01,  2000.0,  0.50,  step=0.50)
    p_max    = st.number_input("Precio Máx ($)",  0.01,  2000.0, 17.00,  step=1.0)
    gap_min  = st.slider("GAP Mínimo (%)", -10.0, 30.0, 1.0, 0.5)
    vol_min  = st.slider("Volumen mínimo (ratio vs avg)", 0.5, 5.0, 1.0, 0.5,
                         help="1.0 = volumen normal. 2.0 = doble del promedio.")
    señales_min = st.slider("Señales mínimas para mostrar", 1, 6, 2,
                             help="Cuántos indicadores deben coincidir.")

    st.divider()
    filtro_tipo = st.selectbox("Tipo de activo", ["TODOS", "accion", "ETF"])

    st.divider()
    st.markdown("## 📱 WHATSAPP")
    id_ins   = st.text_input("ID Instancia",   "7103533853")
    token_ins = st.text_input("Token API",     "e5f6764f996d4c9ea88594a98ebd1741f6ab9f8502a24687b5",
                               type="password")
    celular  = st.text_input("Número destino", "5492664300161")

    st.divider()
    ahora_arg = datetime.datetime.now(ZONA_ARG)
    ahora_ny  = datetime.datetime.now(ZONA_NY)
    st.markdown(f"""
    <div style="font-family:'Space Mono',monospace; font-size:0.68rem; color:#8b949e; line-height:2">
    🇦🇷 {ahora_arg.strftime('%H:%M')} ART<br>
    🇺🇸 {ahora_ny.strftime('%H:%M')} ET<br>
    {"🌅 PRE-MERCADO" if 4 <= ahora_ny.hour < 9 else
     "📈 MERCADO ABIERTO" if 9 <= ahora_ny.hour < 16 else
     "🌙 MERCADO CERRADO"}
    </div>
    """, unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 8. PANTALLA PRINCIPAL
# ─────────────────────────────────────────────────────────────
st.markdown("# 🚀 Scanner Momentum USA")

if not os.path.exists(RUTA_CSV):
    st.error(f"❌ No se encontró `{RUTA_CSV}`. Colocá el archivo en la misma carpeta que este script.")
    st.stop()

# Cargar CSV
df_csv     = pd.read_csv(RUTA_CSV)
df_csv.columns = df_csv.columns.str.strip().str.upper()
col_ticker = [c for c in df_csv.columns if 'TICK' in c][0]
col_tipo_matches = [c for c in df_csv.columns if 'TIPO' in c or 'TYPE' in c]
col_tipo = col_tipo_matches[0] if col_tipo_matches else None

# Filtrar por tipo si corresponde
if filtro_tipo != "TODOS" and col_tipo:
    df_filtrado = df_csv[df_csv[col_tipo].str.upper() == filtro_tipo.upper()]
else:
    df_filtrado = df_csv

tickers_list = df_filtrado[col_ticker].dropna().astype(str).str.strip().str.upper().unique().tolist()

# Diccionario tipo por ticker
tipo_dict = {}
if col_tipo:
    for _, row in df_csv.iterrows():
        tipo_dict[str(row[col_ticker]).strip().upper()] = str(row[col_tipo]).strip()

# Info bar
st.markdown(f"""
<div class="info-box">
📂 <strong>{RUTA_CSV}</strong> — {len(tickers_list)} activos cargados
{"| 🔍 Tipo: " + filtro_tipo if filtro_tipo != "TODOS" else ""}
| 💲 Precio: ${p_min}–${p_max}
| 📊 GAP ≥ {gap_min}%
| ⚡ Señales ≥ {señales_min}
</div>
""", unsafe_allow_html=True)

# Inicializar estado
if 'resultados' not in st.session_state:
    st.session_state.resultados   = []
if 'ts_escaneo' not in st.session_state:
    st.session_state.ts_escaneo   = None

# ── Botones ──────────────────────────────────────────────────
col_b1, col_b2, col_b3 = st.columns([1, 1, 4])

with col_b1:
    escanear = st.button("🔍  ESCANEAR", use_container_width=True)

if st.session_state.resultados:
    with col_b2:
        enviar_wa = st.button("📱  WHATSAPP", use_container_width=True)
    if enviar_wa:
        try:
            ahora = datetime.datetime.now(ZONA_ARG)
            msg   = f"🔔 *SCANNER MOMENTUM* ({ahora.strftime('%d/%m %H:%M')} ART)\n"
            msg  += f"💲 Rango: ${p_min}–${p_max} | GAP≥{gap_min}%\n\n"
            for r in st.session_state.resultados:
                pm_str = f" | PM:{r['PremarketPct']:+.1f}%" if r['PremarketPct'] else ""
                msg += (f"📈 *{r['Ticker']}* [{r['Tipo']}]\n"
                        f"   ${r['Precio']} | GAP:{r['GAP']:+.1f}%{pm_str}\n"
                        f"   RSI:{r['RSI']} | Vol:{r['VolRatio']}x | {r['Tendencia']}\n"
                        f"   Señales: {r['TotalSenales']} | Score: {r['Score']:+d}\n\n")
            msg += "_⚠️ Solo referencia. No es consejo financiero._"
            greenAPI = API.GreenApi(id_ins, token_ins)
            greenAPI.sending.sendMessage(f"{celular}@c.us", msg)
            st.toast("✅ Mensaje enviado a WhatsApp", icon='📲')
        except Exception as e:
            st.error(f"Error al enviar: {e}")

# ── Escaneo ──────────────────────────────────────────────────
if escanear:
    with st.spinner(f"⚡ Analizando {len(tickers_list)} activos..."):
        start = time.time()
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
            raw = list(ex.map(obtener_datos, tickers_list))

        resultados = [r for r in raw if r is not None]

        # Enriquecer con tipo del CSV
        for r in resultados:
            r['Tipo'] = tipo_dict.get(r['Ticker'], "—")

        # Aplicar filtros adicionales
        resultados = [
            r for r in resultados
            if r['VolRatio'] >= vol_min
            and (len(r['SenalesCompra']) + len(r['SenalesVenta'])) >= señales_min
        ]

        # Ordenar: más señales de compra primero, luego por score
        resultados.sort(key=lambda x: (len(x['SenalesCompra']), x['Score']), reverse=True)
        st.session_state.resultados  = resultados[:MAX_RESULTS]
        st.session_state.ts_escaneo  = time.time()
        elapsed = round(time.time() - start, 1)

    if not st.session_state.resultados:
        st.warning("Sin resultados con los filtros actuales. Probá reducir señales mínimas o volumen.")
    else:
        st.toast(f"✅ {len(st.session_state.resultados)} oportunidades en {elapsed}s", icon='📊')

# ── Mostrar resultados ────────────────────────────────────────
if st.session_state.resultados:

    res_list = st.session_state.resultados

    # Stats bar
    avg_rsi = round(np.mean([r['RSI'] for r in res_list if r['RSI']]), 1)
    avg_gap = round(np.mean([r['GAP'] for r in res_list]), 2)
    ts      = st.session_state.ts_escaneo
    ts_str  = datetime.datetime.fromtimestamp(ts, tz=ZONA_ARG).strftime('%H:%M:%S') if ts else "—"

    st.markdown(f"""
    <div class="stats-bar">
        <div class="stat-item">
            <span class="stat-value">{len(res_list)}</span>
            <span class="stat-label">Resultados</span>
        </div>
        <div class="stat-item">
            <span class="stat-value" style="color:#d29922">{avg_rsi}</span>
            <span class="stat-label">RSI promedio</span>
        </div>
        <div class="stat-item">
            <span class="stat-value" style="color:#3fb950">+{avg_gap}%</span>
            <span class="stat-label">GAP promedio</span>
        </div>
        <div class="stat-item">
            <span class="stat-value" style="color:#8b949e; font-size:1rem">{ts_str}</span>
            <span class="stat-label">Último escaneo</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Renderizar tarjetas con st.columns() usando widgets nativos de Streamlit ──
    # Se evita st.markdown(html) dentro de columnas porque Streamlit lo sanitiza.
    # En su lugar se usa st.metric, st.caption y st.progress nativos + un bloque
    # HTML mínimo solo para el encabezado, que sí renderiza correctamente.

    cols = st.columns(3)
    for i, r in enumerate(res_list):
        with cols[i % 3]:
            acc_color  = r['ColorTendencia']
            gap_sign   = "+" if r['GAP'] >= 0 else ""
            atr_str    = f"{r['ATR_pct']:.1f}%" if r['ATR_pct'] else "N/D"
            vwap_str   = f"${r['VWAP']:.3f}" if r['VWAP'] else "N/D"
            score_pct, score_color = bar_score(r['Score'])
            pm_txt     = f"  PM {r['PremarketPct']:+.2f}%" if r['PremarketPct'] else ""
            tipo_txt   = str(r['Tipo']).upper()

            # ── Borde superior de color con CSS inline ──────────────────
            st.markdown(
                f'''<div style="border-top:3px solid {acc_color};
                    border-radius:10px 10px 0 0;
                    background:#161b22;
                    padding:12px 14px 6px 14px;
                    border-left:1px solid #30363d;
                    border-right:1px solid #30363d;
                    margin-bottom:0">
                    <span style="font-family:Space Mono,monospace;font-size:1.1rem;
                        font-weight:700;color:#58a6ff;letter-spacing:1px">
                        {r['Ticker']}
                    </span>
                    <span style="font-size:0.65rem;font-weight:700;
                        padding:2px 7px;border-radius:20px;margin-left:6px;
                        background:rgba(33,150,243,0.15);color:#58a6ff;
                        border:1px solid rgba(33,150,243,0.3)">
                        {tipo_txt}
                    </span>
                    {f'<span style="font-size:0.65rem;font-weight:700;padding:2px 7px;border-radius:4px;margin-left:4px;background:rgba(63,185,80,0.15);color:#3fb950;border:1px solid rgba(63,185,80,0.3)">{pm_txt}</span>' if pm_txt else ''}
                    <div style="float:right;text-align:right;font-size:0.65rem;color:{acc_color};font-weight:700;margin-top:2px">
                        {r['Tendencia']} · EMA9 {r['EMA9']} / EMA21 {r['EMA21']}
                    </div>
                </div>''',
                unsafe_allow_html=True
            )

            # ── Precio + GAP ─────────────────────────────────────────────
            gap_color  = "#3fb950" if r['GAP'] >= 0 else "#f85149"
            var5_color = "#3fb950" if r['VarSemana'] >= 0 else "#f85149"
            st.markdown(
                f'''<div style="background:#161b22;padding:6px 14px 10px 14px;
                    border-left:1px solid #30363d;border-right:1px solid #30363d">
                    <span style="font-family:Space Mono,monospace;font-size:1.5rem;
                        font-weight:700;color:#e6edf3">${r['Precio']}</span>
                    <span style="font-size:1rem;font-weight:700;margin-left:8px;
                        color:{gap_color}">{gap_sign}{r['GAP']}%</span>
                    <span style="font-size:0.75rem;color:{var5_color};margin-left:8px">
                        5d: {r['VarSemana']:+.1f}%</span>
                </div>''',
                unsafe_allow_html=True
            )

            # ── Grilla de métricas con st.columns nativas ────────────────
            st.markdown(
                '<div style="background:#161b22;padding:4px 14px 8px 14px;' +
                'border-left:1px solid #30363d;border-right:1px solid #30363d">',
                unsafe_allow_html=True
            )
            m1, m2, m3 = st.columns(3)
            rsi_color = {"positive":"#3fb950","negative":"#f85149",
                         "warning":"#d29922","neutral":"#8b949e"}[color_rsi(r['RSI'])]
            vol_color = "#3fb950" if r['VolRatio'] >= 2 else "#d29922" if r['VolRatio'] >= 1.5 else "#8b949e"
            with m1:
                st.markdown(f'''<div style="text-align:center;padding:4px 0">
                    <div style="font-size:0.58rem;color:#8b949e;text-transform:uppercase;
                        letter-spacing:.5px">RSI</div>
                    <div style="font-family:Space Mono,monospace;font-size:0.82rem;
                        font-weight:700;color:{rsi_color}">{rsi_label(r['RSI'])}</div>
                </div>''', unsafe_allow_html=True)
            with m2:
                st.markdown(f'''<div style="text-align:center;padding:4px 0">
                    <div style="font-size:0.58rem;color:#8b949e;text-transform:uppercase;
                        letter-spacing:.5px">Volumen</div>
                    <div style="font-family:Space Mono,monospace;font-size:0.82rem;
                        font-weight:700;color:{vol_color}">{r['VolRatio']}x</div>
                </div>''', unsafe_allow_html=True)
            with m3:
                st.markdown(f'''<div style="text-align:center;padding:4px 0">
                    <div style="font-size:0.58rem;color:#8b949e;text-transform:uppercase;
                        letter-spacing:.5px">ATR%</div>
                    <div style="font-family:Space Mono,monospace;font-size:0.82rem;
                        font-weight:700;color:#d29922">{atr_str}</div>
                </div>''', unsafe_allow_html=True)

            m4, m5, m6 = st.columns(3)
            with m4:
                st.markdown(f'''<div style="text-align:center;padding:4px 0">
                    <div style="font-size:0.58rem;color:#8b949e;text-transform:uppercase;
                        letter-spacing:.5px">VWAP</div>
                    <div style="font-family:Space Mono,monospace;font-size:0.82rem;
                        font-weight:700;color:#8b949e">{vwap_str}</div>
                </div>''', unsafe_allow_html=True)
            with m5:
                st.markdown(f'''<div style="text-align:center;padding:4px 0">
                    <div style="font-size:0.58rem;color:#8b949e;text-transform:uppercase;
                        letter-spacing:.5px">Score</div>
                    <div style="font-family:Space Mono,monospace;font-size:0.82rem;
                        font-weight:700;color:{score_color}">{r['Score']:+d}</div>
                </div>''', unsafe_allow_html=True)
            with m6:
                st.markdown(f'''<div style="text-align:center;padding:4px 0">
                    <div style="font-size:0.58rem;color:#8b949e;text-transform:uppercase;
                        letter-spacing:.5px">Señales</div>
                    <div style="font-family:Space Mono,monospace;font-size:0.82rem;
                        font-weight:700;color:{score_color}">⚡ {r['TotalSenales']}</div>
                </div>''', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

            # ── Barra de score (st.progress nativo) ─────────────────────
            st.progress(max(1, score_pct) / 100,
                        text=f"Score {r['Score']:+d}  |  {r['TotalSenales']} señales activas")

            # ── Tags de señales ──────────────────────────────────────────
            all_tags = (
                [f"🟢 {s}" for s in r['SenalesCompra'][:3]] +
                [f"🔴 {s}" for s in r['SenalesVenta'][:2]]
            )
            if all_tags:
                st.caption("  ·  ".join(all_tags))

            # ── Rango del día ────────────────────────────────────────────
            pos_dia  = rango_dia_pct(r['Precio'], r['MinDia'], r['MaxDia'])
            rango_pct_norm = pos_dia / 100.0
            st.markdown(
                f'''<div style="background:#161b22;padding:4px 14px 10px 14px;
                    border-left:1px solid #30363d;border-right:1px solid #30363d;
                    border-bottom:1px solid #30363d;border-radius:0 0 10px 10px;
                    margin-bottom:2px">
                    <div style="font-size:0.60rem;color:#8b949e;margin-bottom:4px">
                        Rango día: <b style="color:#e6edf3">${r['MinDia']}</b>
                        &nbsp;—&nbsp;
                        <b style="color:#e6edf3">${r['MaxDia']}</b>
                        &nbsp;·&nbsp; precio en <b style="color:{acc_color}">{pos_dia:.0f}%</b> del rango
                    </div>
                    <div style="height:5px;background:#21262d;border-radius:3px;position:relative">
                        <div style="position:absolute;height:100%;width:100%;
                            background:linear-gradient(90deg,#f85149,#d29922,#3fb950);
                            border-radius:3px;opacity:0.6"></div>
                        <div style="position:absolute;width:10px;height:10px;
                            background:#fff;border-radius:50%;top:-2.5px;
                            left:calc({pos_dia:.1f}% - 5px);
                            box-shadow:0 0 5px rgba(255,255,255,.6)"></div>
                    </div>
                </div>''',
                unsafe_allow_html=True
            )

            # ── Gráfico Altair (funciona bien fuera del HTML custom) ─────
            chart = build_chart(r['Data'], r['Tendencia'])
            st.altair_chart(chart, use_container_width=True)

            # ── Leyenda del gráfico ──────────────────────────────────────
            leg_color = r['ColorTendencia']
            st.markdown(
                f'<div style="display:flex;gap:12px;padding:0 4px 10px;'
                f'font-size:0.60rem;color:#8b949e">'
                f'<span style="color:{leg_color}">━ Precio</span>'
                f'<span style="color:#f0c040">╌ EMA9</span>'
                f'<span style="color:#c084fc">╌ EMA21</span>'
                f'<span>▊ Vol</span></div>',
                unsafe_allow_html=True
            )

else:
    st.markdown("""
    <div style="text-align:center; padding:60px 20px; color:#484f58">
        <div style="font-size:3rem; margin-bottom:12px">📡</div>
        <div style="font-family:'Space Mono',monospace; font-size:1rem; color:#8b949e">
            Hacé clic en ESCANEAR para analizar el mercado
        </div>
        <div style="font-size:0.80rem; margin-top:8px">
            Se analizarán {len(tickers_list)} activos del archivo CSV
        </div>
    </div>
    """.replace("{len(tickers_list)}", str(len(tickers_list))), unsafe_allow_html=True)
