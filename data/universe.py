"""
universe.py — Definição do universo de ativos, mapeamento setorial e benchmark.

Contém os tickers do Ibovespa, classificação por setor, e os índices
setoriais usados como proxy para Força Relativa.
"""

from __future__ import annotations

# ─────────────────────────── Benchmark ────────────────────────────
BENCHMARK_TICKER: str = "^BVSP"

# ─────────── Setores e seus Índices/Proxies na B3 ────────────────
# Mapeamento: setor → ticker do índice (alguns podem não ter ETF direto,
# então usamos o índice mais próximo disponível no Yahoo Finance).
SECTOR_INDICES: dict[str, str] = {
    "Financeiro":         "^IFNC",
    "Materiais Básicos":  "^IMAT",
    "Consumo":            "^ICON",
    "Utilidade Pública":  "^UTIL",
    "Energia Elétrica":   "^IEEX",
    "Imobiliário":        "^IMOB",
    "Industrial":         "^INDX",
    "Small Caps":         "^SMLL",
}

# ────────── Universo Ibovespa – Top Constituintes ─────────────────
# Cada ticker está mapeado ao seu setor para RS setorial.
IBOV_UNIVERSE: dict[str, str] = {
    # ── Financeiro ──
    "ITUB4.SA": "Financeiro",
    "BBDC4.SA": "Financeiro",
    "BBAS3.SA": "Financeiro",
    "SANB11.SA": "Financeiro",
    "B3SA3.SA": "Financeiro",
    "ITSA4.SA": "Financeiro",
    "BBSE3.SA": "Financeiro",
    "BPAC11.SA": "Financeiro",
    "CIEL3.SA": "Financeiro",
    "IRBR3.SA": "Financeiro",

    # ── Materiais Básicos ──
    "VALE3.SA": "Materiais Básicos",
    "CSNA3.SA": "Materiais Básicos",
    "GGBR4.SA": "Materiais Básicos",
    "GOAU4.SA": "Materiais Básicos",
    "USIM5.SA": "Materiais Básicos",
    "SUZB3.SA": "Materiais Básicos",
    "KLBN11.SA": "Materiais Básicos",
    "BRKM5.SA": "Materiais Básicos",
    "CMIN3.SA": "Materiais Básicos",

    # ── Energia / Petróleo / Gás ──
    "PETR4.SA": "Energia",
    "PETR3.SA": "Energia",
    "PRIO3.SA": "Energia",
    "RECV3.SA": "Energia",
    "RRRP3.SA": "Energia",
    "CSAN3.SA": "Energia",
    "UGPA3.SA": "Energia",
    "VBBR3.SA": "Energia",

    # ── Consumo ──
    "MGLU3.SA": "Consumo",
    "LREN3.SA": "Consumo",
    "AMER3.SA": "Consumo",
    "NTCO3.SA": "Consumo",
    "PETZ3.SA": "Consumo",
    "ASAI3.SA": "Consumo",
    "CRFB3.SA": "Consumo",
    "BHIA3.SA": "Consumo",
    "SOMA3.SA": "Consumo",
    "ARZZ3.SA": "Consumo",
    "ABEV3.SA": "Consumo",
    "JBSS3.SA": "Consumo",
    "BRFS3.SA": "Consumo",
    "MRFG3.SA": "Consumo",
    "BEEF3.SA": "Consumo",
    "MDIA3.SA": "Consumo",
    "SMTO3.SA": "Consumo",
    "SLCE3.SA": "Consumo",

    # ── Utilidade Pública / Energia Elétrica ──
    "ELET3.SA": "Utilidade Pública",
    "ELET6.SA": "Utilidade Pública",
    "CMIG4.SA": "Utilidade Pública",
    "CPFE3.SA": "Utilidade Pública",
    "ENGI11.SA": "Utilidade Pública",
    "EGIE3.SA": "Utilidade Pública",
    "EQTL3.SA": "Utilidade Pública",
    "SBSP3.SA": "Utilidade Pública",
    "SAPR11.SA": "Utilidade Pública",
    "CPLE6.SA": "Utilidade Pública",
    "TAEE11.SA": "Utilidade Pública",
    "AURE3.SA": "Utilidade Pública",

    # ── Saúde ──
    "RDOR3.SA": "Saúde",
    "HAPV3.SA": "Saúde",
    "FLRY3.SA": "Saúde",
    "QUAL3.SA": "Saúde",
    "HYPE3.SA": "Saúde",
    "RADL3.SA": "Saúde",

    # ── Industrial / Infra ──
    "WEGE3.SA": "Industrial",
    "RENT3.SA": "Industrial",
    "RAIL3.SA": "Industrial",
    "CCRO3.SA": "Industrial",
    "ECOR3.SA": "Industrial",
    "EMBR3.SA": "Industrial",
    "GOLL4.SA": "Industrial",
    "AZUL4.SA": "Industrial",

    # ── Imobiliário ──
    "CYRE3.SA": "Imobiliário",
    "MRVE3.SA": "Imobiliário",
    "EZTC3.SA": "Imobiliário",
    "EVEN3.SA": "Imobiliário",
    "MULT3.SA": "Imobiliário",
    "IGTI11.SA": "Imobiliário",

    # ── Tecnologia / Telecom ──
    "VIVT3.SA": "Tecnologia/Telecom",
    "TIMS3.SA": "Tecnologia/Telecom",
    "TOTS3.SA": "Tecnologia/Telecom",
    "LWSA3.SA": "Tecnologia/Telecom",
    "CASH3.SA": "Tecnologia/Telecom",
}


