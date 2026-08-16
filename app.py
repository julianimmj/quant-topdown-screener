"""
app.py — Entry Point do Quant Top-Down Screener (B3).

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

# ── Custom CSS com Design Institucional & Mobile Responsivo ──
st.markdown("""
<style>
    /* Remove padding excessivo */
    .block-container { 
        padding-top: 1.2rem; 
        padding-bottom: 2rem;
    }

    /* Tipografia e cores principais */
    h1 { color: #00D4AA !important; font-weight: 800 !important; }
    h2, h3 { color: #E0E6ED !important; }

    /* Metric cards refinados */
    [data-testid="stMetric"] {
        background: linear-gradient(135deg, #131720 0%, #1c222e 100%);
        border: 1px solid #283040;
        border-radius: 10px;
        padding: 12px 16px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.2);
    }
    [data-testid="stMetricValue"] {
        color: #00D4AA !important;
        font-weight: 800 !important;
        font-size: 1.5rem !important;
    }
    [data-testid="stMetricLabel"] {
        color: #8892B0 !important;
        font-weight: 600 !important;
    }

    /* Tabs styling com suporte a scroll horizontal no mobile */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        overflow-x: auto;
        flex-wrap: nowrap;
        -webkit-overflow-scrolling: touch;
        scrollbar-width: none;
    }
    .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
        display: none;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #151922;
        border-radius: 8px;
        padding: 8px 18px;
        color: #8892B0;
        font-weight: 600;
        border: 1px solid #232936;
        white-space: nowrap;
        flex-shrink: 0;
    }
    .stTabs [aria-selected="true"] {
        background-color: rgba(0, 212, 170, 0.12) !important;
        color: #00D4AA !important;
        border: 1px solid #00D4AA !important;
    }

    /* Sidebar institucional */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0B0E14 0%, #121620 100%);
        border-right: 1px solid #1E2433;
    }

    /* Expander styling */
    .streamlit-expanderHeader {
        background-color: #151922 !important;
        border-radius: 6px !important;
        font-size: 0.9em !important;
        color: #CCD6F6 !important;
    }

    /* Dataframe container */
    .stDataFrame { 
        border-radius: 10px; 
        overflow: hidden; 
        border: 1px solid #232936;
    }

    /* Divider */
    hr { border-color: #232936 !important; margin: 1.2rem 0 !important; }

    /* ── Otimização Completa para Mobile & Telas Pequenas (<= 768px) ── */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0.6rem !important;
            padding-bottom: 1.5rem !important;
        }
        h1 { font-size: 1.4rem !important; margin-bottom: 0.3rem !important; }
        h2 { font-size: 1.2rem !important; }
        h3 { font-size: 1.05rem !important; }
        h4 { font-size: 0.95rem !important; }

        /* Ajuste de métricas no mobile */
        [data-testid="stMetric"] {
            padding: 8px 12px !important;
            margin-bottom: 6px !important;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
        }
        [data-testid="stMetricLabel"] {
            font-size: 0.78rem !important;
        }

        /* Tabs mais compactas e fáceis de tocar */
        .stTabs [data-baseweb="tab"] {
            padding: 6px 12px !important;
            font-size: 0.82rem !important;
        }

        /* Gráficos Plotly em tela cheia suave */
        .js-plotly-plot .plotly .modebar {
            transform: scale(0.85);
            transform-origin: top right;
        }

        /* Espaçamento de colunas nativas */
        [data-testid="stHorizontalBlock"] {
            gap: 8px !important;
        }
    }

    /* ── Mobile Ultra-Compact (<= 480px) ── */
    @media (max-width: 480px) {
        h1 { font-size: 1.25rem !important; }
        .stTabs [data-baseweb="tab"] {
            padding: 5px 10px !important;
            font-size: 0.76rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# ── Imports Internos ──
from data.universe import (
    BENCHMARK_TICKER,
    IBOV_UNIVERSE,
    SMALL_CAPS,
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
    <div style="text-align: center; padding: 10px 0 15px 0;">
        <h1 style="font-size: 1.5em; margin: 0; color: #00D4AA;">📊 Quant Screener</h1>
        <p style="color: #8892B0; font-size: 0.8em; margin: 4px 0 0 0; font-weight: 500;">
            Pipeline Hierárquico Top-Down • B3
        </p>
    </div>
    """, unsafe_allow_html=True)

    # Expander explicativo sobre o TQS
    with st.expander("💡 O que é o TQS & Metodologia?", expanded=False):
        st.markdown(r"""
        O **Trend Quality Score (TQS: 0 a 100)** sintetiza uma análise quantitativa institucional em 4 camadas:
        
        $$\text{TQS} = w_1\text{Macro} + w_2\text{Setor} + w_3\text{Trend} + w_4\text{Trigger}$$
        
        * **🌐 Nível 1 • Macro (Default 20%):** Amplitude de mercado (% acima de SMA 50 e 200). Protege o portfólio em regimes defensivos.
        * **🏢 Nível 2 • Setor RS (Default 20%):** Força Relativa do setor vs. Ibovespa ($\text{RS} > \text{SMA}_{50}$ e ROC 63d/126d).
        * **📈 Nível 3 • Trend Engine (Default 45%):** Alinhamento EMA, Slope SMA50, ADX $\ge 25$, Kaufman ER $\ge 0.40$ e Vol-Adj ROC.
        * **🎯 Nível 4 • Trigger (Default 15%):** Anti-exaustão ($\text{Dist. SMA20} \le 2.2\text{ ATR}$), RSI(14) 45-70 e Pullback.
        """)

    st.divider()

    # 1. Universo de Ativos
    st.markdown("### 🌐 1. Universo de Ativos")
    universe_option = st.selectbox(
        "Selecione o Universo",
        options=[
            f"Universo Amplo B3 ({len(IBOV_UNIVERSE) + len(SMALL_CAPS)} ativos)",
            f"Ibovespa Líquido ({len(IBOV_UNIVERSE)} ativos)",
            f"Small & Mid Caps ({len(SMALL_CAPS)} ativos)",
        ],
        index=0,
        help="Escolha o conjunto de tickers auditados para escanear. Por padrão, o Universo Amplo abrange tanto o Ibovespa quanto as principais Small Caps.",
        key="universe_select",
    )

    if "Universo Amplo" in universe_option:
        selected_universe = "amplo"
    elif "Ibovespa Líquido" in universe_option:
        selected_universe = "ibov"
    else:
        selected_universe = "smallcaps"

    # Tickers customizados
    custom_tickers = st.text_area(
        "Adicionar tickers customizados (vírgula):",
        placeholder="Ex: WEGE3.SA, VALE3.SA, PETR4.SA",
        help="Adicione tickers extras com ou sem o sufixo .SA.",
        key="custom_tickers",
        height=65,
    )

    st.divider()

    # 2. Pesos do TQS com Guia
    st.markdown("### ⚖️ 2. Pesos do TQS")
    st.caption("Ajuste a ponderação de cada camada do pipeline no score final:")

    w_macro = st.slider(
        "Macro (Regime / Breadth)",
        0.0, 1.0, DEFAULT_WEIGHTS["macro"], 0.05,
        help=(
            "🌐 Nível 1 • Macro (Regime / Breadth):\n\n"
            "• O que mede: A saúde estrutural da bolsa (% de ações acima das SMA 50 e 200, correlações e regime de mercado).\n\n"
            "🔼 Aumentar peso: Torna o screener mais conservador e dependente do mercado como um todo. Ativos só atingem scores de topo se a bolsa estiver em regime de alta saudável.\n\n"
            "🔽 Diminuir peso: Reduz a dependência do cenário macro geral, focando na força individual do ativo e do setor. Útil para encontrar papéis descorrelacionados mesmo em momentos de cautela do Ibovespa."
        ),
        key="w_macro",
    )
    w_setor = st.slider(
        "Força Relativa Setorial",
        0.0, 1.0, DEFAULT_WEIGHTS["setor"], 0.05,
        help=(
            "🏢 Nível 2 • Força Relativa Setorial (RS):\n\n"
            "• O que mede: A liderança e momentum do setor econômico vs. o Ibovespa (RS > SMA 50 e ROC 63d/126d).\n\n"
            "🔼 Aumentar peso: Prioriza a rotação setorial institucional. Ações pertencentes aos setores líderes (Top Performers) ganham grande destaque no ranking, penalizando papéis em setores fracos.\n\n"
            "🔽 Diminuir peso: Permite capturar ações individuais fortes e descoladas mesmo que o setor como um todo esteja atrasado ou em consolidação."
        ),
        key="w_setor",
    )
    w_trend = st.slider(
        "Trend Quality Engine",
        0.0, 1.0, DEFAULT_WEIGHTS["trend"], 0.05,
        help=(
            "📈 Nível 3 • Trend Quality Engine:\n\n"
            "• O que mede: A persistência técnica e eficiência da tendência do ativo (Alinhamento de médias móveis, Slope SMA 50, ADX & DI, Kaufman ER e Vol-Adj ROC).\n\n"
            "🔼 Aumentar peso: Enfatiza a solidez da tendência de médio/longo prazo. Filtra ruídos passageiros e seleciona papéis com estruturas de alta fortes e consolidadas.\n\n"
            "🔽 Diminuir peso: Reduz a exigência de histórico prolongado de tendência, dando mais relevância a gatilhos imediatos de curto prazo ou ao momento setorial."
        ),
        key="w_trend",
    )
    w_trigger = st.slider(
        "Gatilho & Anti-Exaustão",
        0.0, 1.0, DEFAULT_WEIGHTS["trigger"], 0.05,
        help=(
            "🎯 Nível 4 • Gatilho & Anti-Exaustão:\n\n"
            "• O que mede: O timing de entrada no curto prazo (pullback saudável na EMA 9/21, RSI 45-70 e filtro anti-exaustão contra compras esticadas longe da média).\n\n"
            "🔼 Aumentar peso: Prioriza o ponto de entrada ideal e imediato. Ideal para swing trade que busca ativos prontos para disparo com risco calibrado.\n\n"
            "🔽 Diminuir peso: Foca na qualidade estrutural da tendência do papel e do setor, tolerando ativos que estejam temporariamente esticados ou em consolidação lateral."
        ),
        key="w_trigger",
    )

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

    st.markdown(
        f"""<div style="background: #151922; border-radius: 6px; padding: 6px 10px; font-size: 0.78em; color: #8892B0; text-align: center; border: 1px solid #232936;">
        Soma normalizada: <b>{w_total:.2f}</b> → <b>100%</b>
        </div>""",
        unsafe_allow_html=True,
    )

    st.divider()

    # 3. Filtros Operacionais
    st.markdown("### 🔧 3. Filtros & Ranking")
    min_tqs = st.slider(
        "Corte Mínimo de TQS",
        0, 100, 0, 5,
        help="Filtra a visualização para exibir apenas ativos com TQS igual ou superior ao patamar escolhido.",
        key="min_tqs",
    )
    top_n = st.slider(
        "Ativos no Ranking Principal",
        5, 50, 20, 5,
        help="Quantidade de melhores ativos exibidos na tabela da aba Overview.",
        key="top_n",
    )

    st.divider()

    # Recalcular
    if st.button("🔄 Recalcular / Atualizar Cotações", use_container_width=True, key="recalc"):
        st.cache_data.clear()
        st.rerun()

    st.caption("⏱️ Dados: Yahoo Finance | Cache: 1h")
    st.caption("⚠️ Ferramenta quantitativa educacional — não é recomendação.")


# ══════════════════════════════════════════════════════════════════
#                       PIPELINE PRINCIPAL
# ══════════════════════════════════════════════════════════════════

st.markdown("""
# 📊 Quant Top-Down Screener
<p style="color: #8892B0; font-size: 1.05em; margin-top: -8px;">
    Pipeline Institucional de Seleção & Ranquear de Ações da B3
</p>
""", unsafe_allow_html=True)

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
    st.error("Nenhum ticker selecionado. Selecione um universo no menu lateral.")
    st.stop()

# ── 2. Fetch dados com Spinner ──
with st.spinner(f"📥 Coletando cotações de {len(ticker_list)} ativos da B3…"):
    universe_data = fetch_ohlcv(ticker_list, period="2y", interval="1d")
    benchmark_data = fetch_benchmark(BENCHMARK_TICKER, period="2y", interval="1d")

if not universe_data:
    st.error("❌ Não foi possível obter cotações para os ativos selecionados. Tente novamente.")
    st.stop()

if benchmark_data.empty:
    st.error("❌ Não foi possível obter dados do benchmark Ibovespa (^BVSP).")
    st.stop()

# ── 3. Análise Macro (Nível 1) ──
macro = analyze_macro(universe_data, benchmark_data=benchmark_data)

# ── 4. Análise Setorial (Nível 2) ──
sector_prices = build_sector_proxy(universe_data, universe)
sector_close_series = {name: series for name, series in sector_prices.items()}
sector_analysis = analyze_sectors(sector_close_series, benchmark_data["Close"])

sector_score_map = {
    name: sr.score for name, sr in sector_analysis.sectors.items()
}

# ── 5. Trend Engine (Nível 3) ──
trend_results = batch_analyze_trends(universe_data)

# ── 6. Scoring Final (Nível 4 + TQS Ponderado) ──
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
    st.markdown(f"### 🏆 Top {min(top_n, len(scores_df))} — Ranking por Trend Quality Score (TQS)")
    st.caption("Tabela com linhas de tons alternados para facilitar a leitura dos parâmetros operacionais de cada ativo:")

    if not scores_df.empty:
        # Stats rápidas em cards
        sc1, sc2, sc3, sc4 = st.columns(4)
        with sc1:
            st.metric("Total Escaneado", f"{len(final_scores)} ativos")
        with sc2:
            strong_buys = len([s for s in final_scores if "Compra Forte" in s.status])
            st.metric("🟢 Compra Forte", strong_buys)
        with sc3:
            buys = len([s for s in final_scores if s.status == "Compra"])
            st.metric("🟡 Compra", buys)
        with sc4:
            overbought = len([s for s in final_scores if "Sobrecomprado" in s.status])
            st.metric("🔴 Sobrecomprado", overbought)

        render_ranking_table(scores_df, top_n=top_n)

        # Distribuição TQS
        st.divider()
        render_tqs_distribution(scores_df)
    else:
        st.warning("Nenhum ativo atendeu ao corte de TQS configurado.")


# ══════════════════════ TAB 2: DEEP DIVE ══════════════════════════

with tab2:
    if not final_scores:
        st.info("Nenhum ativo disponível para análise com os filtros atuais.")
    else:
        # Ordenação estrita por TQS decrescente (mesma ordem da tabela de Ranking)
        final_scores_sorted = sorted(final_scores, key=lambda s: s.tqs, reverse=True)

        # Seletor com posição exata do ranking (#01, #02, etc.)
        ticker_options = [
            f"#{i:02d} | {s.ticker} — TQS: {s.tqs:.1f} ({s.sector})"
            for i, s in enumerate(final_scores_sorted, 1)
        ]
        selected_label = st.selectbox(
            "Selecione um ativo para análise detalhada (ordenado por Ranking TQS):",
            options=ticker_options,
            index=0,
            key="deepdive_select",
        )

        # Extrair ticker do label formatado
        selected_ticker = selected_label.split(" | ")[1].split(" — ")[0].strip()
        selected_score = next((s for s in final_scores_sorted if s.ticker == selected_ticker), None)
        selected_trend = trend_results.get(selected_ticker)

        if selected_score and selected_ticker in universe_data:
            col_left, col_right = st.columns([2, 1])

            with col_left:
                # Lookback selector
                lookback = st.select_slider(
                    "Janela de Visualização Histórica:",
                    options=[63, 126, 189, 252, 378, 504],
                    value=252,
                    format_func=lambda x: f"{x} dias (~{x // 21} meses)",
                    key="lookback_slider",
                )

                # Título limpo acima do gráfico (eliminando sobreposição na legenda)
                st.markdown(f"#### 🕯️ **{selected_ticker}** — Candlestick & Médias Móveis")

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


# ══════════════════════ TAB 3: MATRIZ SETORIAL ══════════════════════

with tab3:
    st.markdown("### 🗺️ Matriz de Força Relativa Setorial")
    st.markdown(
        "Dispersão de performance e liderança dos setores da B3 "
        "baseado na Força Relativa (RS Ratio vs. Ibovespa)."
    )

    render_sector_heatmap(
        sector_analysis=sector_analysis,
        ticker_sector_map=universe,
        scores=final_scores,
    )

    # Top ações por setor
    st.divider()
    st.markdown("### 📊 Melhores Ativos por Setor Econômico")

    sectors_with_stocks = {}
    for s in final_scores:
        if s.sector not in sectors_with_stocks:
            sectors_with_stocks[s.sector] = []
        sectors_with_stocks[s.sector].append(s)

    if sectors_with_stocks:
        # Ordenar setores pelo score setorial
        sector_order = sorted(
            sectors_with_stocks.keys(),
            key=lambda sec: sector_score_map.get(sec, 0),
            reverse=True,
        )

        for sector_name in sector_order:
            stocks = sectors_with_stocks[sector_name]
            if not stocks:
                continue

            rs_score = sector_score_map.get(sector_name, 0.0)

            # Sincronização precisa com a escala de Força Relativa Setorial
            if rs_score >= 60:
                emoji = "🟢"  # Líder / Forte
            elif rs_score >= 45:
                emoji = "🟡"  # Neutro / Estável (em torno do midpoint 50)
            elif rs_score >= 30:
                emoji = "🟠"  # Defensivo Moderado (faixa de transição)
            else:
                emoji = "🔴"  # Fraco / Fundo

            with st.expander(
                f"{emoji} {sector_name} — RS Score: {rs_score:.1f}/100 | {len(stocks)} ativos",
                expanded=False,
            ):
                sector_df = scores_to_dataframe(sorted(stocks, key=lambda s: s.tqs, reverse=True))
                render_ranking_table(sector_df, top_n=len(sector_df))
