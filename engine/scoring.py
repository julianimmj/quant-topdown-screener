"""
scoring.py — Módulo de Scoring Final (Trend Quality Score & Trigger).

Combina os 4 níveis do pipeline em um score final TQS (0-100):
  TQS = w_macro × Score_Macro + w_setor × Score_Setor +
        w_trend × Score_Trend + w_trigger × Score_Trigger

Também implementa o Nível 4 (Trigger / Anti-Exaustão).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import numpy as np
import pandas as pd


# ────────────────── Pesos Padrão do TQS ───────────────────────────

DEFAULT_WEIGHTS: dict[str, float] = {
    "macro": 0.20,
    "setor": 0.20,
    "trend": 0.45,
    "trigger": 0.15,
}


@dataclass
class TriggerResult:
    """Resultado do filtro anti-exaustão e trigger de entrada."""

    distance_from_mean: float    # (Preço - SMA20) / ATR(14)
    rsi_14: float                # RSI(14)
    in_pullback_zone: bool       # Preço entre EMA9 e EMA21
    is_overbought: bool          # Distância > 2.2 ou RSI > 70
    trigger_score: float         # Score 0-100
    status: str                  # 'Compra Forte', 'Aguardar Pullback', 'Neutro', 'Sobrecomprado'
    status_emoji: str            # Emoji para badge


@dataclass
class FinalScore:
    """Score final consolidado de um ativo."""

    ticker: str
    sector: str
    macro_score: float       # 0-100
    sector_score: float      # 0-100
    trend_score: float       # 0-100
    trigger_score: float     # 0-100
    tqs: float               # TQS final 0-100
    trigger: TriggerResult | None = None
    status: str = ""
    status_emoji: str = ""

    # Sub-scores detalhados do trend
    ema_alignment: float = 0.0
    slope: float = 0.0
    adx: float = 0.0
    efficiency_ratio: float = 0.0
    vol_adj_roc: float = 0.0

    # Valores brutos relevantes
    adx_value: float = 0.0
    er_value: float = 0.0
    rsi_value: float = 0.0
    price: float = 0.0


# ──────────────── Cálculos do Trigger (Nível 4) ───────────────────


def compute_rsi(close: pd.Series, period: int = 14) -> pd.Series:
    """Calcula o Relative Strength Index (RSI).

    Usa Wilder's smoothing (EMA).

    Args:
        close: Série de preços de fechamento.
        period: Período do RSI.

    Returns:
        Série do RSI.
    """
    delta = close.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / period, min_periods=period, adjust=False).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.fillna(50)


def compute_atr(
    high: pd.Series,
    low: pd.Series,
    close: pd.Series,
    period: int = 14,
) -> pd.Series:
    """Calcula o Average True Range (ATR)."""
    tr1 = high - low
    tr2 = (high - close.shift(1)).abs()
    tr3 = (low - close.shift(1)).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    return tr.rolling(window=period, min_periods=period).mean()


def analyze_trigger(df: pd.DataFrame) -> TriggerResult | None:
    """Analisa trigger de entrada e filtro anti-exaustão.

    Args:
        df: DataFrame OHLCV do ativo.

    Returns:
        TriggerResult ou None se dados insuficientes.
    """
    if len(df) < 50:
        return None

    close = df["Close"]
    high = df["High"]
    low = df["Low"]

    last_close = close.iloc[-1]

    # SMA 20
    sma20 = close.rolling(window=20, min_periods=20).mean()
    last_sma20 = sma20.iloc[-1]

    # ATR 14
    atr = compute_atr(high, low, close, period=14)
    last_atr = atr.iloc[-1]

    # Distância da média em ATRs
    if last_atr > 0:
        distance = (last_close - last_sma20) / last_atr
    else:
        distance = 0.0

    # RSI(14)
    rsi = compute_rsi(close, period=14)
    last_rsi = float(rsi.iloc[-1])

    # EMA 9 e EMA 21 para pullback zone
    ema9 = close.ewm(span=9, adjust=False, min_periods=9).mean()
    ema21 = close.ewm(span=21, adjust=False, min_periods=21).mean()

    in_pullback = bool(
        min(ema9.iloc[-1], ema21.iloc[-1]) <= last_close <= max(ema9.iloc[-1], ema21.iloc[-1])
    )

    # Overbought check
    is_overbought = distance > 2.2 or last_rsi > 70

    # ── Score Trigger (0-100) ──
    score = 0.0

    # 1. Distância da média (0-40 pts)
    # Ideal: 0 a 1.5 ATRs da SMA20 → score alto
    # > 2.2 ATRs → sobrecomprado → score baixo
    if distance <= 0:
        # Abaixo da média → pode ser pullback ideal
        dist_score = 30.0 if distance > -1.5 else 15.0
    elif distance <= 1.0:
        dist_score = 40.0  # Zona ideal
    elif distance <= 1.5:
        dist_score = 30.0
    elif distance <= 2.0:
        dist_score = 20.0
    elif distance <= 2.2:
        dist_score = 10.0
    else:
        dist_score = 0.0
    score += dist_score

    # 2. RSI em zona ideal (0-35 pts)
    # Ideal: RSI entre 45-65 (momentum sem exaustão)
    if 45 <= last_rsi <= 65:
        rsi_score = 35.0
    elif 35 <= last_rsi < 45:
        rsi_score = 25.0  # Leve oversold
    elif 65 < last_rsi <= 70:
        rsi_score = 20.0  # Momentum alto mas controlado
    elif 70 < last_rsi <= 80:
        rsi_score = 8.0   # Sobrecomprado
    elif last_rsi > 80:
        rsi_score = 0.0   # Fortemente sobrecomprado
    else:
        rsi_score = 15.0  # Muito oversold
    score += rsi_score

    # 3. Pullback Zone (0-25 pts)
    if in_pullback:
        score += 25.0
    elif last_close > ema9.iloc[-1] and distance <= 1.5:
        score += 15.0  # Acima mas não esticado
    elif last_close > ema21.iloc[-1]:
        score += 10.0

    score = float(np.clip(score, 0, 100))

    # ── Status Label ──
    if is_overbought:
        status = "Sobrecomprado"
        emoji = "🔴"
    elif in_pullback and 40 <= last_rsi <= 65:
        status = "Compra Forte"
        emoji = "🟢"
    elif distance <= 1.5 and 40 <= last_rsi <= 70:
        status = "Compra"
        emoji = "🟡"
    elif distance > 1.5:
        status = "Aguardar Pullback"
        emoji = "🟠"
    else:
        status = "Neutro"
        emoji = "⚪"

    return TriggerResult(
        distance_from_mean=float(distance),
        rsi_14=last_rsi,
        in_pullback_zone=in_pullback,
        is_overbought=is_overbought,
        trigger_score=score,
        status=status,
        status_emoji=emoji,
    )


# ──────────────── Score Final TQS ─────────────────────────────────


def compute_tqs(
    macro_score: float,
    sector_score: float,
    trend_score: float,
    trigger_score: float,
    weights: dict[str, float] | None = None,
) -> float:
    """Calcula o Trend Quality Score (TQS) final ponderado.

    TQS = w_macro × Macro + w_setor × Setor + w_trend × Trend + w_trigger × Trigger

    Args:
        macro_score: Score macro 0-100.
        sector_score: Score setorial 0-100.
        trend_score: Score de tendência 0-100.
        trigger_score: Score de trigger 0-100.
        weights: Pesos customizados. Se None, usa DEFAULT_WEIGHTS.

    Returns:
        TQS final 0-100.
    """
    w = weights or DEFAULT_WEIGHTS

    tqs = (
        w["macro"] * macro_score
        + w["setor"] * sector_score
        + w["trend"] * trend_score
        + w["trigger"] * trigger_score
    )

    return float(np.clip(tqs, 0, 100))


def build_final_scores(
    universe_data: dict[str, pd.DataFrame],
    ticker_sector_map: dict[str, str],
    macro_score: float,
    sector_scores: dict[str, float],
    trend_results: dict[str, Any],
    weights: dict[str, float] | None = None,
) -> list[FinalScore]:
    """Constrói a lista final de scores para ranking.

    Args:
        universe_data: Dados OHLCV de cada ticker.
        ticker_sector_map: Mapeamento {ticker: setor}.
        macro_score: Score macro global.
        sector_scores: {setor: score_setorial}.
        trend_results: {ticker: TrendResult}.
        weights: Pesos customizados do TQS.

    Returns:
        Lista de FinalScore ordenada por TQS decrescente.
    """
    scores: list[FinalScore] = []

    for ticker, df in universe_data.items():
        # Trend
        trend = trend_results.get(ticker)
        if trend is None:
            continue

        # Setor
        sector = ticker_sector_map.get(ticker, "N/A")
        sec_score = sector_scores.get(sector, 50.0)

        # Trigger
        trigger = analyze_trigger(df)
        trig_score = trigger.trigger_score if trigger else 50.0

        # TQS
        tqs = compute_tqs(
            macro_score=macro_score,
            sector_score=sec_score,
            trend_score=trend.trend_score,
            trigger_score=trig_score,
            weights=weights,
        )

        # Status (baseado no trigger)
        status = trigger.status if trigger else "Neutro"
        emoji = trigger.status_emoji if trigger else "⚪"

        # Último preço
        last_price = float(df["Close"].iloc[-1])

        final = FinalScore(
            ticker=ticker,
            sector=sector,
            macro_score=macro_score,
            sector_score=sec_score,
            trend_score=trend.trend_score,
            trigger_score=trig_score,
            tqs=tqs,
            trigger=trigger,
            status=status,
            status_emoji=emoji,
            ema_alignment=trend.ema_alignment_score,
            slope=trend.slope_score,
            adx=trend.adx_score,
            efficiency_ratio=trend.efficiency_ratio_score,
            vol_adj_roc=trend.vol_adj_roc_score,
            adx_value=trend.adx_value,
            er_value=trend.efficiency_ratio,
            rsi_value=trigger.rsi_14 if trigger else 0.0,
            price=last_price,
        )
        scores.append(final)

    # Ordenar por TQS decrescente
    scores.sort(key=lambda s: s.tqs, reverse=True)
    return scores


def scores_to_dataframe(scores: list[FinalScore]) -> pd.DataFrame:
    """Converte lista de FinalScore em DataFrame para exibição.

    Args:
        scores: Lista ordenada de FinalScore.

    Returns:
        DataFrame formatado para a tabela do dashboard.
    """
    rows = []
    for i, s in enumerate(scores, 1):
        rows.append({
            "Rank": i,
            "Ticker": s.ticker,
            "Setor": s.sector,
            "Preço": round(s.price, 2),
            "TQS": round(s.tqs, 1),
            "Macro": round(s.macro_score, 1),
            "Setor RS": round(s.sector_score, 1),
            "Trend": round(s.trend_score, 1),
            "Trigger": round(s.trigger_score, 1),
            "ADX": round(s.adx_value, 1),
            "ER": round(s.er_value, 2),
            "RSI": round(s.rsi_value, 1),
            "Status": f"{s.status_emoji} {s.status}",
        })

    return pd.DataFrame(rows)
