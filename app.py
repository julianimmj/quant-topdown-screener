"""
app.py — Entry Point do Quant Top-Down Screener.

Aplicação Streamlit que implementa um Screener de Ações Top-Down
Quant-Mental, filtrando e ranqueando ativos líquidos da B3 através
de um pipeline de 4 camadas hierárquicas:

1. Regime Macro & Amplitude (Market Breadth)
2. Força Relativa Setorial (Sector RS)
3. Qualidade de Tendência & Persistência (Trend Engine)
4. Filtro Anti-Exaustão & Gatilho de Entrada (Trigger)

Executar: streamlit run app.py
"""

from __future__ import annotations

import streamlit as st
import pandas as pd
import numpy as np

# ── Page Config ──
st.set_page_config(
    page_title="Quant Top-Down Screener | B3",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ──
st.markdown("""
<style>
    /* Remove padding do topo */
    .block-container { padding-top: 1.5rem; }

    /* Header styling */
    h1 { color: #00D4AA !important; font-weight: 800 !important; }
    h2, h3 { color: #E0E0E0 !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #1a1d23 0%, #222730 100%);
        border: 1px solid #333;
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] {
        color: #00D4AA !important;
        font-weight: 700 !important;
    }

    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #1a1d2380;
        border-radius: 8px;
        padding: 8px 20px;
        color: #aaa;
    }
    .stTabs [aria-selected="true"] {
        background-color: #00D4AA20 !important;
        color: #00D4AA !important;
        border-bottom: 2px solid #00D4AA;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0E1117 0%, #161B22 100%);
    }

    /* Dataframe */
    .stDataFrame { border-radius: 8px; overflow: hidden; }

    /* Divider */
    hr { border-color: #333 !important; }
</style>
""", unsafe_allow_html=True)

# ── Imports Internos ──
from data.universe import (
    BENCHMARK_TICKER,
    IBOV_UNIVERSE,
    SECTOR_INDICES,
    get_universe,
    get_all_sectors,
)
from data.fetcher import (
    fetch_ohlcv,
    fetch_benchmark,
    build_sector_proxy,
)
from engine.macro import analyze_macro
from engine.sectors import analyze_sectors, get_ticker_sector_score
from engine.trend import batch_analyze_trends
from engine.scoring import (
    DEFAULT_WEIGHTS,
    build_final_scores,
    scores_to_dataframe,
)
from ui.dashboard import (
    render_macro_kpis,
    render_breadth_chart,
    render_ranking_table,
    render_score_decomposition,
    render_sector_heatmap,
)
from ui.charts import (
    render_deep_dive_chart,
    render_rsi_chart,
    render_tqs_distribution,
)


# ══════════════════════════════════════════════════════════════════
#                          SIDEBAR
# ══════════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown("""
    <div style="text-align: center; padding: 15px 0;">
        <h1 style="font-size: 1.6em; margin: 0; color: #00D4AA;">📊 Quant Screener</h1>
        <p style="color: #888; font-size: 0.85em; margin: 5px 0 0 0;">
            Top-Down | Pipeline 4 Níveis
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.divider()

    # Universo
    st.markdown("### 🌐 Universo de Ativos")
    universe_option = st.selectbox(
        "Seleção",
        options=["Ibovespa", "Ibovespa + Small Caps", "Small Caps"],
        index=0,
        key="universe_select",
    )

    universe_map = {
        "Ibovespa": "ibov",
        "Ibovespa + Small Caps": "amplo",
        "Small Caps": "smallcaps",
    }
    selected_universe = universe_map[universe_option]

    # Tickers customizados
    custom_tickers = st.text_area(
        "Tickers customizados (separados por vírgula)",
        placeholder="Ex: PETR4.SA, VALE3.SA, WEGE3.SA",
        key="custom_tickers",
        height=68,
    )

    st.divider()

    # Pesos do TQS
    st.markdown("### ⚖️ Pesos do TQS")
    w_macro = st.slider("Macro", 0.0, 1.0, DEFAULT_WEIGHTS["macro"], 0.05, key="w_macro")
    w_setor = st.slider("Setor RS", 0.0, 1.0, DEFAULT_WEIGHTS["setor"], 0.05, key="w_setor")
    w_trend = st.slider("Trend", 0.0, 1.0, DEFAULT_WEIGHTS["trend"], 0.05, key="w_trend")
    w_trigger = st.slider("Trigger", 0.0, 1.0, DEFAULT_WEIGHTS["trigger"], 0.05, key="w_trigger")

    # Normalizar pesos
    w_total = w_macro + w_setor + w_trend + w_trigger
    if w_total > 0:
        weights = {
            "macro": w_macro / w_total,
            "setor": w_setor / w_total,
            "trend": w_trend / w_total,
            "trigger": w_trigger / w_total,
        }
    else:
        weights = DEFAULT_WEIGHTS

    st.caption(f"Soma normalizada: {w_total:.2f} → 1.00")

    st.divider()

    # Filtros
    st.markdown("### 🔧 Filtros")
    min_tqs = st.slider("TQS mínimo para exibição", 0, 100, 0, 5, key="min_tqs")
    top_n = st.slider("Top N para ranking", 5, 50, 20, 5, key="top_n")

    st.divider()

    # Recalcular
    if st.button("🔄 Recalcular (Limpar Cache)", use_container_width=True, key="recalc"):
        st.cache_data.clear()
        st.rerun()

    st.divider()
    st.caption("Dados: Yahoo Finance | Atualizado a cada hora")
    st.caption("⚠️ Uso educacional — não constitui recomendação de investimento.")


# ══════════════════════════════════════════════════════════════════
#                       PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════

st.markdown("""
# 📊 Quant Top-Down Screener
**Pipeline Hierárquico de 4 Níveis** — Regime Macro → Força Relativa Setorial → Trend Engine → Trigger
""")

# ── 1. Carregar universo ──
universe = get_universe(selected_universe)

# Adicionar tickers customizados
if custom_tickers.strip():
    custom_list = [t.strip().upper() for t in custom_tickers.split(",") if t.strip()]
    for t in custom_list:
        if not t.endswith(".SA"):
            t += ".SA"
        if t not in universe:
            universe[t] = "Customizado"

ticker_list = list(universe.keys())

if not ticker_list:
    st.error("Nenhum ticker selecionado. Selecione um universo na sidebar.")
    st.stop()

# ── 2. Fetch dados ──
with st.spinner(f"📥 Baixando dados de {len(ticker_list)} ativos…"):
    universe_data = fetch_ohlcv(ticker_list, period="2y", interval="1d")
    benchmark_data = fetch_benchmark(BENCHMARK_TICKER, period="2y", interval="1d")

if not universe_data:
    st.error("❌ Não foi possível baixar dados de nenhum ativo. Tente novamente.")
    st.stop()

if benchmark_data.empty:
    st.error("❌ Não foi possível baixar dados do benchmark (IBOV).")
    st.stop()

st.success(f"✅ {len(universe_data)} ativos carregados com sucesso.")

# ── 3. Análise Macro (Nível 1) ──
macro = analyze_macro(universe_data, benchmark_data=benchmark_data)

# ── 4. Análise Setorial (Nível 2) ──
# Construir proxy setorial equal-weighted
sector_prices = build_sector_proxy(universe_data, universe)

# Converter para Series de Close para análise RS
sector_close_series = {name: series for name, series in sector_prices.items()}

sector_analysis = analyze_sectors(sector_close_series, benchmark_data["Close"])

# Mapa de score setorial
sector_score_map = {
    name: sr.score for name, sr in sector_analysis.sectors.items()
}

# ── 5. Trend Engine (Nível 3) ──
trend_results = batch_analyze_trends(universe_data)

# ── 6. Scoring Final ──
final_scores = build_final_scores(
    universe_data=universe_data,
    ticker_sector_map=universe,
    macro_score=macro.score,
    sector_scores=sector_score_map,
    trend_results=trend_results,
    weights=weights,
)

# Aplicar filtro TQS mínimo
if min_tqs > 0:
    final_scores = [s for s in final_scores if s.tqs >= min_tqs]

scores_df = scores_to_dataframe(final_scores)


# ══════════════════════════════════════════════════════════════════
#                            TABS
# ══════════════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs([
    "📋 Overview & Ranking",
    "🔍 Deep Dive Individual",
    "🗺️ Matriz Setorial",
])


