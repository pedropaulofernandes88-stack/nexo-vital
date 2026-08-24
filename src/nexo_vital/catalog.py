"""Canonical indicator and source catalog."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Indicator:
    id: str
    code: str
    label: str
    unit: str
    source: str
    direction: int


INDICATORS: dict[str, Indicator] = {
    "life_expectancy": Indicator(
        "life_expectancy", "WHOSIS_000001", "Expectativa de vida", "anos", "WHO GHO", 1
    ),
    "under5_mortality": Indicator(
        "under5_mortality",
        "SH.DYN.MORT",
        "Mortalidade até 5 anos",
        "por 1.000",
        "World Bank / UN IGME",
        -1,
    ),
    "physicians_density": Indicator(
        "physicians_density", "HWF_0001", "Médicos", "por 10.000", "WHO GHO", 1
    ),
    "obesity_prevalence": Indicator(
        "obesity_prevalence", "NCD_BMI_30A", "Obesidade adulta", "%", "WHO GHO", -1
    ),
    "gdp_per_capita_ppp": Indicator(
        "gdp_per_capita_ppp",
        "NY.GDP.PCAP.PP.KD",
        "PIB per capita PPP",
        "US$ internacionais constantes de 2021",
        "World Bank",
        1,
    ),
    "expected_schooling": Indicator(
        "expected_schooling", "SE.SCH.LIFE", "Escolaridade esperada", "anos", "World Bank", 1
    ),
    "population": Indicator("population", "SP.POP.TOTL", "População", "pessoas", "World Bank", 0),
    "health_spending_ppp": Indicator(
        "health_spending_ppp",
        "SH.XPD.CHEX.PP.CD",
        "Gasto corrente em saúde per capita",
        "US$ internacionais correntes",
        "World Bank",
        1,
    ),
    "tobacco_prevalence": Indicator(
        "tobacco_prevalence",
        "SH.PRV.SMOK",
        "Uso de tabaco",
        "% da população com 15+",
        "World Bank",
        -1,
    ),
}

CORE_FEATURES = (
    "obesity_prevalence",
    "gdp_per_capita_ppp",
    "health_spending_ppp",
    "tobacco_prevalence",
)

CLUSTER_FEATURES = (
    "life_expectancy",
    "under5_mortality",
    "obesity_prevalence",
    "gdp_per_capita_ppp",
    "health_spending_ppp",
    "tobacco_prevalence",
)

LOG_FEATURES = frozenset({"under5_mortality", "gdp_per_capita_ppp", "health_spending_ppp"})

LEGACY_FIELD_MAP = {
    "expectativa_vida": "life_expectancy",
    "mortalidade_infantil": "under5_mortality",
    "medicos_10k": "physicians_density",
    "obesidade": "obesity_prevalence",
    "pib_per_capita_ppp": "gdp_per_capita_ppp",
    "escolaridade_esperada": "expected_schooling",
    "populacao": "population",
    "gasto_saude_per_capita": "health_spending_ppp",
    "tabagismo": "tobacco_prevalence",
}
