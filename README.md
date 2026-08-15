# 📊 Quant Top-Down Screener

**Screener de Ações Top-Down Quant-Mental** para o mercado brasileiro (B3), implementando um pipeline hierárquico de 4 níveis para filtrar e ranquear ativos líquidos com base em análise quantitativa institucional.

## 🏗️ Pipeline de 4 Níveis

```
[Nível 1: Regime Macro] ➔ [Nível 2: Força Relativa Setorial] ➔ [Nível 3: Trend Engine] ➔ [Nível 4: Trigger]
```

### Nível 1 — Regime Macro & Market Breadth
- % de ativos acima da SMA 50 e SMA 200
- Classificação: Favorável (>60%), Neutro (40-60%), Defensivo (<40%)
- Correlações rolantes cross-asset

### Nível 2 — Força Relativa Setorial
- RS Ratio = Preço Setor / Benchmark (IBOV)
- RS Trend: RS Ratio > SMA50(RS Ratio)
- ROC 63 e 126 dias do RS Ratio
- Ranking em quartis

### Nível 3 — Trend Quality Engine
| Indicador | Score |
|---|---|
| EMA Alignment (Preço > EMA21 > EMA50 > SMA200) | 0-25 |
| Slope linear SMA 50 (20 dias) | 0-15 |
| ADX(14) + Direcionalidade (+DI > -DI) | 0-20 |
| Kaufman Efficiency Ratio (ER ≥ 0.40) | 0-20 |
| Vol-Adj ROC (ROC63 / ATR%) | 0-20 |

### Nível 4 — Trigger & Anti-Exaustão
- Distância da média: (Preço - SMA20) / ATR(14) ≤ 2.2
- RSI(14) entre 45-70
- Pullback zone (preço entre EMA9 e EMA21)

### Trend Quality Score (TQS)

```
TQS = 0.20 × Macro + 0.20 × Setor RS + 0.45 × Trend + 0.15 × Trigger
```

## 🚀 Quick Start

### Local
```bash
pip install -r requirements.txt
streamlit run app.py
```

### Deploy no Streamlit Cloud
1. Faça push para o GitHub
2. Conecte o repositório em [share.streamlit.io](https://share.streamlit.io)
3. Defina `app.py` como entry point

## 📁 Estrutura

```
quant-topdown-screener/
├── .streamlit/config.toml    # Tema dark institucional
├── data/
│   ├── universe.py           # Tickers IBOV + Small Caps + setores
│   └── fetcher.py            # Ingestão yfinance com cache
├── engine/
│   ├── macro.py              # Market Breadth & Regime
│   ├── sectors.py            # RS Ratio & Ranking Setorial
│   ├── trend.py              # EMA, ADX, Kaufman ER, Vol-Adj ROC
│   └── scoring.py            # TQS final + Trigger
├── ui/
│   ├── dashboard.py          # Tabelas, KPIs, Heatmaps
│   └── charts.py             # Candlesticks, Subplots Plotly
├── app.py                    # Entry point Streamlit
└── requirements.txt
```

## ⚖️ Disclaimer

Este screener é uma ferramenta **educacional e de pesquisa**. Não constitui recomendação de investimento. Sempre faça sua própria análise antes de tomar decisões de investimento.

## 📊 Stack

- **Frontend:** Streamlit
- **Dados:** yfinance
- **Gráficos:** Plotly
- **Cálculos:** NumPy, Pandas, SciPy
- **Python:** 3.10+
