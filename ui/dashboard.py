"""
dashboard.py — Componentes de UI para o Dashboard principal.

Renderiza:
- Métricas KPI no topo (Regime, Breadth, etc.)
- Tabela interativa Top N com zebra striping e badges coloridos
- Heatmap setorial
- Decomposição de sub-scores responsiva
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
            background: linear-gradient(135deg, #131720 0%, #1e2430 100%);
            border: 1px solid {regime_color}50;
            border-radius: 12px;
            padding: 18px 24px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.3);
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
                <div>
                    <span style="color: #8892B0; font-size: 0.85em; text-transform: uppercase; letter-spacing: 1px; font-weight: 600;">
                        Nível 1 • Regime Macro de Mercado
                    </span>
                    <h2 style="color: {regime_color}; margin: 4px 0 0 0; font-size: 1.6em; font-weight: 800;">
                        {regime}
                    </h2>
                </div>
                <div style="background: {regime_color}18; border: 1px solid {regime_color}40; border-radius: 8px; padding: 6px 14px; text-align: right;">
                    <span style="color: #AAA; font-size: 0.75em; display: block;">SCORE MACRO</span>
                    <span style="color: {regime_color}; font-size: 1.4em; font-weight: 800;">{macro_score:.0f}/100</span>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            label="📊 Amplitude Curto Prazo (> SMA 50)",
            value=f"{pct_sma50:.1f}%",
            help="Percentual de todos os ativos do universo monitorado cotados acima da Média Móvel Simples de 50 períodos.",
        )
    with col2:
        st.metric(
            label="📈 Amplitude Longo Prazo (> SMA 200)",
            value=f"{pct_sma200:.1f}%",
            help="Percentual de ativos cotados acima da SMA 200. Base do filtro eliminatório de regime institucional (>60% Risk-on, <40% Defensivo).",
        )
    with col3:
        status_txt = "Risk-On (Expansão)" if pct_sma200 >= 60 else ("Neutro" if pct_sma200 >= 40 else "Risk-Off (Defensivo)")
        st.metric(
            label="🧭 Condição Estrutural",
            value=status_txt,
            help="Classificação algorítmica da postura operacional sugerida para estratégias direcionais.",
        )

    # Correlações
    if correlations:
        st.markdown("##### 🔗 Correlações Rolantes (63 dias)")
        corr_cols = st.columns(min(len(correlations), 4))
        for i, (name, val) in enumerate(correlations.items()):
            with corr_cols[i % len(corr_cols)]:
                color = "#00D4AA" if val > 0 else "#FF4444"
                st.markdown(
                    f"""<div style="text-align: center; padding: 8px; background: #1a1d2380;
                    border-radius: 8px; border: 1px solid {color}30;">
                    <span style="color: #888; font-size: 0.8em;">{name}</span><br>
                    <span style="color: {color}; font-size: 1.2em; font-weight: 700;">
                    {val:+.2f}</span></div>""",
                    unsafe_allow_html=True,
                )


def render_breadth_chart(
    breadth_50: pd.Series | None,
    breadth_200: pd.Series | None,
) -> None:
    """Renderiza gráfico histórico de market breadth."""
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
    fig.add_hline(y=60, line_dash="dash", line_color="#00D4AA", opacity=0.5,
                  annotation_text="Favorável (60%)", annotation_position="top left")
    fig.add_hline(y=40, line_dash="dash", line_color="#FF4444", opacity=0.5,
                  annotation_text="Defensivo (40%)", annotation_position="bottom left")

    fig.update_layout(
        title="Histórico de Amplitude de Mercado (Market Breadth)",
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=320,
        margin=dict(l=50, r=20, t=50, b=30),
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
    """Renderiza tabela de ranking com linhas de tons alternados (Zebra Striping) e cores institucionais.

    Args:
        df: DataFrame com scores formatados.
        top_n: Número de ativos a exibir.
    """
    display_df = df.head(top_n).copy()

    if display_df.empty:
        st.warning("Nenhum ativo encontrado com os parâmetros atuais.")
        return

    # Formatação de cores de texto
    def color_tqs(val: float) -> str:
        color = _tqs_color(val)
        return f"color: {color}; font-weight: 800;"

    def color_score(val: float) -> str:
        if val >= 65:
            return "color: #00D4AA; font-weight: 600;"
        elif val >= 45:
            return "color: #FFD700; font-weight: 600;"
        else:
            return "color: #FF6B6B;"

    # Zebra striping profissional com tons alternados escuros
    def style_zebra_and_rank(data: pd.DataFrame) -> pd.DataFrame:
        styles = pd.DataFrame("", index=data.index, columns=data.columns)
        for i, row_idx in enumerate(data.index):
            # Alternância de tons de fundo
            if i % 2 == 0:
                bg = "background-color: #121620;"
            else:
                bg = "background-color: #1A202C;"

            # Destaque de borda para top performers
            tqs_val = data.loc[row_idx, "TQS"] if "TQS" in data.columns else 0
            if tqs_val >= 75:
                bg += " border-left: 3px solid #00D4AA;"
            elif tqs_val >= 60:
                bg += " border-left: 3px solid #FFD700;"

            styles.loc[row_idx, :] = bg
        return styles

    styled = (
        display_df.style
        .apply(style_zebra_and_rank, axis=None)
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
        height=min(42 * len(display_df) + 45, 900),
        hide_index=True,
    )


def render_score_decomposition(score: FinalScore) -> None:
    """Renderiza decomposição detalhada dos sub-scores de um ativo com layout responsivo.

    Args:
        score: FinalScore do ativo selecionado.
    """
    st.markdown(f"### 🔍 Decomposição Quantitativa — `{score.ticker}`")
    st.markdown(f"**Setor Econômico:** {score.sector} | **Último Fechamento:** R$ {score.price:.2f}")

    # TQS gauge
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score.tqs,
        domain=dict(x=[0, 1], y=[0, 1]),
        title=dict(text="Trend Quality Score (TQS)", font=dict(size=15, color="#AAA")),
        number=dict(font=dict(size=38, color=_tqs_color(score.tqs))),
        gauge=dict(
            axis=dict(range=[0, 100], tickwidth=1, tickcolor="#666"),
            bar=dict(color=_tqs_color(score.tqs)),
            bgcolor="#151922",
            borderwidth=2,
            bordercolor="#2A303C",
            steps=[
                dict(range=[0, 25], color="rgba(255, 68, 68, 0.13)"),
                dict(range=[25, 50], color="rgba(255, 215, 0, 0.08)"),
                dict(range=[50, 75], color="rgba(0, 212, 170, 0.08)"),
                dict(range=[75, 100], color="rgba(0, 212, 170, 0.15)"),
            ],
            threshold=dict(line=dict(color="#FFF", width=2), thickness=0.75, value=score.tqs),
        ),
    ))
    fig_gauge.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        height=230,
        margin=dict(l=25, r=25, t=25, b=10),
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
        text=[f"{v:.0f} pts (×{w:.0%} = {wv:.1f})" for v, w, wv in zip(values, weights, weighted_vals)],
        textposition="inside",
        textfont=dict(color="white", size=11, family="sans-serif"),
    ))
    fig_bar.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=190,
        margin=dict(l=70, r=20, t=10, b=10),
        xaxis=dict(range=[0, 100], title="Pontuação (0-100)"),
        showlegend=False,
    )
    st.plotly_chart(fig_bar, use_container_width=True, key=f"bar_{score.ticker}")

    # Detalhamento do Trend Engine
    st.markdown("#### 📐 Nível 3 • Trend Engine (Sub-Componentes)")
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
                f"""<div style="text-align: center; padding: 8px 4px; background: #151922;
                border-radius: 8px; border-left: 3px solid {color}; margin-bottom: 8px;">
                <span style="color: #8892B0; font-size: 0.7em; display: block; height: 28px; line-height: 14px;">{label}</span>
                <span style="color: {color}; font-size: 1.3em; font-weight: 700;">
                {val:.1f}</span></div>""",
                unsafe_allow_html=True,
            )

    # Trigger info — Layout customizado sem st.metric para evitar texto cortado
    if score.trigger:
        st.markdown("#### 🎯 Nível 4 • Gatilho de Entrada & Anti-Exaustão")
        t = score.trigger

        # Determinação de cores e badges para o status
        if "Compra Forte" in t.status:
            status_color = "#00D4AA"
            status_bg = "rgba(0, 212, 170, 0.15)"
        elif "Compra" in t.status:
            status_color = "#FFD700"
            status_bg = "rgba(255, 215, 0, 0.15)"
        elif "Sobrecomprado" in t.status:
            status_color = "#FF4444"
            status_bg = "rgba(255, 68, 68, 0.15)"
        elif "Pullback" in t.status:
            status_color = "#FF8C00"
            status_bg = "rgba(255, 140, 0, 0.15)"
        else:
            status_color = "#AAAAAA"
            status_bg = "rgba(255, 255, 255, 0.05)"

        pullback_txt = "✅ Sim (Zona de Valor)" if t.in_pullback_zone else "❌ Não"
        pullback_col = "#00D4AA" if t.in_pullback_zone else "#888888"

        row1_c1, row1_c2 = st.columns(2)
        with row1_c1:
            st.markdown(
                f"""<div style="background: #151922; border: 1px solid #2A303C; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 10px;">
                    <div style="color: #8892B0; font-size: 0.8em; margin-bottom: 2px;">Dist. Média (ATRs)</div>
                    <div style="color: #E0E0E0; font-size: 1.3em; font-weight: 700;">{t.distance_from_mean:.2f}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with row1_c2:
            st.markdown(
                f"""<div style="background: #151922; border: 1px solid #2A303C; border-radius: 8px; padding: 12px; text-align: center; margin-bottom: 10px;">
                    <div style="color: #8892B0; font-size: 0.8em; margin-bottom: 2px;">RSI (14)</div>
                    <div style="color: #E0E0E0; font-size: 1.3em; font-weight: 700;">{t.rsi_14:.1f}</div>
                </div>""",
                unsafe_allow_html=True,
            )

        row2_c1, row2_c2 = st.columns(2)
        with row2_c1:
            st.markdown(
                f"""<div style="background: #151922; border: 1px solid #2A303C; border-radius: 8px; padding: 12px; text-align: center;">
                    <div style="color: #8892B0; font-size: 0.8em; margin-bottom: 2px;">Pullback Zone</div>
                    <div style="color: {pullback_col}; font-size: 1.15em; font-weight: 700;">{pullback_txt}</div>
                </div>""",
                unsafe_allow_html=True,
            )
        with row2_c2:
            st.markdown(
                f"""<div style="background: {status_bg}; border: 1px solid {status_color}; border-radius: 8px; padding: 12px; text-align: center;">
                    <div style="color: #BBB; font-size: 0.8em; margin-bottom: 2px;">Status do Gatilho</div>
                    <div style="color: {status_color}; font-size: 1.15em; font-weight: 800;">
                        {t.status_emoji} {t.status}
                    </div>
                </div>""",
                unsafe_allow_html=True,
            )


def render_sector_heatmap(
    sector_analysis: Any,
    ticker_sector_map: dict[str, str],
    scores: list[FinalScore],
) -> None:
    """Renderiza heatmap de performance setorial."""
    if not sector_analysis.sectors:
        st.info("Dados setoriais insuficientes para gerar heatmap.")
        return

    # Dados para heatmap
    sectors_data = []
    for name, sr in sector_analysis.sectors.items():
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
            title="Distribuição & Força Relativa Setorial (RS Score)",
        )
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0E1117",
            height=380,
            margin=dict(l=10, r=10, t=45, b=10),
        )
        fig.update_traces(
            textinfo="label+value+text",
            texttemplate="<b>%{label}</b><br>RS: %{color:.0f}<br>Ativos: %{value}",
        )
        st.plotly_chart(fig, use_container_width=True, key="sector_treemap")
