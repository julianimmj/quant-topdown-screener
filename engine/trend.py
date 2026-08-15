"""
trend.py — Módulo de Qualidade de Tendência & Persistência (Nível 3).

Implementa o Trend Quality Engine para cada ativo individual:
- EMA Alignment (Preço > EMA21 > EMA50 > SMA200)
- Slope linear da SMA 50 (20 dias)
- ADX e Direcionalidade (+DI > -DI)
- Kaufman Efficiency Ratio (ER)
- Momentum Ajustado à Volatilidade (Vol-Adj ROC)

Score composto: 0-100 pontos distribuídos entre 5 dimensões.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats


@dataclass
class TrendResult:
    """Resultado da análise de tendência de um ativo individual."""

    ticker: str

    # ── Sub-scores (somam até 100) ──
    ema_alignment_score: float        # 0-25
    slope_score: float                # 0-15
    adx_score: float                  # 0-20
    efficiency_ratio_score: float     # 0-20
    vol_adj_roc_score: float          # 0-20

    # ── Valores brutos ──
    ema_aligned: bool
    slope_sma50: float
    adx_value: float
    plus_di: float
    minus_di: float
    efficiency_ratio: float
    vol_adj_roc: float

    # ── Score Total ──
    trend_score: float                # 0-100

    # ── Dados auxiliares para charting ──
    ema9: pd.Series | None = None
    ema21: pd.Series | None = None
    ema50: pd.Series | None = None
    sma200: pd.Series | None = None
    adx_series: pd.Series | None = None
    plus_di_series: pd.Series | None = None
    minus_di_series: pd.Series | None = None


# ──────────────────────── Indicadores ──────────────────────────────


def ema(series: pd.Series, period: int) -> pd.Series:
    """Exponential Moving Average."""
    return series.ewm(span=period, adjust=False, min_periods=period).mean()


def sma(series: pd.Series, period: int) -> pd.Series:
    """Simple Moving Average."""
    return series.rolling(window=period, min_periods=period).mean()


def compute_ema_alignment(close: pd.Series) -> tuple[bool, float, pd.Series, pd.Series, pd.Series, pd.Series]:
    """Verifica alinhamento: Preço > EMA21 > EMA50 > SMA200.

    Returns:
        (is_aligned, score, ema9, ema21, ema50, sma200)
    """
    ema9_s = ema(close, 9)
    ema21_s = ema(close, 21)
    ema50_s = ema(close, 50)
    sma200_s = sma(close, 200)

    last_close = close.iloc[-1]
    last_ema21 = ema21_s.iloc[-1]
    last_ema50 = ema50_s.iloc[-1]
    last_sma200 = sma200_s.iloc[-1]

    # Score granular (0-25):
    # Cada condição vale pontos parciais
    score = 0.0

    # Preço > SMA200 (fundamento de alta) = 7 pts
    if last_close > last_sma200:
        score += 7.0

    # EMA50 > SMA200 (tendência confirmada) = 6 pts
    if last_ema50 > last_sma200:
        score += 6.0

    # EMA21 > EMA50 (momentum de médio prazo) = 6 pts
    if last_ema21 > last_ema50:
        score += 6.0

    # Preço > EMA21 (momentum de curto prazo) = 6 pts
    if last_close > last_ema21:
        score += 6.0

    is_aligned = (
        last_close > last_ema21 > last_ema50 > last_sma200
    )

    return is_aligned, score, ema9_s, ema21_s, ema50_s, sma200_s


def compute_slope_sma50(close: pd.Series, lookback: int = 20) -> tuple[float, float]:
    """Calcula o slope linear da SMA 50 nos últimos 20 dias.

    Returns:
        (slope_value, score 0-15)
    """
    sma50_s = sma(close, 50)
    sma50_recent = sma50_s.dropna().tail(lookback)

    if len(sma50_recent) < lookback:
        return 0.0, 0.0

    x = np.arange(len(sma50_recent))
    y = sma50_recent.values
    result = stats.linregress(x, y)
    slope = result.slope

    # Normalizar o slope pelo preço para torná-lo comparável
    normalized_slope = slope / sma50_recent.iloc[-1] * 100  # % por dia

    # Score: 0-15
    # Slope positivo forte (>0.15% por dia) = 15
    if normalized_slope <= 0:
        score = 0.0
    else:
        score = min(15.0, normalized_slope / 0.15 * 15.0)

    return float(slope), score


def compute_adx(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> tuple[float, float, float, float, pd.Series, pd.Series, pd.Series]:
    """Calcula ADX, +DI e -DI manualmente (sem dependência de pandas_ta).

    Returns:
        (adx_value, plus_di, minus_di, score, adx_series, plus_di_series, minus_di_series)
    """
    n = len(close)
    if n < period * 3:
        empty = pd.Series(dtype=float)
        return 0.0, 0.0, 0.0, 0.0, empty, empty, empty

    # True Range
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Directional Movement
    up_move = high - high.shift(1)
    down_move = low.shift(1) - low

    plus_dm = pd.Series(np.where((up_move > down_move) & (up_move > 0), up_move, 0), index=close.index)
    minus_dm = pd.Series(np.where((down_move > up_move) & (down_move > 0), down_move, 0), index=close.index)

    # Wilder's smoothing (EMA com alpha = 1/period)
    atr = tr.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    plus_di_s = 100 * plus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr
    minus_di_s = 100 * minus_dm.ewm(alpha=1 / period, min_periods=period, adjust=False).mean() / atr

    # DX e ADX
    dx = (plus_di_s - minus_di_s).abs() / (plus_di_s + minus_di_s) * 100
    dx = dx.replace([np.inf, -np.inf], np.nan).fillna(0)
    adx_s = dx.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    adx_val = float(adx_s.iloc[-1]) if not np.isnan(adx_s.iloc[-1]) else 0.0
    plus_di_val = float(plus_di_s.iloc[-1]) if not np.isnan(plus_di_s.iloc[-1]) else 0.0
    minus_di_val = float(minus_di_s.iloc[-1]) if not np.isnan(minus_di_s.iloc[-1]) else 0.0

    # Score: 0-20
    # ADX >= 25 E +DI > -DI = score alto
    score = 0.0
    if adx_val >= 25 and plus_di_val > minus_di_val:
        # Base 12 pts por ter tendência com direção correta
        score = 12.0
        # Bonus proporcional ao ADX (25-50 → 0-8 pts adicionais)
        bonus = np.clip((adx_val - 25) / 25 * 8, 0, 8)
        score += bonus
    elif adx_val >= 20 and plus_di_val > minus_di_val:
        # Tendência emergente
        score = 7.0
    elif plus_di_val > minus_di_val:
        # Direção correta mas sem força
        score = 3.0

    return adx_val, plus_di_val, minus_di_val, score, adx_s, plus_di_s, minus_di_s


def compute_kaufman_efficiency_ratio(
    close: pd.Series,
    period: int = 21,
) -> tuple[float, float]:
    """Calcula o Kaufman Efficiency Ratio (ER).

    ER = |Close_t - Close_{t-n}| / Σ|Close_i - Close_{i-1}|

    Returns:
        (er_value, score 0-20)
    """
    if len(close) < period + 1:
        return 0.0, 0.0

    # Deslocamento direcional (sinal)
    direction = abs(close.iloc[-1] - close.iloc[-period - 1])

    # Soma dos movimentos absolutos (ruído)
    volatility = close.diff().abs().tail(period).sum()

    if volatility == 0:
        return 0.0, 0.0

    er = direction / volatility

    # Score: 0-20
    # ER >= 0.40 → começa a pontuar, ER = 1.0 = máximo
    if er < 0.20:
        score = 0.0
    elif er < 0.40:
        score = (er - 0.20) / 0.20 * 8  # 0-8 pts
    else:
        score = 8.0 + (er - 0.40) / 0.60 * 12  # 8-20 pts

    score = min(20.0, score)
    return float(er), score


def compute_vol_adj_roc(
    close: pd.Series,
    high: pd.Series,
    low: pd.Series,
    roc_period: int = 63,
    atr_period: int = 14,
) -> tuple[float, float]:
    """Calcula Momentum Ajustado à Volatilidade.

    Vol-Adj ROC = ROC(63) / (ATR(14) / Preço)

    Returns:
        (vol_adj_roc_value, score 0-20)
    """
    if len(close) < roc_period + 1:
        return 0.0, 0.0

    # ROC
    roc = (close.iloc[-1] - close.iloc[-roc_period - 1]) / close.iloc[-roc_period - 1] * 100

    # ATR
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=atr_period, min_periods=atr_period).mean()
    last_atr = atr.iloc[-1]
    last_price = close.iloc[-1]

    if last_price == 0 or last_atr == 0:
        return 0.0, 0.0

    normalized_vol = last_atr / last_price * 100  # ATR como % do preço
    vol_adj = roc / normalized_vol if normalized_vol > 0 else 0.0

    # Score: 0-20
    # vol_adj positivo indica momentum forte ajustado ao risco
    if vol_adj <= 0:
        score = 0.0
    else:
        # Escala: vol_adj de 0 a 10 → score 0 a 20
        score = min(20.0, vol_adj / 10.0 * 20.0)

    return float(vol_adj), score


# ──────────────────── Pipeline Principal ──────────────────────────


def analyze_trend(
    ticker: str,
    df: pd.DataFrame,
) -> TrendResult | None:
    """Pipeline completo de análise de tendência para um ativo.

    Args:
        ticker: Ticker do ativo.
        df: DataFrame OHLCV.

    Returns:
        TrendResult ou None se dados insuficientes.
    """
    if len(df) < 200:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    try:
        # 1. EMA Alignment (0-25)
        is_aligned, ema_score, ema9_s, ema21_s, ema50_s, sma200_s = compute_ema_alignment(close)

        # 2. Slope SMA 50 (0-15)
        slope_val, slope_score = compute_slope_sma50(close, lookback=20)

        # 3. ADX (0-20)
        adx_val, plus_di, minus_di, adx_score, adx_s, plus_di_s, minus_di_s = compute_adx(
            high, low, close, period=14
        )

        # 4. Kaufman ER (0-20)
        er_val, er_score = compute_kaufman_efficiency_ratio(close, period=21)

        # 5. Vol-Adj ROC (0-20)
        var_val, var_score = compute_vol_adj_roc(close, high, low, roc_period=63, atr_period=14)

        # Total Trend Score
        total = ema_score + slope_score + adx_score + er_score + var_score

        return TrendResult(
            ticker=ticker,
            ema_alignment_score=ema_score,
            slope_score=slope_score,
            adx_score=adx_score,
            efficiency_ratio_score=er_score,
            vol_adj_roc_score=var_score,
            ema_aligned=is_aligned,
            slope_sma50=slope_val,
            adx_value=adx_val,
            plus_di=plus_di,
            minus_di=minus_di,
            efficiency_ratio=er_val,
            vol_adj_roc=var_val,
            trend_score=total,
            ema9=ema9_s,
            ema21=ema21_s,
            ema50=ema50_s,
            sma200=sma200_s,
            adx_series=adx_s,
            plus_di_series=plus_di_s,
            minus_di_series=minus_di_s,
        )

    except Exception:
        return None


def batch_analyze_trends(
    universe_data: dict[str, pd.DataFrame],
) -> dict[str, TrendResult]:
    """Executa análise de tendência para todo o universo.

    Args:
        universe_data: {ticker: DataFrame OHLCV}.

    Returns:
        {ticker: TrendResult} apenas para ativos válidos.
    """
    results: dict[str, TrendResult] = {}

    for ticker, df in universe_data.items():
        result = analyze_trend(ticker, df)
        if result is not None:
            results[ticker] = result

    return results
