# Análise de evolução e auditoria

## Síntese executiva

Nexo Vital foi implementado como produto independente: pacote Python tipado,
snapshots públicos versionados, contratos fail-fast, artefatos acadêmicos e interface
estática sem dependências remotas em tempo de execução. Não há histórico Git herdado
nem código de aplicação reutilizado.

O principal avanço não é visual. É a separação entre:

- associação no ajuste completo;
- desempenho fora da amostra;
- classificação por banda conformal;
- estabilidade de especificação;
- agrupamento exploratório;
- medição de medicamentos com cobertura explícita.

## Resultados do release inicial

### Painel e modelo

- 33.043 observações, 217 códigos de país/território, 9 indicadores e 2000–2022;
- 159 países completos no recorte de 2015;
- modelo principal com 4 preditores, sem mortalidade até cinco anos;
- R² associativo ≈ 0,735 e R² preditivo LOO ≈ 0,716;
- RMSE LOO ≈ 4,02 anos e MAE ≈ 2,94 anos;
- banda de 80% com raio ≈ 4,47 anos e cobertura empírica ≈ 81,1%;
- 16 países abaixo, 129 dentro e 14 acima da banda;
- 12 dos 16 abaixo estão na África Subsaariana, contra ≈ 3,92 esperados sob seleção
  aleatória; razão ≈ 3,06 e p hipergeométrico unilateral ≈ 9,45×10⁻⁶.

Os maiores desvios negativos incluem Eswatini, Lesoto, Botsuana, África do Sul,
Serra Leoa e Zimbábue. Esse padrão é compatível com carga histórica de HIV/AIDS,
desigualdade, conflito e capacidade estatal, mas o modelo não contém variáveis
suficientes para decompor essas explicações.

### Inferência e fragilidade

PIB e gasto em saúde têm VIF ao redor de 10. Isso não invalida a previsão conjunta,
mas torna frágeis leituras isoladas dos coeficientes. O dashboard mostra IC HC3 e o
release inclui benchmark Ridge aninhado para avaliar se regularização melhora a
generalização. Ridge obteve R² LOO ≈ 0,719, RMSE ≈ 4,00 e MAE ≈ 2,89 anos, ganho
pequeno e coerente com estabilização, não uma mudança de conclusão. Nove países
ultrapassam o limiar heurístico de Cook `4/n`; sua presença
deve motivar inspeção, não exclusão automática.

O sinal positivo parcial do tabaco no OLS é exemplo didático de confundimento
ecológico: países mais ricos podem combinar maior longevidade e prevalência reportada
de tabaco. O coeficiente não significa benefício do tabaco e não deve ser interpretado
biologicamente.

### Segmentação

- PC1 explica ≈ 66,1%; PC1–PC3, ≈ 94,8%;
- K=2 tem o melhor silhouette do intervalo testado (≈ 0,426);
- estabilidade bootstrap média: ARI ≈ 0,96 para K=2 e ≈ 0,81 para K=4;
- o percentil 5% do ARI é ≈ 0,91 em K=2 e ≈ 0,53 em K=4.

Consequência: K=2 pode resumir uma grande clivagem estrutural. K=4 oferece narrativas
mais ricas, mas é sensivelmente menos estável e permanece secundário.

### Paradoxo dos medicamentos

No último ano disponível por país no recorte WHO GLASS:

- 73 países/territórios e 414 observações entre 2016 e 2023;
- mediana de 18,80 DDD/1.000/dia;
- mínimo 5,66 e máximo 65,76, razão de 11,62 vezes;
- 25 de 73 alcançam participação Access ≥70%;
- 29 de 73 possuem ressalva explícita de cobertura;
- volume total e participação Access têm Spearman ρ≈−0,40 (p≈0,0005).

O último resultado sugere que, nesse recorte reportante, maior volume não coincide
necessariamente com composição mais alinhada ao grupo Access. Não é uma relação
causal e pode refletir mix epidemiológico, regras de mercado e diferenças de
vigilância. Brasil, China, Índia e Estados Unidos não aparecem na extração comparável;
isso é lacuna de cobertura, não consumo zero.

O cruzamento com expectativa de vida, mortalidade até cinco anos, PIB e gasto em
saúde próximos ao ano GLASS não produziu nenhuma correlação significativa após FDR
(oito testes; todos os valores-p ajustados ≈ 0,994). Esse resultado nulo é informativo:
volume nacional bruto, dentro da amostra seletiva de países reportantes, não funciona
como atalho simples para desenvolvimento ou resultado sanitário. Também pode refletir
baixa comparabilidade, seleção de participação e confundimento.

### Brasil e pessoas estrangeiras

Em 2019, a pesquisa turística implica cerca de 44,5 mil chegadas com saúde como motivo
principal. Em 2021, a fonte COBRADI reporta 35.164 internações SUS de nacionalidades
estrangeiras e aproximadamente R$ 67,0 milhões. Os números não podem ser comparados ou
somados: um é estimativa de fluxo de viagem; o outro é evento hospitalar por
nacionalidade e pode incluir residentes.

## Auditoria por severidade

### Alta prioridade

1. **Comparabilidade farmacêutica.** GLASS combina anos e escopos. A interface marca
   ressalvas, mas uma análise científica deve modelar cobertura ou restringir a um
   subconjunto comparável.
2. **Confundimento e desenho transversal.** O modelo não contém HIV, conflito,
   desigualdade, saneamento, qualidade institucional ou cobertura universal. Resíduos
   não devem orientar política como medida de desempenho.
3. **Colinearidade econômica.** PIB e gasto em saúde têm VIF elevado. Coeficientes
   parciais não sustentam ranking de “importância”. Ridge, componentes ou desenho
   longitudinal são próximos passos.

### Média prioridade

4. **Incerteza regional.** A banda conformal é marginal; regiões pequenas podem ter
   cobertura diferente. Avaliar conformal por grupos requer mais amostra ou pooling.
5. **Defasagem.** O modelo usa 2015; a interface deve sempre exibir o ano e nunca se
   apresentar como fotografia corrente.
6. **Série brasileira fragmentada.** Falta identificador de pessoa e atendimento
   ambulatorial. A evolução depende de microdados anonimizados e governança pública.
7. **SNGPC.** Dados de antimicrobianos e controlados no varejo privado brasileiro são
   volumosos e sofreram ruptura após a suspensão de transmissão em novembro de 2021.
   Devem formar painel separado, não ser juntados diretamente ao GLASS.

### Baixa prioridade / produto

8. Adicionar exportação selecionável em CSV e descrição longa de gráficos.
9. Criar testes visuais de regressão em múltiplos navegadores quando houver ambiente
   de integração contínua.
10. Publicar versões assinadas de snapshots e relatório de diferença entre releases.

## Próxima agenda científica

1. construir painel longitudinal com efeitos fixos de país e ano;
2. incorporar HIV, DALYs, saneamento, vacinação, Gini, conflito e governança;
3. pré-registrar hipóteses e separar confirmação de exploração;
4. estimar modelos hierárquicos com interceptos regionais;
5. testar defasagens entre gasto, acesso e desfechos;
6. estudar excesso e insuficiência de uso antimicrobiano com desfechos de resistência;
7. desenvolver módulo Brasil com SNGPC 2014–2021, denominadores populacionais e
   detecção explícita da ruptura regulatória;
8. buscar dados administrativos que distingam residente estrangeiro, turista,
   procedimento, pagador, fronteira e continuidade do cuidado.
