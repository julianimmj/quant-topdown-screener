"""
charts.py — Gráficos interativos em Plotly para Deep Dive Individual.

Renderiza:
- Gráfico de Candles + EMAs (9, 21, 50, 200) com Volume
- Subplot de Força Relativa vs. IBOV com média móvel
- Subplot de ADX + DI
- RSI
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from engine.trend import TrendResult


def render_deep_dive_chart(
    ticker: str,
    df: pd.DataFrame,
    trend: TrendResult,
    benchmark_close: pd.Series | None = None,
    lookback_days: int = 252,
) -> None:
    """Renderiza gráfico completo de Deep Dive para um ativo.

    Layout:
    - Row 1: Candlestick + EMAs (height 60%)
    - Row 2: Volume (height 10%)
    - Row 3: RS vs IBOV (height 15%)
    - Row 4: ADX + DI (height 15%)

    Args:
        ticker: Ticker do ativo.
        df: DataFrame OHLCV do ativo.
        trend: TrendResult com séries de EMAs e ADX.
        benchmark_close: Série Close do benchmark para RS.
        lookback_days: Dias para exibição (padrão 252 = 1 ano).
    """
    # Limitar período de exibição
    df_plot = df.tail(lookback_days).copy()

    has_rs = benchmark_close is not None and len(benchmark_close) > 50
    n_rows = 4 if has_rs else 3
    row_heights = [0.55, 0.10, 0.15, 0.20] if has_rs else [0.60, 0.12, 0.28]

    subplot_titles = [
        f"{ticker} — Preço & Médias Móveis",
        "Volume",
    ]
    if has_rs:
        subplot_titles.append("Força Relativa vs. IBOV")
    subplot_titles.append("ADX & Direcionalidade")

    fig = make_subplots(
        rows=n_rows,
        cols=1,
        shared_xaxes=True,
        vertical_spacing=0.03,
        row_heights=row_heights,
        subplot_titles=subplot_titles,
    )

    # ── Row 1: Candlestick + EMAs ──
    fig.add_trace(
        go.Candlestick(
            x=df_plot.index,
            open=df_plot["Open"],
            high=df_plot["High"],
            low=df_plot["Low"],
            close=df_plot["Close"],
            name="OHLC",
            increasing_line_color="#00D4AA",
            decreasing_line_color="#FF4444",
            increasing_fillcolor="#00D4AA",
            decreasing_fillcolor="#FF4444",
        ),
        row=1,
        col=1,
    )

    # EMAs
    ema_configs = [
        (trend.ema9, "EMA 9", "#FF6B6B", 1),
        (trend.ema21, "EMA 21", "#FFD93D", 1.2),
        (trend.ema50, "EMA 50", "#6BCB77", 1.5),
        (trend.sma200, "SMA 200", "#4D96FF", 2),
    ]

    for ema_series, name, color, width in ema_configs:
        if ema_series is not None:
            ema_plot = ema_series.reindex(df_plot.index)
            fig.add_trace(
                go.Scatter(
                    x=df_plot.index,
                    y=ema_plot,
                    name=name,
                    line=dict(color=color, width=width),
                    opacity=0.85,
                ),
                row=1,
                col=1,
            )

    # ── Row 2: Volume ──
    colors_vol = [
        "#00D4AA" if df_plot["Close"].iloc[i] >= df_plot["Open"].iloc[i] else "#FF4444"
        for i in range(len(df_plot))
    ]

    fig.add_trace(
        go.Bar(
            x=df_plot.index,
            y=df_plot["Volume"],
            name="Volume",
            marker_color=colors_vol,
            opacity=0.6,
            showlegend=False,
        ),
        row=2,
        col=1,
    )

    current_row = 3

    # ── Row 3: Força Relativa vs IBOV ──
    if has_rs:
        bench_aligned = benchmark_close.reindex(df_plot.index)
        rs_ratio = df_plot["Close"] / bench_aligned
        rs_ratio = rs_ratio.dropna()
        rs_ratio = rs_ratio / rs_ratio.iloc[0] * 100  # Base 100

        rs_sma50 = rs_ratio.rolling(50).mean()

        fig.add_trace(
            go.Scatter(
                x=rs_ratio.index,
                y=rs_ratio,
                name="RS Ratio",
                line=dict(color="#00D4AA", width=2),
            ),
            row=current_row,
            col=1,
        )
        fig.add_trace(
            go.Scatter(
                x=rs_sma50.index,
                y=rs_sma50,
                name="RS SMA 50",
                line=dict(color="#FFD700", width=1.5, dash="dash"),
            ),
            row=current_row,
            col=1,
        )
        # Linha de referência 100
        fig.add_hline(
            y=100,
            line_dash="dot",
            line_color="#666",
            opacity=0.5,
            row=current_row,
            col=1,
        )
        current_row += 1

    # ── Row N: ADX + DI ──
    if trend.adx_series is not None:
        adx_plot = trend.adx_series.reindex(df_plot.index)
        fig.add_trace(
            go.Scatter(
                x=df_plot.index,
                y=adx_plot,
                name="ADX",
                line=dict(color="#FFFFFF", width=2),
            ),
            row=current_row,
            col=1,
        )

    if trend.plus_di_series is not None:
        pdi_plot = trend.plus_di_series.reindex(df_plot.index)
        fig.add_trace(
            go.Scatter(
                x=df_plot.index,
                y=pdi_plot,
                name="+DI",
                line=dict(color="#00D4AA", width=1.2),
            ),
            row=current_row,
            col=1,
        )

    if trend.minus_di_series is not None:
        mdi_plot = trend.minus_di_series.reindex(df_plot.index)
        fig.add_trace(
            go.Scatter(
                x=df_plot.index,
                y=mdi_plot,
                name="−DI",
                line=dict(color="#FF4444", width=1.2),
            ),
            row=current_row,
            col=1,
        )

    # Linha de referência ADX = 25
    fig.add_hline(
        y=25,
        line_dash="dash",
        line_color="#FFD700",
        opacity=0.4,
        row=current_row,
        col=1,
        annotation_text="ADX 25",
    )

    # ── Layout Global ──
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=800,
        margin=dict(l=60, r=30, t=40, b=40),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
            font=dict(size=10),
        ),
        xaxis_rangeslider_visible=False,
    )

    # Estilo dos eixos
    for i in range(1, n_rows + 1):
        fig.update_yaxes(
            gridcolor="rgba(26, 29, 35, 0.5)",
            zerolinecolor="#333",
            row=i,
            col=1,
        )
        fig.update_xaxes(
            gridcolor="rgba(26, 29, 35, 0.13)",
            row=i,
            col=1,
        )

    st.plotly_chart(fig, use_container_width=True, key=f"deepdive_{ticker}")


def render_rsi_chart(
    ticker: str,
    df: pd.DataFrame,
    lookback_days: int = 252,
) -> None:
    """Renderiza gráfico de RSI isolado.

    Args:
        ticker: Ticker do ativo.
        df: DataFrame OHLCV.
        lookback_days: Dias para exibição.
    """
    from engine.scoring import compute_rsi

    df_plot = df.tail(lookback_days).copy()
    rsi = compute_rsi(df_plot["Close"], period=14)

    fig = go.Figure()

    # Colorir RSI por zona
    fig.add_trace(go.Scatter(
        x=df_plot.index,
        y=rsi,
        name="RSI(14)",
        line=dict(color="#7C83FD", width=2),
        fill="tozeroy",
        fillcolor="rgba(124, 131, 253, 0.08)",
    ))

    # Zonas
    fig.add_hline(y=70, line_dash="dash", line_color="#FF4444", opacity=0.5,
                  annotation_text="Sobrecomprado (70)")
    fig.add_hline(y=30, line_dash="dash", line_color="#00D4AA", opacity=0.5,
                  annotation_text="Sobrevendido (30)")
    fig.add_hline(y=50, line_dash="dot", line_color="#666", opacity=0.3)

    # Região overbought
    fig.add_hrect(y0=70, y1=100, fillcolor="rgba(255, 68, 68, 0.06)", line_width=0)
    fig.add_hrect(y0=0, y1=30, fillcolor="rgba(0, 212, 170, 0.06)", line_width=0)

    fig.update_layout(
        title=f"RSI(14) — {ticker}",
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=250,
        margin=dict(l=60, r=30, t=40, b=30),
        yaxis=dict(range=[0, 100], title="RSI"),
        xaxis=dict(title=""),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, key=f"rsi_{ticker}")


def render_tqs_distribution(
    scores_df: pd.DataFrame,
) -> None:
    """Renderiza distribuição dos TQS de todo o universo.

    Args:
        scores_df: DataFrame com coluna 'TQS'.
    """
    if "TQS" not in scores_df.columns or scores_df.empty:
        return

    fig = go.Figure()

    fig.add_trace(go.Histogram(
        x=scores_df["TQS"],
        nbinsx=20,
        marker_color="#00D4AA",
        opacity=0.7,
        name="Distribuição TQS",
    ))

    # Média e mediana
    mean_tqs = scores_df["TQS"].mean()
    median_tqs = scores_df["TQS"].median()

    fig.add_vline(x=mean_tqs, line_dash="dash", line_color="#FFD700",
                  annotation_text=f"Média: {mean_tqs:.1f}")
    fig.add_vline(x=median_tqs, line_dash="dot", line_color="#FF6B6B",
                  annotation_text=f"Mediana: {median_tqs:.1f}")

    fig.update_layout(
        title="Distribuição dos Trend Quality Scores",
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=300,
        margin=dict(l=60, r=30, t=50, b=40),
        xaxis=dict(title="TQS", range=[0, 100]),
        yaxis=dict(title="Nº de Ativos"),
        showlegend=False,
    )

    st.plotly_chart(fig, use_container_width=True, key="tqs_distribution")
