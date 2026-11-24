# Pauliceia TCC — busca aproximada de logradouros históricos

Instruções de instalação e execução: [Como rodar o projeto](COMO_RODAR.md).

## O que foi implementado

1. Ambiente Docker com PostGIS, Elasticsearch, API, serviço de modelo e portal.
2. Extração e normalização dos nomes do backup: **853 registros pesquisáveis**,
   correspondentes a **847 nomes normalizados**.
3. Recuperação de até 100 candidatos com BM25 e BM25 com trigramas.
4. Random Forest para reordenar candidatos, combinando sete atributos:
   Damerau–Levenshtein, Jaro–Winkler, Token Sort, Token Set, Levenshtein,
   pontuação relativa do Elasticsearch e razão de comprimentos.
5. Gabarito de 6.136 consultas, separação por grupos e seleção do modelo na
   validação; teste reservado, complemento histórico/fonético exploratório e
   comparação das similaridades isoladas.
6. Busca aproximada integrada ao portal: sugestões de ruas e recuperação de
   pontos existentes no banco por ID, número e ano, sem interpolar coordenadas.
7. Testes automatizados, validação do serviço HTTP e medições locais de latência.

## Resultados principais

Teste reservado de **1.207 consultas**; todos os métodos usam o mesmo catálogo.

| Método | Top-1 | Recall@100 | MRR@100 |
| --- | ---: | ---: | ---: |
| BM25 | 63,55% | 86,50% | 0,6889 |
| BM25 + trigramas | 97,02% | 100,00% | 0,9808 |
| Random Forest | 100,00% | 100,00% | 1,0000 |

O RF corrigiu 36 consultas em relação ao BM25 com trigramas, sem perda de acertos
nesse teste. O resultado de 100% se refere a esse conjunto e não constitui uma
garantia para novos dados.

O complemento tem 179 consultas: 10 grafias documentadas, 90 variantes históricas
simuladas e 79 fonéticas simuladas. RF e Damerau–Levenshtein isolado acertaram
todas nesse complemento. O vínculo das grafias documentadas aos IDs foi inferido
textualmente, sem revisão histórica independente.

| Validação HTTP local | Verificações corretas | Mediana | P95 |
| --- | ---: | ---: | ---: |
| Busca | 336/336 | 14,97 ms | 33,09 ms |
| Pontos | 219/219 | 3,92 ms | 22,54 ms |
| Fluxos | 60/60 | 20,58 ms | 46,99 ms |

As medições foram sequenciais, com aquecimento, no ambiente local. A validação
espacial confere fidelidade ao backup, sem medir erro contra uma fonte geográfica
independente. A solução usa Python/RapidFuzz no lugar do Painless inicialmente
previsto; o recorte não cobre integralmente os séculos XIX e XX.
