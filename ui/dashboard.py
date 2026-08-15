"""
dashboard.py — Componentes de UI para o Dashboard principal.

Renderiza:
- Métricas KPI no topo (Regime, Breadth, etc.)
- Tabela interativa Top N com badges coloridos
- Heatmap setorial
- Decomposição de sub-scores
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from engine.scoring import FinalScore


def render_macro_kpis(
    regime: str,
    regime_color: str,
    pct_sma50: float,
    pct_sma200: float,
    macro_score: float,
    correlations: dict[str, float] | None = None,
) -> None:
    """Renderiza KPIs de regime macro no topo da página.

    Args:
        regime: Nome do regime (ex: '🟢 Favorável').
        regime_color: Cor hex do regime.
        pct_sma50: % acima da SMA 50.
        pct_sma200: % acima da SMA 200.
        macro_score: Score macro 0-100.
        correlations: Correlações rolantes (opcional).
    """
    st.markdown(
        f"""
        <div style="
            background: linear-gradient(135deg, #1a1d23 0%, #262b36 100%);
            border: 1px solid {regime_color}40;
            border-radius: 12px;
            padding: 20px 28px;
            margin-bottom: 24px;
        ">
            <h3 style="color: {regime_color}; margin: 0 0 8px 0; font-size: 1.1em;">
                Regime de Mercado
            </h3>
            <p style="color: {regime_color}; font-size: 1.6em; font-weight: 700; margin: 0;">
                {regime}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="📊 Ações > SMA 50",
            value=f"{pct_sma50:.1f}%",
            delta=None,
        )
    with col2:
        st.metric(
            label="📈 Ações > SMA 200",
            value=f"{pct_sma200:.1f}%",
            delta=None,
        )
    with col3:
        st.metric(
            label="🎯 Score Macro",
            value=f"{macro_score:.0f}/100",
            delta=None,
        )

    # Correlações
    if correlations:
        st.markdown("##### Correlações Rolantes (63 dias)")
        corr_cols = st.columns(min(len(correlations), 4))
        for i, (name, val) in enumerate(correlations.items()):
            with corr_cols[i % len(corr_cols)]:
                color = "#00D4AA" if val > 0 else "#FF4444"
                st.markdown(
                    f"""<div style="text-align: center; padding: 8px; background: #1a1d2380;
                    border-radius: 8px; border: 1px solid {color}30;">
                    <span style="color: #888; font-size: 0.8em;">{name}</span><br>
                    <span style="color: {color}; font-size: 1.3em; font-weight: 600;">
                    {val:+.2f}</span></div>""",
                    unsafe_allow_html=True,
                )


