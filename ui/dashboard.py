"""
dashboard.py — Componentes de UI para o Dashboard principal.

Renderiza:
- Métricas KPI no topo (Regime, Breadth, etc.)
- Tabela de ranking institucional com linhas de tons alternados (Zebra Striping)
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


def st_html(html_str: str) -> None:
    """Renderiza HTML limpando qualquer espaçamento/indentação no início das linhas.
    
    Isso impede que o Markdown do Streamlit confunda tags HTML com blocos de código (<pre><code>).
    """
    clean_lines = [line.strip() for line in html_str.split("\n") if line.strip()]
    clean_content = "".join(clean_lines)
    if hasattr(st, "html"):
        st.html(clean_content)
    else:
        st.markdown(clean_content, unsafe_allow_html=True)


def render_macro_kpis(
    regime: str,
    regime_color: str,
    pct_sma50: float,
    pct_sma200: float,
    macro_score: float,
    correlations: dict[str, float] | None = None,
) -> None:
    """Renderiza KPIs de regime macro no topo da página."""
    st_html(f"""
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
    """)

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
                st_html(f"""
                <div style="text-align: center; padding: 8px; background: #1a1d2380; border-radius: 8px; border: 1px solid {color}30;">
                    <span style="color: #888; font-size: 0.8em;">{name}</span><br>
                    <span style="color: {color}; font-size: 1.2em; font-weight: 700;">{val:+.2f}</span>
                </div>
                """)


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
    """Renderiza tabela de ranking institucional com linhas de tons alternados (Zebra Striping) perfeitas."""
    display_df = df.head(top_n).copy()

    if display_df.empty:
        st.warning("Nenhum ativo encontrado com os parâmetros atuais.")
        return

    # Construção de tabela HTML pura com zebra striping nítido
    rows_html = []
    for i, (_, row) in enumerate(display_df.iterrows()):
        # Alternância nítida de tons escuros institucionais (#111520 e #191F30)
        bg_color = "#111520" if i % 2 == 0 else "#191F30"
        
        tqs = float(row.get("TQS", 0))
        tqs_col = _tqs_color(tqs)
        
        # Borda esquerda destacando os líderes
        left_border = "border-left: 4px solid #00D4AA;" if tqs >= 75 else ("border-left: 4px solid #FFD700;" if tqs >= 60 else "border-left: 4px solid transparent;")

        # Badges de status com cores dinâmicas
        status_str = str(row.get("Status", "⚪ Neutro"))
        if "Compra Forte" in status_str:
            status_badge = '<span style="background: rgba(0, 212, 170, 0.18); color: #00D4AA; border: 1px solid #00D4AA; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; white-space: nowrap;">🟢 Compra Forte</span>'
        elif "Compra" in status_str:
            status_badge = '<span style="background: rgba(255, 215, 0, 0.18); color: #FFD700; border: 1px solid #FFD700; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; white-space: nowrap;">🟡 Compra</span>'
        elif "Sobrecomprado" in status_str:
            status_badge = '<span style="background: rgba(255, 68, 68, 0.18); color: #FF4444; border: 1px solid #FF4444; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; white-space: nowrap;">🔴 Sobrecomprado</span>'
        elif "Pullback" in status_str:
            status_badge = '<span style="background: rgba(255, 140, 0, 0.18); color: #FF8C00; border: 1px solid #FF8C00; padding: 4px 10px; border-radius: 12px; font-weight: 700; font-size: 0.8rem; white-space: nowrap;">🟠 Aguardar Pullback</span>'
        else:
            status_badge = f'<span style="background: rgba(255, 255, 255, 0.06); color: #BBB; border: 1px solid #444; padding: 4px 10px; border-radius: 12px; font-size: 0.8rem; white-space: nowrap;">{status_str}</span>'

        # Helper para colorir números de sub-score
        def num_color(val):
            try:
                v = float(val)
                if v >= 65: return f'<span style="color: #00D4AA; font-weight: 700;">{v:.0f}</span>'
                elif v >= 45: return f'<span style="color: #FFD700; font-weight: 600;">{v:.0f}</span>'
                else: return f'<span style="color: #FF6B6B;">{v:.0f}</span>'
            except Exception:
                return str(val)

        # Rank badge
        rank_val = row.get("Rank", i + 1)
        if rank_val == 1:
            rank_html = '<span style="background: #FFD700; color: #000; font-weight: 800; padding: 2px 7px; border-radius: 50%; font-size: 0.8rem;">1</span>'
        elif rank_val == 2:
            rank_html = '<span style="background: #E0E0E0; color: #000; font-weight: 800; padding: 2px 7px; border-radius: 50%; font-size: 0.8rem;">2</span>'
        elif rank_val == 3:
            rank_html = '<span style="background: #CD7F32; color: #000; font-weight: 800; padding: 2px 7px; border-radius: 50%; font-size: 0.8rem;">3</span>'
        else:
            rank_html = f'<span style="color: #8892B0; font-weight: 600;">{rank_val}</span>'

        price_val = f"R$ {float(row.get('Preço', 0)):.2f}" if "Preço" in row else "-"
        adx_val = f"{float(row.get('ADX', 0)):.1f}" if "ADX" in row else "-"
        er_val = f"{float(row.get('ER', 0)):.2f}" if "ER" in row else "-"
        rsi_val = f"{float(row.get('RSI', 0)):.1f}" if "RSI" in row else "-"

        row_html = f"""
        <tr style="background-color: {bg_color}; {left_border}">
            <td style="padding: 11px 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">{rank_html}</td>
            <td style="padding: 11px 10px; font-weight: 800; color: #00D4AA; border-bottom: 1px solid rgba(255,255,255,0.04);">{row.get('Ticker', '')}</td>
            <td style="padding: 11px 10px; color: #CCD6F6; font-size: 0.85rem; border-bottom: 1px solid rgba(255,255,255,0.04);">{row.get('Setor', '')}</td>
            <td style="padding: 11px 10px; color: #E0E6ED; font-weight: 600; text-align: right; border-bottom: 1px solid rgba(255,255,255,0.04);">{price_val}</td>
            <td style="padding: 11px 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">
                <span style="background: rgba(0, 212, 170, 0.15); color: {tqs_col}; border: 1px solid {tqs_col}; padding: 3px 10px; border-radius: 6px; font-weight: 800; font-size: 0.95rem;">
                    {tqs:.1f}
                </span>
            </td>
            <td style="padding: 11px 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">{num_color(row.get('Macro', 0))}</td>
            <td style="padding: 11px 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">{num_color(row.get('Setor RS', 0))}</td>
            <td style="padding: 11px 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">{num_color(row.get('Trend', 0))}</td>
            <td style="padding: 11px 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">{num_color(row.get('Trigger', 0))}</td>
            <td style="padding: 11px 8px; text-align: right; color: #CCD6F6; border-bottom: 1px solid rgba(255,255,255,0.04);">{adx_val}</td>
            <td style="padding: 11px 8px; text-align: right; color: #CCD6F6; border-bottom: 1px solid rgba(255,255,255,0.04);">{er_val}</td>
            <td style="padding: 11px 8px; text-align: right; color: #CCD6F6; border-bottom: 1px solid rgba(255,255,255,0.04);">{rsi_val}</td>
            <td style="padding: 11px 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">{status_badge}</td>
        </tr>
        """
        rows_html.append(row_html)

    table_html = f"""
    <div style="overflow-x: auto; border: 1px solid #232936; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-top: 10px; margin-bottom: 20px;">
        <table style="width: 100%; border-collapse: collapse; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 0.88rem;">
            <thead>
                <tr style="background-color: #1A2030; border-bottom: 2px solid #00D4AA; color: #8892B0; text-transform: uppercase; font-size: 0.76rem; letter-spacing: 0.8px;">
                    <th style="padding: 12px 8px; text-align: center;">Rank</th>
                    <th style="padding: 12px 10px; text-align: left;">Ticker</th>
                    <th style="padding: 12px 10px; text-align: left;">Setor</th>
                    <th style="padding: 12px 10px; text-align: right;">Preço</th>
                    <th style="padding: 12px 10px; text-align: center; color: #00D4AA;">TQS Score</th>
                    <th style="padding: 12px 8px; text-align: center;">Macro</th>
                    <th style="padding: 12px 8px; text-align: center;">Setor RS</th>
                    <th style="padding: 12px 8px; text-align: center;">Trend</th>
                    <th style="padding: 12px 8px; text-align: center;">Trigger</th>
                    <th style="padding: 12px 8px; text-align: right;">ADX</th>
                    <th style="padding: 12px 8px; text-align: right;">ER</th>
                    <th style="padding: 12px 8px; text-align: right;">RSI</th>
                    <th style="padding: 12px 10px; text-align: center;">Recomendação</th>
                </tr>
            </thead>
            <tbody>
                {''.join(rows_html)}
            </tbody>
        </table>
    </div>
    """

    st_html(table_html)


def render_score_decomposition(score: FinalScore) -> None:
    """Renderiza decomposição detalhada dos sub-scores de um ativo com layout responsivo e fontes balanceadas."""
    st.markdown(f"### 🔍 Decomposição Quantitativa — `{score.ticker}`")
    st.markdown(f"**Setor Econômico:** {score.sector} | **Último Fechamento:** R$ {score.price:.2f}")

    # TQS gauge perfeitamente centralizado
    fig_gauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score.tqs,
        domain=dict(x=[0.05, 0.95], y=[0.0, 1.0]),
        title=dict(
            text="<b>Trend Quality Score (TQS)</b>",
            font=dict(size=15, color="#8892B0"),
            align="center",
        ),
        number=dict(
            font=dict(size=38, color=_tqs_color(score.tqs), family="Arial Black, sans-serif"),
        ),
        gauge=dict(
            axis=dict(
                range=[0, 100],
                tickwidth=1,
                tickcolor="#8892B0",
                tickvals=[0, 25, 50, 75, 100],
                ticktext=["0", "25", "50", "75", "100"],
            ),
            bar=dict(color=_tqs_color(score.tqs), thickness=0.28),
            bgcolor="#151922",
            borderwidth=2,
            bordercolor="#2A303C",
            steps=[
                dict(range=[0, 25], color="rgba(255, 68, 68, 0.15)"),
                dict(range=[25, 50], color="rgba(255, 215, 0, 0.10)"),
                dict(range=[50, 75], color="rgba(0, 212, 170, 0.10)"),
                dict(range=[75, 100], color="rgba(0, 212, 170, 0.20)"),
            ],
            threshold=dict(line=dict(color="#FFFFFF", width=3), thickness=0.8, value=score.tqs),
        ),
    ))
    fig_gauge.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        height=220,
        margin=dict(l=25, r=25, t=35, b=15),
    )
    st.plotly_chart(fig_gauge, use_container_width=True, key=f"gauge_{score.ticker}")

    # Sub-scores em barras horizontais perfeitamente alinhadas e centralizadas
    categories = ["Trigger", "Trend", "Setor RS", "Macro"]
    values = [score.trigger_score, score.trend_score, score.sector_score, score.macro_score]
    weights = [0.15, 0.45, 0.20, 0.20]
    weighted_vals = [v * w for v, w in zip(values, weights)]
    colors = [_tqs_color(v) for v in values]

    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(
        y=categories,
        x=values,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(color="rgba(255,255,255,0.15)", width=1),
        ),
        text=[f"<b>{v:.0f} pts</b> (×{w:.0%} = {wv:.1f})" for v, w, wv in zip(values, weights, weighted_vals)],
        textposition="auto",
        insidetextanchor="middle",
        textfont=dict(color="white", size=11, family="sans-serif"),
    ))
    fig_bar.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0E1117",
        plot_bgcolor="#0E1117",
        height=195,
        margin=dict(l=75, r=25, t=10, b=25),
        xaxis=dict(
            range=[0, 100],
            dtick=25,
            gridcolor="rgba(255,255,255,0.06)",
            title=dict(text="Escala de Pontuação (0 - 100)", font=dict(size=11, color="#8892B0")),
        ),
        yaxis=dict(gridcolor="transparent"),
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
            st_html(f"""
            <div style="text-align: center; padding: 8px 4px; background: #151922; border-radius: 8px; border-left: 3px solid {color}; margin-bottom: 8px;">
                <span style="color: #8892B0; font-size: 0.7em; display: block; height: 26px; line-height: 13px;">{label}</span>
                <span style="color: {color}; font-size: 1.25em; font-weight: 700;">{val:.1f}</span>
            </div>
            """)

    # Trigger info — Cartões balanceados e legíveis sem truncamento
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

        pullback_txt = "✅ Sim (Zona de Valor)" if t.in_pullback_zone else "❌ Fora da Faixa"
        pullback_col = "#00D4AA" if t.in_pullback_zone else "#8892B0"

        # Grid 2x2 com tamanho de fonte perfeitamente calibrado
        row1_c1, row1_c2 = st.columns(2)
        with row1_c1:
            st_html(f"""
            <div style="background: #151922; border: 1px solid #2A303C; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 8px;">
                <div style="color: #8892B0; font-size: 0.78rem; margin-bottom: 2px;">Dist. Média (ATRs)</div>
                <div style="color: #E0E0E0; font-size: 1.15rem; font-weight: 700;">{t.distance_from_mean:.2f}</div>
            </div>
            """)
        with row1_c2:
            st_html(f"""
            <div style="background: #151922; border: 1px solid #2A303C; border-radius: 8px; padding: 10px; text-align: center; margin-bottom: 8px;">
                <div style="color: #8892B0; font-size: 0.78rem; margin-bottom: 2px;">RSI (14)</div>
                <div style="color: #E0E0E0; font-size: 1.15rem; font-weight: 700;">{t.rsi_14:.1f}</div>
            </div>
            """)

        row2_c1, row2_c2 = st.columns(2)
        with row2_c1:
            st_html(f"""
            <div style="background: #151922; border: 1px solid #2A303C; border-radius: 8px; padding: 10px; text-align: center;">
                <div style="color: #8892B0; font-size: 0.78rem; margin-bottom: 2px;">Pullback Zone</div>
                <div style="color: {pullback_col}; font-size: 0.92rem; font-weight: 700; line-height: 1.3;">{pullback_txt}</div>
            </div>
            """)
        with row2_c2:
            st_html(f"""
            <div style="background: {status_bg}; border: 1px solid {status_color}; border-radius: 8px; padding: 10px; text-align: center;">
                <div style="color: #BBB; font-size: 0.78rem; margin-bottom: 2px;">Recomendação</div>
                <div style="color: {status_color}; font-size: 0.95rem; font-weight: 800; line-height: 1.3;">
                    {t.status_emoji} {t.status}
                </div>
            </div>
            """)


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

    # Tabela setorial dedicada com zebra striping
    sector_rows_html = []
    for i, s in enumerate(sectors_df.to_dict(orient="records")):
        bg_col = "#111520" if i % 2 == 0 else "#191F30"
        rs_val = float(s["RS Score"])
        rs_col = _tqs_color(rs_val)
        border_left = "border-left: 4px solid #00D4AA;" if rs_val >= 60 else ("border-left: 4px solid #FFD700;" if rs_val >= 40 else "border-left: 4px solid #FF4444;")

        q_badge = f'<span style="background: rgba(0, 212, 170, 0.15); color: #00D4AA; padding: 2px 8px; border-radius: 6px; font-weight: 700;">{s["Quartil"]}</span>' if "Q1" in str(s["Quartil"]) else f'<span style="color: #BBB;">{s["Quartil"]}</span>'
        sma_badge = '<span style="color: #00D4AA; font-weight: 700;">✅ Sim</span>' if "✅" in str(s["RS > SMA50"]) else '<span style="color: #FF6B6B;">❌ Não</span>'

        row_h = f"""
        <tr style="background-color: {bg_col}; {border_left}">
            <td style="padding: 10px 8px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04); font-weight: 700; color: #8892B0;">{i + 1}</td>
            <td style="padding: 10px 12px; font-weight: 800; color: #FFFFFF; border-bottom: 1px solid rgba(255,255,255,0.04);">{s["Setor"]}</td>
            <td style="padding: 10px 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">
                <span style="background: rgba(0, 212, 170, 0.15); color: {rs_col}; border: 1px solid {rs_col}; padding: 3px 10px; border-radius: 6px; font-weight: 800;">
                    {rs_val:.1f}
                </span>
            </td>
            <td style="padding: 10px 10px; text-align: right; color: {'#00D4AA' if s['ROC 63d'] > 0 else '#FF6B6B'}; font-weight: 600; border-bottom: 1px solid rgba(255,255,255,0.04);">{s['ROC 63d']:+.1f}%</td>
            <td style="padding: 10px 10px; text-align: right; color: {'#00D4AA' if s['ROC 126d'] > 0 else '#FF6B6B'}; font-weight: 600; border-bottom: 1px solid rgba(255,255,255,0.04);">{s['ROC 126d']:+.1f}%</td>
            <td style="padding: 10px 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">{sma_badge}</td>
            <td style="padding: 10px 10px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.04);">{q_badge}</td>
            <td style="padding: 10px 10px; text-align: center; color: #CCD6F6; border-bottom: 1px solid rgba(255,255,255,0.04);">{s["Ativos"]}</td>
            <td style="padding: 10px 10px; text-align: center; color: #00D4AA; font-weight: 700; border-bottom: 1px solid rgba(255,255,255,0.04);">{s["TQS Médio"]:.1f}</td>
        </tr>
        """
        sector_rows_html.append(row_h)

    sec_table_html = f"""
    <div style="overflow-x: auto; border: 1px solid #232936; border-radius: 10px; box-shadow: 0 4px 15px rgba(0,0,0,0.3); margin-top: 10px; margin-bottom: 20px;">
        <table style="width: 100%; border-collapse: collapse; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; font-size: 0.88rem;">
            <thead>
                <tr style="background-color: #1A2030; border-bottom: 2px solid #00D4AA; color: #8892B0; text-transform: uppercase; font-size: 0.76rem; letter-spacing: 0.8px;">
                    <th style="padding: 12px 8px; text-align: center;">Rank</th>
                    <th style="padding: 12px 12px; text-align: left;">Setor Econômico</th>
                    <th style="padding: 12px 10px; text-align: center; color: #00D4AA;">RS Score</th>
                    <th style="padding: 12px 10px; text-align: right;">ROC 63d</th>
                    <th style="padding: 12px 10px; text-align: right;">ROC 126d</th>
                    <th style="padding: 12px 10px; text-align: center;">RS > SMA 50</th>
                    <th style="padding: 12px 10px; text-align: center;">Quartil</th>
                    <th style="padding: 12px 10px; text-align: center;">Nº Ativos</th>
                    <th style="padding: 12px 10px; text-align: center;">TQS Médio</th>
                </tr>
            </thead>
            <tbody>
                {''.join(sector_rows_html)}
            </tbody>
        </table>
    </div>
    """

    st_html(sec_table_html)

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
