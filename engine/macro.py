"""
macro.py — Módulo de Regime Macro & Market Breadth (Nível 1).

Calcula:
- % de ativos acima de SMA 50 e SMA 200
- Classificação de regime (Favorável / Neutro / Defensivo)
- Correlações rolantes entre classes de ativos
- Score Macro (0-100)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np
import pandas as pd


@dataclass
class MacroRegime:
    """Resultado da análise de regime macro."""

    pct_above_sma50: float      # % de ativos acima da SMA 50
    pct_above_sma200: float     # % de ativos acima da SMA 200
    regime: str                 # 'Favorável', 'Neutro', 'Defensivo'
    regime_color: str           # Cor para badge UI
    score: float                # Score macro 0-100
    breadth_history_50: pd.Series | None = None   # Série histórica breadth SMA50
    breadth_history_200: pd.Series | None = None  # Série histórica breadth SMA200
    correlations: dict[str, float] | None = None  # Correlações rolantes


def compute_sma(series: pd.Series, window: int) -> pd.Series:
    """Calcula a Média Móvel Simples."""
    return series.rolling(window=window, min_periods=window).mean()


def compute_market_breadth(
    universe_data: dict[str, pd.DataFrame],
    sma_window: int = 200,
) -> tuple[float, pd.Series | None]:
    """Calcula % de ativos acima da SMA especificada.

    Args:
        universe_data: {ticker: DataFrame OHLCV}.
        sma_window: Período da SMA (50 ou 200).

    Returns:
        Tupla (percentual_atual, série_histórica_percentual).
    """
    if not universe_data:
        return 0.0, None

    daily_above: dict[str, pd.Series] = {}

    for ticker, df in universe_data.items():
        if len(df) < sma_window:
            continue
        close = df["Close"]
        sma = compute_sma(close, sma_window)
        above = (close > sma).astype(float)
        daily_above[ticker] = above

    if not daily_above:
        return 0.0, None

    # Combinar todos os tickers numa matriz, calcular % diário
    combined = pd.DataFrame(daily_above)
    pct_above = combined.mean(axis=1) * 100  # Percentual
    pct_above = pct_above.dropna()

    current_pct = pct_above.iloc[-1] if len(pct_above) > 0 else 0.0

    return float(current_pct), pct_above


def classify_regime(pct_above_sma200: float) -> tuple[str, str]:
    """Classifica o regime macro com base no breadth de SMA 200.

    Returns:
        Tupla (regime_nome, cor_hex).
    """
    if pct_above_sma200 >= 60:
        return "🟢 Favorável (Risk-On)", "#00D4AA"
    elif pct_above_sma200 >= 40:
        return "🟡 Neutro", "#FFD700"
    else:
        return "🔴 Defensivo (Risk-Off)", "#FF4444"


def compute_rolling_correlations(
    benchmark_close: pd.Series,
    other_series: dict[str, pd.Series],
    window: int = 63,
) -> dict[str, float]:
    """Calcula correlações rolantes entre benchmark e outras séries.

    Args:
        benchmark_close: Série de preços Close do benchmark.
        other_series: {nome: série de preços}.
        window: Janela de correlação rolante (21 ou 63 dias).

    Returns:
        Dicionário {nome: correlação_atual}.
    """
    correlations: dict[str, float] = {}
    bench_ret = benchmark_close.pct_change().dropna()

    for name, series in other_series.items():
        try:
            ret = series.pct_change().dropna()
            # Alinhar índices
            aligned = pd.concat([bench_ret, ret], axis=1, join="inner")
            aligned.columns = ["bench", "other"]

            if len(aligned) < window:
                continue

            rolling_corr = aligned["bench"].rolling(window).corr(aligned["other"])
            current_corr = rolling_corr.iloc[-1]

            if not np.isnan(current_corr):
                correlations[name] = float(current_corr)
        except Exception:
            continue

    return correlations


def compute_macro_score(pct_above_sma50: float, pct_above_sma200: float) -> float:
    """Calcula o score macro (0-100) baseado em breadth.

    Combina ambos os breadth indicators com pesos:
    - 40% peso para % > SMA200 (indicador de longo prazo)
    - 60% peso para % > SMA50 (indicador de médio prazo)

    Args:
        pct_above_sma50: Percentual de ativos acima da SMA 50.
        pct_above_sma200: Percentual de ativos acima da SMA 200.

    Returns:
        Score de 0 a 100.
    """
    # Normalizar para escala 0-100
    # Se 80%+ dos ativos estão acima = score máximo
    # Se 0% estão acima = score 0
    score_50 = np.clip(pct_above_sma50, 0, 100)
    score_200 = np.clip(pct_above_sma200, 0, 100)

    raw_score = 0.60 * score_50 + 0.40 * score_200
    return float(np.clip(raw_score, 0, 100))


def analyze_macro(
    universe_data: dict[str, pd.DataFrame],
    benchmark_data: pd.DataFrame | None = None,
    extra_series: dict[str, pd.Series] | None = None,
) -> MacroRegime:
    """Pipeline completo de análise macro.

    Args:
        universe_data: Dados OHLCV de todos os ativos.
        benchmark_data: DataFrame do benchmark (para correlações).
        extra_series: Séries adicionais para correlação (Dólar, DI, etc.).

    Returns:
        Objeto MacroRegime com todos os resultados.
    """
    # Market Breadth
    pct_50, hist_50 = compute_market_breadth(universe_data, sma_window=50)
    pct_200, hist_200 = compute_market_breadth(universe_data, sma_window=200)

    # Regime
    regime, color = classify_regime(pct_200)

    # Score
    score = compute_macro_score(pct_50, pct_200)

    # Correlações (se benchmark disponível)
    correlations = None
    if benchmark_data is not None and extra_series:
        correlations = compute_rolling_correlations(
            benchmark_data["Close"], extra_series, window=63
        )

    return MacroRegime(
        pct_above_sma50=pct_50,
        pct_above_sma200=pct_200,
        regime=regime,
        regime_color=color,
        score=score,
        breadth_history_50=hist_50,
        breadth_history_200=hist_200,
        correlations=correlations,
    )
