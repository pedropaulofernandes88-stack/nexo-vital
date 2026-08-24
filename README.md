# Nexo Vital

**Atlas Global de Saúde, Desenvolvimento e Medicamentos**

**[Acessar o dashboard publicado](https://pedropaulofernandes88-stack.github.io/nexo-vital/)**

[![quality-gates](https://github.com/pedropaulofernandes88-stack/nexo-vital/actions/workflows/ci.yml/badge.svg)](https://github.com/pedropaulofernandes88-stack/nexo-vital/actions/workflows/ci.yml)
[![deploy-dashboard](https://github.com/pedropaulofernandes88-stack/nexo-vital/actions/workflows/pages.yml/badge.svg)](https://github.com/pedropaulofernandes88-stack/nexo-vital/actions/workflows/pages.yml)

Nexo Vital é um observatório analítico independente para investigar como condições
econômicas, capacidade sanitária, riscos populacionais e uso de medicamentos se
associam a resultados de saúde entre países. O projeto separa três perguntas que não
devem ser confundidas:

1. quais fatores estão associados à expectativa de vida em um recorte internacional;
2. quais países se afastam do valor esperado por um modelo explicitamente limitado;
3. como volume, composição e cobertura dos dados de medicamentos variam entre países.

O produto não faz inferência causal e não converte consumo farmacêutico em qualidade
assistencial. Ele registra incerteza, cobertura e comparabilidade como parte do dado.

## Diferenciais metodológicos

- contrato de dados com chaves, domínio, unidade e proveniência validados;
- regressão com erros-padrão HC3, VIF, alavancagem e distância de Cook;
- validação leave-one-out e validação cruzada repetida fora da amostra;
- banda preditiva conformal baseada em resíduos fora da amostra;
- desempenho e viés auditados por região;
- concentração regional dos desvios testada por distribuição hipergeométrica;
- PCA com contribuição das variáveis e seleção de `k` por três critérios;
- estabilidade da clusterização estimada por bootstrap e Adjusted Rand Index;
- sensibilidades de especificação, sinais e classificação;
- módulo farmacêutico que distingue volume, composição AWaRe e ressalvas de cobertura;
- duas medidas brasileiras deliberadamente separadas: turismo por motivo de saúde e
  internações SUS de pessoas com nacionalidade estrangeira.

## Execução

```powershell
# Somente ao abrir um novo release de dados:
python pipelines/refresh_public_sources.py

# Construção e gates locais:
python pipelines/build_observatory.py
python pipelines/validate_release.py
python -m pytest
python -m http.server 8000 --directory dashboard
```

Abra `dashboard/index.html` por um servidor HTTP local após a geração dos artefatos.

## Estrutura

- `src/nexo_vital/`: regras de dados, modelagem, segmentação e exportação;
- `pipelines/`: preparação, construção e auditoria de release;
- `data/snapshots/`: cópias versionáveis dos dados públicos usados;
- `data/derived/`: tabelas derivadas, nunca editadas manualmente;
- `artifacts/`: resultados acadêmicos tabulares;
- `dashboard/`: interface estática e seus contratos JSON;
- `docs/`: metodologia, dicionário e auditoria.

## Limites essenciais

O recorte principal é ecológico e transversal (2015), escolhido por completude. Uma
associação entre países não identifica um efeito individual. Ausência em GLASS não
significa consumo zero. DDD/1.000 habitantes/dia é uma unidade técnica de volume, não
o número de pessoas tratadas nem uma medida de prescrição apropriada. Internações SUS
por nacionalidade não equivalem a turistas médicos e podem incluir residentes.

O modelo principal não usa mortalidade até cinco anos para explicar expectativa de
vida: as duas medidas compartilham mecanicamente parte do mesmo processo demográfico.
Essa variável entra na segmentação e em um benchmark de sensibilidade, explicitamente
rotulado, para que ganho preditivo não seja confundido com explicação independente.

Consulte [DATA_LICENSES.md](DATA_LICENSES.md) para fontes, termos e datas de acesso.