# ── Small Caps Líquidas (complemento opcional) ───────────────────
SMALL_CAPS: dict[str, str] = {
    "POSI3.SA": "Tecnologia/Telecom",
    "MOVI3.SA": "Industrial",
    "AERI3.SA": "Industrial",
    "VLID3.SA": "Industrial",
    "CAML3.SA": "Consumo",
    "PNVL3.SA": "Saúde",
    "BPAN4.SA": "Financeiro",
    "ALPA4.SA": "Consumo",
    "YDUQ3.SA": "Consumo",
    "COGN3.SA": "Consumo",
    "SIMH3.SA": "Industrial",
    "TEND3.SA": "Imobiliário",
    "JHSF3.SA": "Imobiliário",
    "MLAS3.SA": "Consumo",
    "TRIS3.SA": "Imobiliário",
    "LAVV3.SA": "Imobiliário",
    "ESPA3.SA": "Consumo",
    "AESB3.SA": "Utilidade Pública",
    "RAIZ4.SA": "Energia",
    "MBLY3.SA": "Tecnologia/Telecom",
}


def get_universe(selection: str = "ibov") -> dict[str, str]:
    """Retorna o dicionário {ticker: setor} conforme a seleção do usuário.

    Args:
        selection: 'ibov' | 'amplo' | 'smallcaps' | 'all'

    Returns:
        Dicionário ticker → setor.
    """
    if selection == "ibov":
        return dict(IBOV_UNIVERSE)
    elif selection == "smallcaps":
        return dict(SMALL_CAPS)
    elif selection in ("amplo", "all"):
        merged = {**IBOV_UNIVERSE, **SMALL_CAPS}
        return merged
    else:
        return dict(IBOV_UNIVERSE)


def get_all_sectors() -> list[str]:
    """Retorna lista de todos os setores únicos no universo completo."""
    all_tickers = {**IBOV_UNIVERSE, **SMALL_CAPS}
    return sorted(set(all_tickers.values()))


def get_sector_tickers(sector: str, universe: dict[str, str] | None = None) -> list[str]:
    """Retorna os tickers pertencentes a um setor específico.

    Args:
        sector: Nome do setor.
        universe: Universo de tickers. Se None, usa IBOV + Small Caps.

    Returns:
        Lista de tickers do setor.
    """
    if universe is None:
        universe = {**IBOV_UNIVERSE, **SMALL_CAPS}
    return [t for t, s in universe.items() if s == sector]
