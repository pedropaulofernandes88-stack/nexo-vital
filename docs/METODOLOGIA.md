# Protocolo metodológico do Nexo Vital

## 1. Pergunta e estatuto da evidência

O Nexo Vital investiga associações ecológicas entre condições econômicas, gastos,
riscos populacionais e expectativa de vida. A unidade de análise é o país, não a
pessoa. O desenho principal é transversal e observacional. Portanto:

- coeficientes não estimam efeitos causais;
- resíduos não medem eficiência governamental;
- agrupamentos não são tipos naturais de países;
- associação agregada pode divergir da associação individual;
- erro de mensuração e variáveis omitidas podem mudar sinais e magnitudes.

O recorte de 2015 foi selecionado por cobertura conjunta, antes da inspeção de
resíduos. A escolha reduz perda de países e evita misturar anos no modelo principal,
mas não representa necessariamente a realidade corrente.

## 2. Dados e contratos

### 2.1 Painel global

O contrato longo possui chave única `(country_iso3, year, indicator_id)`. Campos
obrigatórios: ISO3, nome, região, renda, ano, identificador, código original, fonte,
unidade e valor. A construção falha se houver:

- ISO3 fora de `[A-Z]{3}`;
- chave duplicada;
- valor ausente ou não finito;
- indicador fora do catálogo;
- fonte, código ou unidade divergente do catálogo.

Indicadores:

| ID canônico | Código | Fonte | Unidade |
|---|---|---|---|
| `life_expectancy` | WHOSIS_000001 | WHO GHO | anos |
| `under5_mortality` | SH.DYN.MORT | World Bank / UN IGME | por 1.000 nascidos vivos |
| `physicians_density` | HWF_0001 | WHO GHO | por 10.000 habitantes |
| `obesity_prevalence` | NCD_BMI_30A | WHO GHO | % de adultos |
| `gdp_per_capita_ppp` | NY.GDP.PCAP.PP.KD | World Bank | US$ int. constantes de 2021 |
| `expected_schooling` | SE.SCH.LIFE | World Bank | anos |
| `population` | SP.POP.TOTL | World Bank | pessoas |
| `health_spending_ppp` | SH.XPD.CHEX.PP.CD | World Bank | US$ int. correntes per capita |
| `tobacco_prevalence` | SH.PRV.SMOK | World Bank | % da população 15+ |

### 2.2 Medicamentos

O módulo antimicrobiano usa WHO GLASS processado pela Our World in Data. Consumo é
DDD por 1.000 habitantes por dia; Access, Watch, Reserve e não classificados medem
composição. O ano mais recente é escolhido por país, logo o gráfico é um recorte de
últimas observações e não um mesmo ano universal.

O módulo OECD seleciona quatro classes: antidiabéticos (A10), modificadores de
lipídios (C10), antidepressivos (N06A) e uma soma dos códigos C02, C03, C07, C08 e C09
para anti-hipertensivos. Comparações 2011–2021 exigem observação nos dois anos.

DDD é uma unidade técnica padronizada. Ela não mede pacientes tratados, adesão,
necessidade clínica ou adequação. Fontes nacionais podem cobrir vendas, reembolsos,
dispensação, comunidade, hospitais ou somente setor público.

### 2.3 Pessoas estrangeiras e saúde no Brasil

Duas métricas são mantidas em painéis separados:

1. estimativa de chegadas com saúde como motivo principal: percentual de pesquisa
   amostral multiplicado pelo total anual de chegadas internacionais;
2. internações SUS por nacionalidade estrangeira em 2021: eventos hospitalares e
   gasto, incluindo potencialmente pessoas residentes.

Elas não compartilham população-alvo, denominador ou unidade. Não são somadas e não
recebem o rótulo de “turistas médicos” como se fossem equivalentes.

## 3. Transformações

Antes da regressão aplicam-se logaritmos naturais a PIB per capita PPP e gasto em
saúde per capita PPP. Obesidade e tabaco permanecem em pontos percentuais. No ajuste
inferencial, os preditores transformados são padronizados:

\[
z_{ij} = \frac{x_{ij} - \bar{x}_j}{s_j}.
\]

Assim, cada coeficiente corresponde à diferença em anos associada a um desvio-padrão
do preditor, mantendo os demais constantes. “Mantendo constante” é uma propriedade
algébrica do modelo, não prova de intervenção controlada.

## 4. Modelo de associação

O modelo principal é:

\[
LE_i = \beta_0 + \beta_1 Obesidade_i + \beta_2 \log(PIB_i)
       + \beta_3 \log(GastoSaude_i) + \beta_4 Tabaco_i + \epsilon_i.
\]

Mortalidade até cinco anos não entra no modelo principal, pois contribui
mecanicamente para a própria expectativa de vida. Ela é usada na segmentação e em
um benchmark rotulado como sensibilidade. O objetivo é impedir que concordância entre
dois desfechos demográficos seja vendida como explicação independente.

### 4.1 Inferência robusta

O estimador pontual é OLS. A matriz de covariância usa HC3:

\[
\widehat{Var}_{HC3}(\hat\beta)=(X'X)^{-1}X'\,diag\left[
\frac{\hat e_i^2}{(1-h_{ii})^2}\right]X(X'X)^{-1}.
\]

HC3 reduz a fragilidade dos erros-padrão sob heterocedasticidade e alavancagem, mas
não corrige forma funcional errada, endogeneidade ou variáveis omitidas.

São exportados VIF, distância de Cook e alavancagem. VIF elevado entre PIB e gasto em
saúde é esperado e significa que seus coeficientes parciais isolados têm incerteza
maior. O efeito conjunto e o desempenho preditivo são mais defensáveis que uma
narrativa causal para cada coeficiente.

### 4.2 Validação fora da amostra

Para cada país `i`, o modelo é treinado nos outros `n−1` países e produz
`\hat y_i^{(-i)}`. O resíduo fora da amostra é:

\[
r_i = y_i - \hat y_i^{(-i)}.
\]

Reportam-se R² preditivo, RMSE, MAE e viés. Uma validação cruzada 10-fold repetida 20
vezes fornece a distribuição das métricas em 200 partições. Padronização é ajustada
dentro de cada conjunto de treino, evitando vazamento.

Como benchmark para multicolinearidade, Ridge é ajustado em um esquema aninhado:
cada treino externo escolhe a penalização por validação interna de cinco partes. O
país externo nunca participa da escolha de `alpha`.

### 4.3 Banda conformal

A banda exploratória usa o quantil de ordem superior dos valores `|r_i|`. Para
cobertura nominal `1−α=0,8`:

\[
q = Q_{\lceil(n+1)(1-\alpha)\rceil/n}(|r|).
\]

Um país está “abaixo” quando `r_i < −q`, “acima” quando `r_i > q` e “dentro” nos
demais casos. Como os mesmos resíduos LOO calibram e avaliam a cobertura agregada,
esta é uma aproximação jackknife/conformal exploratória, não um intervalo causal ou
uma garantia condicional por região.

## 5. Sensibilidade

As posições são recalculadas com a mesma largura de referência para:

- modelo principal;
- modelo acrescido de mortalidade até cinco anos;
- modelo sem tabaco;
- modelo somente com PIB e gasto em saúde.

“Estável” significa mesma classe nas quatro especificações. Isso mede apenas a
dependência desse conjunto de escolhas, não todas as decisões plausíveis.

## 6. Concentração regional

Se `N` é o total de países, `K` o total da região, `n` o número abaixo da banda e `x`
o observado da região entre os `n`, calcula-se:

\[
p=P(X\ge x),\quad X\sim Hipergeométrica(N,K,n).
\]

O teste quantifica quão incomum seria a concentração sob seleção aleatória simples.
Não demonstra que a região, por si só, cause o desvio. Conflito, epidemias,
desigualdade interna, qualidade institucional e história sanitária são confundidores
plausíveis não medidos.

## 7. PCA e clusterização

Seis indicadores entram na segmentação: expectativa de vida, mortalidade até cinco
anos, obesidade, PIB, gasto em saúde e tabaco. Variáveis positivas assimétricas usam
log; todas são padronizadas. PCA decompõe a matriz de correlação.

K-Means é comparado para `k=2,…,8` por:

- silhouette, maior é melhor;
- Davies–Bouldin, menor é melhor;
- Calinski–Harabasz, maior é melhor;
- inércia, usada apenas como diagnóstico complementar.

Para estabilidade, 250 amostras bootstrap são geradas para `k=2` e `k=4`. Cada
modelo é projetado sobre a amostra completa e comparado ao agrupamento de referência
por Adjusted Rand Index. K=2 é a partição estatística principal; K=4 é uma tipologia
exploratória mais granular.

## 8. Descoberta exploratória

Resíduos do modelo principal são correlacionados por Spearman com densidade médica,
escolaridade esperada e log da população. Indicadores próximos a 2015 são aceitos em
janela máxima de três anos. Valores-p recebem correção Benjamini–Hochberg FDR.

Em uma família separada, consumo total e participação Access do último GLASS são
cruzados com expectativa de vida, mortalidade até cinco anos, PIB e gasto em saúde no
ano mais próximo, limitado a três anos. Os oito testes de Spearman recebem correção
FDR conjunta. Como o “último ano” difere por país e GLASS não tem cobertura universal,
o resultado é exploratório e sensível ao mecanismo de participação na vigilância.

Esses testes foram definidos no código, mas não pré-registrados antes de todo contato
com os dados. Resultados devem ser tratados como geração de hipótese.

## 9. Fontes oficiais

- [WHO Global Health Observatory](https://www.who.int/data/gho)
- [World Bank Indicators API](https://datahelpdesk.worldbank.org/knowledgebase/articles/889392)
- [WHO GLASS antimicrobial-use dashboard](https://data.who.int/dashboards/amr/antimicrobial-use)
- [WHO GLASS report 2025](https://www.who.int/publications/i/item/9789240108127)
- [OECD pharmaceutical consumption definition](https://www.oecd.org/en/publications/health-at-a-glance-2023_7a7afb35-en/full-report/pharmaceutical-consumption_4b6cb013.html)
- [Anvisa SNGPC — consumo por estado](https://www.gov.br/anvisa/pt-br/assuntos/fiscalizacao-e-monitoramento/sngpc/consumo-de-medicamentos-por-estado)
- [Ministério do Turismo — demanda internacional 2019](https://www.gov.br/turismo/pt-br/acesso-a-informacao/acoes-e-programas/observatorio/demanda-turistica/demanda-turistica-internacional-1/DemandaInternacional2019Apresentao.pdf)
- [Relatório COBRADI 2021](https://www.gov.br/abc/pt-br/centrais-de-conteudo/publicacoes/documentos/a-cooperacao-educacional-e-cientifica-brasileira-em-foco-relatorio-cobradi-2021.pdf)
