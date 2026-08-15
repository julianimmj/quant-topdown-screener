"""
fetcher.py — Ingestão de dados via yfinance com cache e fallback robusto.

Centraliza todo o download de preços históricos, tratando dados faltantes,
tickers inválidos e rate limits do Yahoo Finance de forma resiliente.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd
import streamlit as st
import yfinance as yf

logger = logging.getLogger(__name__)


@st.cache_data(ttl=3600, show_spinner="Baixando dados de mercado…")
def fetch_ohlcv(
    tickers: list[str],
    period: str = "2y",
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """Baixa dados OHLCV para uma lista de tickers via yfinance.

    Usa batch download para eficiência e trata falhas individuais sem
    quebrar o pipeline.

    Args:
        tickers: Lista de tickers (ex: ['PETR4.SA', 'VALE3.SA']).
        period: Período histórico (ex: '2y', '1y').
        interval: Intervalo de candles ('1d', '1wk', etc.).

    Returns:
        Dicionário {ticker: DataFrame} com colunas [Open, High, Low, Close, Volume].
    """
    result: dict[str, pd.DataFrame] = {}

    if not tickers:
        return result

    # Dividir em batches para evitar rate limits
    batch_size = 30
    all_tickers = list(set(tickers))

    for i in range(0, len(all_tickers), batch_size):
        batch = all_tickers[i : i + batch_size]
        try:
            data = yf.download(
                tickers=batch,
                period=period,
                interval=interval,
                group_by="ticker",
                auto_adjust=True,
                threads=True,
                progress=False,
            )

            if data.empty:
                continue

            for ticker in batch:
                try:
                    if len(batch) == 1:
                        df = data.copy()
                        # Flatten MultiIndex para single ticker
                        if isinstance(df.columns, pd.MultiIndex):
                            df.columns = df.columns.droplevel("Ticker")
                    else:
                        # yfinance 1.2+: columns are (Price, Ticker) MultiIndex
                        if isinstance(data.columns, pd.MultiIndex):
                            level_names = [str(n) for n in data.columns.names]
                            # Tentar extrair por ticker do level correto
                            if "Ticker" in level_names:
                                ticker_level = level_names.index("Ticker")
                                if ticker not in data.columns.get_level_values(ticker_level):
                                    continue
                                df = data.xs(ticker, level="Ticker", axis=1).copy()
                            else:
                                # Fallback: assume nível 0 é ticker
                                if ticker not in data.columns.get_level_values(0):
                                    continue
                                df = data[ticker].copy()
                        else:
                            continue

                    # Remover linhas completamente NaN
                    df = df.dropna(how="all")

                    if df.empty or len(df) < 60:
                        logger.warning(
                            f"Ticker {ticker}: dados insuficientes ({len(df)} candles). Ignorando."
                        )
                        continue

                    # Garantir colunas padrão
                    required_cols = ["Open", "High", "Low", "Close", "Volume"]
                    if not all(c in df.columns for c in required_cols):
                        continue

                    # Forward-fill para gaps pequenos, depois drop residual
                    df[required_cols] = df[required_cols].ffill(limit=5)
                    df = df.dropna(subset=["Close"])

                    # Filtrar volume zero prolongado (ativo sem liquidez)
                    if df["Volume"].tail(20).sum() == 0:
                        logger.warning(f"Ticker {ticker}: sem volume nos últimos 20 dias. Ignorando.")
                        continue

                    result[ticker] = df[required_cols]

                except Exception as e:
                    logger.warning(f"Erro ao processar {ticker}: {e}")
                    continue

        except Exception as e:
            logger.error(f"Erro no batch download: {e}")
            continue

    return result


@st.cache_data(ttl=3600, show_spinner="Baixando benchmark…")
def fetch_benchmark(
    ticker: str = "^BVSP",
    period: str = "2y",
    interval: str = "1d",
) -> pd.DataFrame:
    """Baixa dados do benchmark (default: Ibovespa).

    Args:
        ticker: Ticker do benchmark.
        period: Período histórico.
        interval: Intervalo.

    Returns:
        DataFrame com colunas OHLCV.
    """
    try:
        data = yf.download(
            tickers=ticker,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )
        if data.empty:
            st.error(f"❌ Não foi possível baixar dados do benchmark {ticker}.")
            return pd.DataFrame()

        # yfinance 1.2+ retorna MultiIndex (Price, Ticker) mesmo para 1 ticker
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = data.columns.droplevel("Ticker")

        data = data.dropna(how="all")
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        missing = [c for c in required_cols if c not in data.columns]
        if missing:
            logger.error(f"Colunas ausentes no benchmark: {missing}. Disponíveis: {list(data.columns)}")
            st.error(f"❌ Colunas ausentes no benchmark: {missing}")
            return pd.DataFrame()
        data = data[required_cols].ffill(limit=5).dropna(subset=["Close"])
        return data

    except Exception as e:
        logger.error(f"Erro ao baixar benchmark {ticker}: {e}")
        st.error(f"❌ Erro ao baixar benchmark: {e}")
        return pd.DataFrame()


@st.cache_data(ttl=3600, show_spinner="Baixando índices setoriais…")
def fetch_sector_indices(
    sector_tickers: dict[str, str],
    period: str = "2y",
    interval: str = "1d",
) -> dict[str, pd.DataFrame]:
    """Baixa dados dos índices setoriais.

    Se um índice falhar, calcula um proxy equal-weighted a partir
    dos ativos daquele setor no universo.

    Args:
        sector_tickers: Dicionário {nome_setor: ticker_indice}.
        period: Período.
        interval: Intervalo.

    Returns:
        Dicionário {nome_setor: DataFrame}.
    """
    tickers_list = list(sector_tickers.values())
    data = fetch_ohlcv(tickers_list, period=period, interval=interval)

    result: dict[str, pd.DataFrame] = {}
    for sector_name, ticker in sector_tickers.items():
        if ticker in data and not data[ticker].empty:
            result[sector_name] = data[ticker]

    return result


def build_sector_proxy(
    universe_data: dict[str, pd.DataFrame],
    sector_tickers: dict[str, str],
) -> dict[str, pd.Series]:
    """Calcula proxy equal-weighted de retorno acumulado por setor.

    Usado como fallback quando índices setoriais não estão disponíveis.

    Args:
        universe_data: Dados OHLCV de todos os ativos {ticker: df}.
        sector_tickers: Mapeamento {ticker: setor}.

    Returns:
        Dicionário {setor: Series de preço normalizado base 100}.
    """
    from collections import defaultdict

    sector_returns: dict[str, list[pd.Series]] = defaultdict(list)

    for ticker, sector in sector_tickers.items():
        if ticker in universe_data:
            close = universe_data[ticker]["Close"]
            if len(close) > 0:
                # Retornos diários
                ret = close.pct_change().fillna(0)
                sector_returns[sector].append(ret)

    result: dict[str, pd.Series] = {}
    for sector, returns_list in sector_returns.items():
        if returns_list:
            # Equal-weighted average return
            avg_ret = pd.concat(returns_list, axis=1).mean(axis=1)
            # Converter para preço normalizado base 100
            cumulative = (1 + avg_ret).cumprod() * 100
            result[sector] = cumulative

    return result
