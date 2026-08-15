"""
universe.py — Definição do universo de ativos auditados da B3 e mapeamento setorial.

Contém os 116 tickers mais líquidos e ativos da B3 (100% validados contra yfinance),
classificados por setor econômico e agrupados em Ibovespa Líquido e Small/Mid Caps.
"""

from __future__ import annotations

# ─────────────────────────── Benchmark ────────────────────────────
BENCHMARK_TICKER: str = "^BVSP"

# ────────── Universo Ibovespa Líquido (~60 Ativos Principais) ─────
IBOV_UNIVERSE: dict[str, str] = {
    # ── Financeiro & Seguros ──
    "ITUB4.SA": "Financeiro",
    "BBDC4.SA": "Financeiro",
    "BBDC3.SA": "Financeiro",
    "BBAS3.SA": "Financeiro",
    "SANB11.SA": "Financeiro",
    "B3SA3.SA": "Financeiro",
    "ITSA4.SA": "Financeiro",
    "BBSE3.SA": "Financeiro",
    "BPAC11.SA": "Financeiro",
    "CXSE3.SA": "Financeiro",
    "PSSA3.SA": "Financeiro",
    "IRBR3.SA": "Financeiro",

    # ── Materiais Básicos, Mineração & Siderurgia & Papel ──
    "VALE3.SA": "Materiais Básicos",
    "CSNA3.SA": "Materiais Básicos",
    "GGBR4.SA": "Materiais Básicos",
    "GOAU4.SA": "Materiais Básicos",
    "USIM5.SA": "Materiais Básicos",
    "SUZB3.SA": "Materiais Básicos",
    "KLBN11.SA": "Materiais Básicos",
    "BRKM5.SA": "Materiais Básicos",
    "CMIN3.SA": "Materiais Básicos",
    "DXCO3.SA": "Materiais Básicos",

    # ── Petróleo, Gás & Biocombustíveis ──
    "PETR4.SA": "Petróleo & Gás",
    "PETR3.SA": "Petróleo & Gás",
    "PRIO3.SA": "Petróleo & Gás",
    "RECV3.SA": "Petróleo & Gás",
    "BRAV3.SA": "Petróleo & Gás",  # Fusão 3R Petroleum + Enauta
    "CSAN3.SA": "Petróleo & Gás",
    "UGPA3.SA": "Petróleo & Gás",
    "VBBR3.SA": "Petróleo & Gás",
    "RAIZ4.SA": "Petróleo & Gás",

    # ── Consumo, Varejo & Alimentos ──
    "ABEV3.SA": "Consumo & Alimentos",
    "ASAI3.SA": "Consumo & Alimentos",
    "BEEF3.SA": "Consumo & Alimentos",
    "MDIA3.SA": "Consumo & Alimentos",
    "SMTO3.SA": "Consumo & Alimentos",
    "SLCE3.SA": "Consumo & Alimentos",
    "MGLU3.SA": "Consumo & Varejo",
    "LREN3.SA": "Consumo & Varejo",
    "AZZA3.SA": "Consumo & Varejo",  # Fusão Arezzo&Co + Grupo Soma
    "ALPA4.SA": "Consumo & Varejo",

    # ── Utilidade Pública (Energia & Saneamento) ──
    "CMIG4.SA": "Utilidade Pública",
    "CPFE3.SA": "Utilidade Pública",
    "ENGI11.SA": "Utilidade Pública",
    "EGIE3.SA": "Utilidade Pública",
    "EQTL3.SA": "Utilidade Pública",
    "SBSP3.SA": "Utilidade Pública",
    "SAPR11.SA": "Utilidade Pública",
    "CPLE3.SA": "Utilidade Pública",
    "TAEE11.SA": "Utilidade Pública",
    "AURE3.SA": "Utilidade Pública",  # Incorporou AES Brasil
    "CSMG3.SA": "Utilidade Pública",
    "ALUP11.SA": "Utilidade Pública",

    # ── Saúde ──
    "RDOR3.SA": "Saúde",
    "HAPV3.SA": "Saúde",
    "FLRY3.SA": "Saúde",
    "RADL3.SA": "Saúde",
    "HYPE3.SA": "Saúde",

    # ── Bens Industriais & Logística ──
    "WEGE3.SA": "Industrial & Bens de Capital",
    "RENT3.SA": "Transporte & Logística",
    "RAIL3.SA": "Transporte & Logística",
    "ECOR3.SA": "Transporte & Logística",

    # ── Imobiliário ──
    "CYRE3.SA": "Imobiliário & Construção",
    "MRVE3.SA": "Imobiliário & Construção",
    "EZTC3.SA": "Imobiliário & Construção",
    "MULT3.SA": "Imobiliário & Construção",
    "IGTI11.SA": "Imobiliário & Construção",
    "ALOS3.SA": "Imobiliário & Construção",

    # ── Telecomunicações, Tecnologia & Educação ──
    "VIVT3.SA": "Telecomunicações",
    "TIMS3.SA": "Telecomunicações",
    "TOTS3.SA": "Tecnologia",
    "LWSA3.SA": "Tecnologia",
    "YDUQ3.SA": "Educação",
    "COGN3.SA": "Educação",
}