# ══════════════════════ TAB 1: OVERVIEW ═══════════════════════════

with tab1:
    # Macro KPIs
    render_macro_kpis(
        regime=macro.regime,
        regime_color=macro.regime_color,
        pct_sma50=macro.pct_above_sma50,
        pct_sma200=macro.pct_above_sma200,
        macro_score=macro.score,
        correlations=macro.correlations,
    )

    # Breadth Chart
    render_breadth_chart(macro.breadth_history_50, macro.breadth_history_200)

    st.divider()

    # Ranking Table
    st.markdown(f"### 🏆 Top {top_n} — Ranking por Trend Quality Score (TQS)")

    if not scores_df.empty:
        # Stats rápidas
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric("Ativos Analisados", len(final_scores))
        with sc2:
            strong_buys = len([s for s in final_scores if s.status == "Compra Forte"])
            st.metric("🟢 Compra Forte", strong_buys)
        with sc3:
            buys = len([s for s in final_scores if s.status == "Compra"])
            st.metric("🟡 Compra", buys)
        with sc4:
            overbought = len([s for s in final_scores if s.status == "Sobrecomprado"])
            st.metric("🔴 Sobrecomprado", overbought)

        render_ranking_table(scores_df, top_n=top_n)

        # Distribuição TQS
        st.divider()
        render_tqs_distribution(scores_df)
    else:
        st.warning("Nenhum ativo atendeu aos critérios de filtro.")


