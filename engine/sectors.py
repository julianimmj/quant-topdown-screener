"""
sectors.py — Módulo de Força Relativa Setorial (Nível 2).

Calcula:
- RS Ratio de cada setor vs. Benchmark
- RS Trend (RS Ratio > SMA50 do RS Ratio)
- ROC 63 e 126 dias do RS Ratio
- Quartil superior de setores líderes
- Score Setorial (0-100) por ativo
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd


@dataclass
class SectorRS:
    """Resultado da análise de Força Relativa de um setor."""

    sector: str
    rs_ratio_current: float          # RS Ratio atual
    rs_ratio_series: pd.Series       # Série histórica do RS Ratio
    rs_above_sma50: bool             # RS Ratio > SMA50(RS Ratio)
    roc_63: float                    # Rate of Change 63 dias do RS Ratio
    roc_126: float                   # Rate of Change 126 dias do RS Ratio
    quartile: int                    # Quartil do ranking (1=top, 4=bottom)
    score: float                     # Score setorial 0-100


@dataclass
class SectorAnalysis:
    """Container para toda a análise setorial."""

    sectors: dict[str, SectorRS] = field(default_factory=dict)
    ranking: list[str] = field(default_factory=list)     # Setores ordenados por score
    top_quartile: list[str] = field(default_factory=list)  # Setores no quartil superior


def compute_rs_ratio(
    sector_prices: pd.Series,
    benchmark_prices: pd.Series,
) -> pd.Series:
    """Calcula o RS Ratio = Preço Setor / Preço Benchmark.

    Normaliza base 100 no início da série para comparabilidade.

    Args:
        sector_prices: Série de preços do setor/ETF.
        benchmark_prices: Série de preços do benchmark.

    Returns:
        Série do RS Ratio normalizado.
    """
    # Alinhar índices
    aligned = pd.concat(
        [sector_prices, benchmark_prices], axis=1, join="inner"
    )
    aligned.columns = ["sector", "benchmark"]
    aligned = aligned.dropna()

    if len(aligned) < 10:
        return pd.Series(dtype=float)

    rs = aligned["sector"] / aligned["benchmark"]
    # Normalizar base 100
    rs = rs / rs.iloc[0] * 100
    return rs


def compute_roc(series: pd.Series, periods: int) -> float:
    """Calcula Rate of Change em % para N períodos.

    Args:
        series: Série de preços/valores.
        periods: Número de períodos.

    Returns:
        ROC em percentual.
    """
    if len(series) < periods + 1:
        return 0.0
    current = series.iloc[-1]
    past = series.iloc[-periods - 1]
    if past == 0:
        return 0.0
    return float((current - past) / past * 100)


def analyze_sectors(
    sector_prices: dict[str, pd.Series],
    benchmark_close: pd.Series,
) -> SectorAnalysis:
    """Pipeline completo de análise de Força Relativa Setorial.

    Args:
        sector_prices: {nome_setor: série de preços Close}.
        benchmark_close: Série de preços Close do benchmark.

    Returns:
        SectorAnalysis com ranking e scores.
    """
    result = SectorAnalysis()
    sector_data: list[tuple[str, float]] = []

    for sector_name, prices in sector_prices.items():
        try:
            # RS Ratio
            rs = compute_rs_ratio(prices, benchmark_close)
            if rs.empty:
                continue

            # ── 1. Tendência Estrutural do RS Ratio (35% peso) ──
            sma50_rs = rs.rolling(window=50, min_periods=20).mean()
            sma200_rs = rs.rolling(window=200, min_periods=50).mean()

            last_rs = float(rs.iloc[-1])
            last_sma50 = float(sma50_rs.iloc[-1]) if len(sma50_rs.dropna()) > 0 else last_rs
            last_sma200 = float(sma200_rs.iloc[-1]) if len(sma200_rs.dropna()) > 0 else last_sma50

            rs_above = bool(last_rs > last_sma50)

            # Distância contínua para as médias (eliminando saltos binários de 40 pontos)
            dist_50 = ((last_rs - last_sma50) / last_sma50 * 100) if last_sma50 > 0 else 0.0
            dist_200 = ((last_rs - last_sma200) / last_sma200 * 100) if last_sma200 > 0 else 0.0

            # Mapeamento contínuo centrado em 50 (Neutro):
            # dist_50 ±6% -> [0, 100]; dist_200 ±12% -> [0, 100]
            score_trend_50 = float(np.clip(50.0 + (dist_50 / 6.0) * 50.0, 0, 100))
            score_trend_200 = float(np.clip(50.0 + (dist_200 / 12.0) * 50.0, 0, 100))
            score_trend = 0.65 * score_trend_50 + 0.35 * score_trend_200

            # ── 2. Momentum Relativo de Médio Prazo (ROC 63d, 40% peso) ──
            roc63 = compute_roc(rs, 63)
            # Alpha de 1 trimestre: ±15% mapeado continuamente para [0, 100] centrado em 50
            score_roc63 = float(np.clip(50.0 + (roc63 / 15.0) * 50.0, 0, 100))

            # ── 3. Momentum Relativo de Longo Prazo (ROC 126d, 25% peso) ──
            roc126 = compute_roc(rs, 126)
            # Alpha de 2 trimestres: ±25% mapeado continuamente para [0, 100] centrado em 50
            score_roc126 = float(np.clip(50.0 + (roc126 / 25.0) * 50.0, 0, 100))

            # ── 4. Score Setorial Ponderado Contínuo ──
            raw_score = 0.35 * score_trend + 0.40 * score_roc63 + 0.25 * score_roc126
            raw_score = float(np.clip(raw_score, 0, 100))

            sector_rs = SectorRS(
                sector=sector_name,
                rs_ratio_current=last_rs,
                rs_ratio_series=rs,
                rs_above_sma50=rs_above,
                roc_63=roc63,
                roc_126=roc126,
                quartile=0,  # Será calculado após ranking
                score=raw_score,
            )
            result.sectors[sector_name] = sector_rs
            sector_data.append((sector_name, raw_score))

        except Exception:
            continue

    # Ranking e quartis
    if sector_data:
        sector_data.sort(key=lambda x: x[1], reverse=True)
        result.ranking = [s[0] for s in sector_data]

        n = len(sector_data)
        for i, (name, _) in enumerate(sector_data):
            quartile = int(i / n * 4) + 1
            quartile = min(quartile, 4)
            result.sectors[name].quartile = quartile

        # Top quartile
        cutoff = max(1, n // 4)
        result.top_quartile = result.ranking[:cutoff]

    return result


def get_ticker_sector_score(
    ticker: str,
    ticker_sector_map: dict[str, str],
    sector_analysis: SectorAnalysis,
) -> float:
    """Retorna o score setorial de um ticker baseado no seu setor.

    Args:
        ticker: Ticker do ativo.
        ticker_sector_map: Mapeamento {ticker: setor}.
        sector_analysis: Resultado da análise setorial.

    Returns:
        Score setorial 0-100.
    """
    sector = ticker_sector_map.get(ticker, "")
    if sector and sector in sector_analysis.sectors:
        return sector_analysis.sectors[sector].score
    return 50.0  # Score neutro como fallback


def is_sector_top_quartile(
    ticker: str,
    ticker_sector_map: dict[str, str],
    sector_analysis: SectorAnalysis,
) -> bool:
    """Verifica se o setor do ticker está no quartil superior.

    Args:
        ticker: Ticker do ativo.
        ticker_sector_map: Mapeamento {ticker: setor}.
        sector_analysis: Resultado da análise setorial.

    Returns:
        True se o setor está no top quartile.
    """
    sector = ticker_sector_map.get(ticker, "")
    return sector in sector_analysis.top_quartile