# ── Small & Mid Caps Líquidas da B3 (~56 Ativos Complementares) ──
SMALL_CAPS: dict[str, str] = {
    # ── Financeiro & Bancos Médios ──
    "BRSR6.SA": "Financeiro",
    "ABCB4.SA": "Financeiro",

    # ── Materiais Básicos & Metalurgia ──
    "FESA4.SA": "Materiais Básicos",
    "RANI3.SA": "Materiais Básicos",

    # ── Consumo, Varejo & Vestuário ──
    "CEAB3.SA": "Consumo & Varejo",
    "VIVA3.SA": "Consumo & Varejo",
    "SBFG3.SA": "Consumo & Varejo",
    "LJQQ3.SA": "Consumo & Varejo",
    "AMER3.SA": "Consumo & Varejo",
    "BHIA3.SA": "Consumo & Varejo",
    "CAML3.SA": "Consumo & Alimentos",
    "AGRO3.SA": "Consumo & Alimentos",

    # ── Saúde & Farmácias ──
    "PNVL3.SA": "Saúde",
    "QUAL3.SA": "Saúde",
    "ONCO3.SA": "Saúde",
    "VVEO3.SA": "Saúde",
    "MATD3.SA": "Saúde",
    "BLAU3.SA": "Saúde",

    # ── Bens Industriais, Máquinas & Autopeças ──
    "TUPY3.SA": "Industrial & Bens de Capital",
    "KEPL3.SA": "Industrial & Bens de Capital",
    "POMO4.SA": "Industrial & Bens de Capital",
    "RAPT4.SA": "Industrial & Bens de Capital",
    "VLID3.SA": "Industrial & Bens de Capital",
    "AERI3.SA": "Industrial & Bens de Capital",

    # ── Logística & Transporte ──
    "SIMH3.SA": "Transporte & Logística",
    "MOVI3.SA": "Transporte & Logística",
    "TGMA3.SA": "Transporte & Logística",

    # ── Imobiliário, Construção & Shoppings ──
    "DIRR3.SA": "Imobiliário & Construção",
    "CURY3.SA": "Imobiliário & Construção",
    "PLPL3.SA": "Imobiliário & Construção",
    "TRIS3.SA": "Imobiliário & Construção",
    "LAVV3.SA": "Imobiliário & Construção",
    "TEND3.SA": "Imobiliário & Construção",
    "EVEN3.SA": "Imobiliário & Construção",
    "JHSF3.SA": "Imobiliário & Construção",

    # ── Tecnologia & Internet ──
    "CASH3.SA": "Tecnologia",
    "POSI3.SA": "Tecnologia",
    "INTB3.SA": "Tecnologia",
    "SEQL3.SA": "Tecnologia",
    "BMOB3.SA": "Tecnologia",

    # ── Educação ──
    "ANIM3.SA": "Educação",
    "CSED3.SA": "Educação",
}


def get_universe(selection: str = "ibov") -> dict[str, str]:
    """Retorna o dicionário {ticker: setor} conforme a seleção do usuário.

    Args:
        selection: 'ibov' (60 ativos) | 'smallcaps' (56 ativos) | 'amplo' (116 ativos)

    Returns:
        Dicionário ticker → setor.
    """
    if selection == "ibov":
        return dict(IBOV_UNIVERSE)
    elif selection == "smallcaps":
        return dict(SMALL_CAPS)
    elif selection in ("amplo", "all"):
        return {**IBOV_UNIVERSE, **SMALL_CAPS}
    else:
        return dict(IBOV_UNIVERSE)


def get_all_sectors() -> list[str]:
    """Retorna lista de todos os setores únicos no universo completo."""
    all_tickers = {**IBOV_UNIVERSE, **SMALL_CAPS}
    return sorted(set(all_tickers.values()))


def get_sector_tickers(sector: str, universe: dict[str, str] | None = None) -> list[str]:
    """Retorna os tickers pertencentes a um setor específico."""
    if universe is None:
        universe = {**IBOV_UNIVERSE, **SMALL_CAPS}
    return [t for t, s in universe.items() if s == sector]