def render_breadth_chart(
    breadth_50: pd.Series | None,
    breadth_200: pd.Series | None,
) -> None:
    """Renderiza gráfico histórico de market breadth.

    Args:
        breadth_50: Série % > SMA50.
        breadth_200: Série % > SMA200.
    """
    if breadth_50 is None and breadth_200 is None:
        return

    fig = go.Figure()

    if breadth_50 is not None:
        fig.add_trace(go.Scatter(
            x=breadth_50.index,
            y=breadth_50.values,
            name="% > SMA 50",
            line=dict(color="#00D4AA", width=2),
            fill="tozeroy",
            fillcolor="rgba(0, 212, 170, 0.08)",
        ))

    if breadth_200 is not None:
        fig.add_trace(go.Scatter(
            x=breadth_200.index,
            y=breadth_200.values,
            name="% > SMA 200",
            line=dict(color="#FFD700", width=2),
            fill="tozeroy",
            fillcolor="rgba(255, 215, 0, 0.05)",
        ))

    # Linhas de referência
    fig.add_hline(y=60, line_dash="dash", line_color="#00D4AA", opacity=0.4,
                  annotation_text="Favorável (60%)")
    fig.add_hline(y=40, line_dash="dash", line_color="#FF4444", opacity=0.4,
                  annotation_text="Defensivo (40%)")

    fig.update_layout(
        title="Market Breadth — Amplitude de Mercado",
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=350,
        margin=dict(l=60, r=30, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(title="% do Universo", range=[0, 100]),
        xaxis=dict(title=""),
    )

    st.plotly_chart(fig, use_container_width=True, key="breadth_chart")


def _tqs_color(tqs: float) -> str:
    """Retorna cor hex com base no TQS."""
    if tqs >= 75:
        return "#00D4AA"
    elif tqs >= 55:
        return "#7CFFCB"
    elif tqs >= 40:
        return "#FFD700"
    elif tqs >= 25:
        return "#FF8C00"
    else:
        return "#FF4444"


def render_ranking_table(
    df: pd.DataFrame,
    top_n: int = 20,
) -> None:
    """Renderiza tabela de ranking com estilização.

    Args:
        df: DataFrame com scores (output de scores_to_dataframe).
        top_n: Número de ativos a exibir.
    """
    display_df = df.head(top_n).copy()

    if display_df.empty:
        st.warning("Nenhum ativo encontrado com dados suficientes.")
        return

    # Estilização com cores condicionais
    def color_tqs(val: float) -> str:
        color = _tqs_color(val)
        return f"color: {color}; font-weight: 700;"

    def color_score(val: float) -> str:
        if val >= 60:
            return "color: #00D4AA;"
        elif val >= 40:
            return "color: #FFD700;"
        else:
            return "color: #FF4444;"

    def highlight_row(row: pd.Series) -> list[str]:
        tqs = row.get("TQS", 0)
        if tqs >= 75:
            bg = "background-color: rgba(0, 212, 170, 0.08);"
        elif tqs >= 55:
            bg = "background-color: rgba(124, 255, 203, 0.05);"
        else:
            bg = ""
        return [bg] * len(row)

    styled = (
        display_df.style
        .apply(highlight_row, axis=1)
        .map(color_tqs, subset=["TQS"])
        .map(color_score, subset=["Macro", "Setor RS", "Trend", "Trigger"])
        .format({
            "Preço": "R$ {:.2f}",
            "TQS": "{:.1f}",
            "Macro": "{:.0f}",
            "Setor RS": "{:.0f}",
            "Trend": "{:.0f}",
            "Trigger": "{:.0f}",
            "ADX": "{:.1f}",
            "ER": "{:.2f}",
            "RSI": "{:.1f}",
        })
    )

    st.dataframe(
        styled,
        use_container_width=True,
        height=min(45 * len(display_df) + 50, 800),
        hide_index=True,
    )


def render_score_decomposition(score: FinalScore) -> None:
    """Renderiza decomposição detalhada dos sub-scores de um ativo.

    Args:
        score: FinalScore do ativo selecionado.
    """
    st.markdown(f"### 🔍 Decomposição — {score.ticker}")
    st.markdown(f"**Setor:** {score.sector} | **Preço:** R$ {score.price:.2f}")

    # TQS gauge
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score.tqs,
        domain=dict(x=[0, 1], y=[0, 1]),
        title=dict(text="Trend Quality Score", font=dict(size=16)),
        number=dict(font=dict(size=40, color=_tqs_color(score.tqs))),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#666"),
            bar=dict(color=_tqs_color(score.tqs)),
            bgcolor="#1a1d23",
            borderwidth=2,
            bordercolor="#333",
            steps=[
                dict(range=[0, 25], color="rgba(255, 68, 68, 0.13)"),
                dict(range=[25, 50], color="rgba(255, 215, 0, 0.08)"),
                dict(range=[50, 75], color="rgba(0, 212, 170, 0.08)"),
                dict(range=[75, 100], color="rgba(0, 212, 170, 0.15)"),
            ],
            threshold=dict(line=dict(color="#fff", width=2), thickness=0.75, value=score.tqs),
        ),
    ))
    fig_gauge.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        height=250,
        margin=dict(l=30, r=30, t=30, b=10),
    )
    st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{score.ticker}")

    # Sub-scores em barras horizontais
    categories = ["Macro", "Setor RS", "Trend", "Trigger"]
    values = [score.macro_score, score.sector_score, score.trend_score, score.trigger_score]
    weights = [0.20, 0.20, 0.45, 0.15]
    weighted_vals = [v * w for v, w in zip(values, weights)]
    colors = [_tqs_color(v) for v in values]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=categories,
        x=values,
        orientation="h",
        marker_color=colors,
        text=[f"{v:.0f} (×{w:.0%} = {wv:.1f})" for v, w, wv in zip(values, weights, weighted_vals)],
        textposition="inside",
        textfont=dict(color="white", size=12),
    ))
    fig_bar.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=200,
        margin=dict(l=80, r=30, t=10, b=10),
        xaxis=dict(range=[0, 100], title="Score"),
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True, key=f"bar_{score.ticker}")

    # Detalhamento do Trend Engine
    st.markdown("#### 📐 Trend Engine — Sub-componentes")
    trend_items = {
        "EMA Alignment (0-25)": score.ema_alignment,
        "Slope SMA50 (0-15)": score.slope,
        "ADX & DI (0-20)": score.adx,
        "Kaufman ER (0-20)": score.efficiency_ratio,
        "Vol-Adj ROC (0-20)": score.vol_adj_roc,
    }

    cols = st.columns(len(trend_items))
    for i, (label, val) in enumerate(trend_items.items()):
        max_val = float(label.split("0-")[1].rstrip(")"))
        pct = val / max_val * 100 if max_val > 0 else 0
        color = "#00D4AA" if pct >= 60 else "#FFD700" if pct >= 40 else "#FF4444"
        with cols[i]:
            st.markdown(
                f"""<div style="text-align: center; padding: 10px; background: #1a1d2380;
                border-radius: 8px; border-left: 3px solid {color};">
                <span style="color: #888; font-size: 0.7em;">{label}</span><br>
                <span style="color: {color}; font-size: 1.4em; font-weight: 700;">
                {val:.1f}</span></div>""",
                unsafe_allow_html=True,
            )

    # Trigger info
    if score.trigger:
        st.markdown("#### 🎯 Trigger & Anti-Exaustão")
        t = score.trigger
        tc1, tc2, tc3, tc4 = st.columns(4)
        with tc1:
            st.metric("Dist. da Média (ATRs)", f"{t.distance_from_mean:.2f}")
        with tc2:
            st.metric("RSI(14)", f"{t.rsi_14:.1f}")
        with tc3:
            st.metric("Pullback Zone", "✅ Sim" if t.in_pullback_zone else "❌ Não")
        with tc4:
            st.metric("Status", f"{t.status_emoji} {t.status}")