# ══════════════════════ TAB 2: DEEP DIVE ══════════════════════════

with tab2:
    if not final_scores:
        st.info("Execute o screener primeiro (aba Overview).")
    else:
        # Seletor de ativo
        ticker_options = [f"{s.ticker} (TQS: {s.tqs:.1f})" for s in final_scores]
        selected_label = st.selectbox(
            "Selecionar ativo para análise detalhada",
            options=ticker_options,
            index=0,
            key="deepdive_select",
        )

        # Extrair ticker do label
        selected_ticker = selected_label.split(" (")[0]
        selected_score = next((s for s in final_scores if s.ticker == selected_ticker), None)
        selected_trend = trend_results.get(selected_ticker)

        if selected_score and selected_ticker in universe_data:
            col_left, col_right = st.columns([2, 1])

            with col_left:
                # Lookback selector
                lookback = st.select_slider(
                    "Período de visualização",
                    options=[63, 126, 189, 252, 378, 504],
                    value=252,
                    format_func=lambda x: f"{x} dias (~{x // 21} meses)",
                    key="lookback_slider",
                )

                # Chart principal
                if selected_trend:
                    render_deep_dive_chart(
                        ticker=selected_ticker,
                        df=universe_data[selected_ticker],
                        trend=selected_trend,
                        benchmark_close=benchmark_data["Close"],
                        lookback_days=lookback,
                    )

                # RSI Chart
                render_rsi_chart(selected_ticker, universe_data[selected_ticker], lookback_days=lookback)

            with col_right:
                render_score_decomposition(selected_score)
        else:
            st.warning(f"Dados insuficientes para {selected_ticker}.")


# ═══════════════════ TAB 3: MATRIZ SETORIAL ═══════════════════════

with tab3:
    st.markdown("### 🗺️ Matriz de Força Relativa Setorial")
    st.markdown(
        "Dispersão de performance e ranking dos setores da B3 "
        "baseado no RS Ratio vs. Ibovespa."
    )

    render_sector_heatmap(
        sector_analysis=sector_analysis,
        ticker_sector_map=universe,
        scores=final_scores,
    )

    # Top ações por setor
    st.divider()
    st.markdown("### 📊 Melhores Ativos por Setor")

    sectors_with_stocks = {}
    for s in final_scores:
        if s.sector not in sectors_with_stocks:
            sectors_with_stocks[s.sector] = []
        sectors_with_stocks[s.sector].append(s)

    if sectors_with_stocks:
        # Ordenar setores pelo score médio
        sector_order = sorted(
            sectors_with_stocks.keys(),
            key=lambda sec: sector_score_map.get(sec, 0),
            reverse=True,
        )

        for sector_name in sector_order:
            stocks = sectors_with_stocks[sector_name]
            if not stocks:
                continue

            rs_score = sector_score_map.get(sector_name, 0)
            emoji = "🟢" if rs_score >= 60 else "🟡" if rs_score >= 40 else "🔴"

            with st.expander(
                f"{emoji} {sector_name} — RS Score: {rs_score:.0f} | {len(stocks)} ativos",
                expanded=False,
            ):
                sector_df = scores_to_dataframe(sorted(stocks, key=lambda s: s.tqs, reverse=True))
                st.dataframe(sector_df, use_container_width=True, hide_index=True, height=200)
