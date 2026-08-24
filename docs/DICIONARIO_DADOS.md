# Dicionário de dados

## Painel global

| Campo | Tipo | Regra |
|---|---|---|
| `country_iso3` | string | exatamente três letras maiúsculas |
| `country_name` | string | nome harmonizado pelo World Bank |
| `region` | string | região analítica do World Bank |
| `income_group` | string | grupo de renda da versão do snapshot |
| `year` | inteiro | 2000–2022 no release inicial |
| `indicator_id` | enum | identificador interno estável |
| `indicator_code` | string | código da fonte original |
| `source` | enum | organização responsável |
| `unit` | string | unidade sem conversão implícita |
| `value` | float | valor observado, finito |

## Resultados por país

| Campo | Significado |
|---|---|
| `predicted_life_expectancy_loo` | previsão produzida sem treinar no próprio país |
| `residual_loo` | observado menos previsto, em anos |
| `prediction_band_low/high` | previsão ± raio conformal comum |
| `position` | `below`, `within` ou `above` |
| `cooks_distance` | influência no ajuste OLS completo |
| `leverage` | diagonal da matriz chapéu |
| `stable_all_specs` | classe idêntica nas especificações de sensibilidade |
| `pc1`, `pc2` | escores dos dois primeiros componentes |
| `cluster_k2` | partição estatística principal, ordenada por expectativa de vida |
| `cluster_k4` | tipologia exploratória, ordenada por expectativa de vida |

## WHO GLASS

| Campo | Significado |
|---|---|
| `total_ddd_per_1000_day` | antibióticos e antituberculose, DDD/1.000/dia |
| `access_ddd`, `watch_ddd`, `reserve_ddd` | volume por grupo AWaRe |
| `unclassified_ddd` | volume não classificado/recomendado |
| `access_share_pct` | Access dividido pela soma AWaRe disponível |
| `coverage_caveat` | limitação específica documentada pela fonte |
| `has_coverage_caveat` | marcador derivado, nunca substitui a ressalva textual |
| `paradox_quadrant` | volume alto/baixo × Access acima/abaixo da mediana |

## OECD

| Campo | Significado |
|---|---|
| `class_id` | classe canônica |
| `atc` | código ATC ou composição de códigos |
| `ddd_per_1000_day` | DDD por 1.000 habitantes por dia |
| `oecd_status` | flag de observação da fonte |
| `percent_change` | `(DDD_2021−DDD_2011)/DDD_2011 × 100` |

## Brasil

`estimated_health_reason_arrivals` é uma estimativa de fluxo anual. `hospitalizations`
é contagem de eventos hospitalares. `expenditure_brl` é valor reportado nominalmente
em 2021. Nenhum desses campos identifica pessoas únicas.