def render_sector_heatmap(
    sector_analysis: Any,
    ticker_sector_map: dict[str, str],
    scores: list[FinalScore],
) -> None:
    """Renderiza heatmap de performance setorial.

    Args:
        sector_analysis: SectorAnalysis com dados de RS.
        ticker_sector_map: Mapeamento {ticker: setor}.
        scores: Lista de FinalScore.
    """
    if not sector_analysis.sectors:
        st.info("Dados setoriais insuficientes para gerar heatmap.")
        return

    # Dados para heatmap
    sectors_data = []
    for name, sr in sector_analysis.sectors.items():
        # Contar ativos nesse setor
        n_tickers = sum(1 for s in scores if s.sector == name)
        avg_tqs = np.mean([s.tqs for s in scores if s.sector == name]) if n_tickers > 0 else 0

        sectors_data.append({
            "Setor": name,
            "RS Score": round(sr.score, 1),
            "ROC 63d": round(sr.roc_63, 2),
            "ROC 126d": round(sr.roc_126, 2),
            "RS > SMA50": "✅" if sr.rs_above_sma50 else "❌",
            "Quartil": sr.quartile,
            "Ativos": n_tickers,
            "TQS Médio": round(avg_tqs, 1),
        })

    sectors_df = pd.DataFrame(sectors_data).sort_values("RS Score", ascending=False)

    # Tabela
    st.dataframe(sectors_df, use_container_width=True, hide_index=True)

    # Heatmap visual
    if len(sectors_df) > 1:
        fig = px.treemap(
            sectors_df,
            path=["Setor"],
            values="Ativos",
            color="RS Score",
            color_continuous_scale=["#FF4444", "#FFD700", "#00D4AA"],
            color_continuous_midpoint=50,
            title="Mapa de Força Relativa Setorial",
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            height=400,
            margin=dict(l=10, r=10, t=50, b=10),
        )
        fig.update_traces(
            textinfo="label+value+text",
            texttemplate="<b>%{label}</b><br>RS: %{color:.0f}<br>Ativos: %{value}",
        )
        st.plotly_chart(fig, use_container_width=True, key="sector_treemap")
