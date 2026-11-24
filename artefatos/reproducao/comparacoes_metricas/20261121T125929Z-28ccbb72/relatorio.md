# Comparação de métricas isoladas

Comparação adicional realizada após conhecer o teste original. Nenhum ajuste do modelo.
As quatro similaridades e o RF reordenam os mesmos candidatos BM25 + trigramas (até 100).
BM25 aparece como referência de recuperação própria, com candidatos potencialmente diferentes.
Empates preservam a ordem dos trigramas; por isso, não se trata de busca isolada em todo o catálogo.
As similaridades usam a mesma precisão float32 dos atributos do RF.
Este experimento compara métodos; não mede causalmente a contribuição de cada atributo no RF.

## Teste reservado original (1.207 consultas)

| Método | N | Top-1 | Top-3 | Top-5 | Recall@100 | MRR@100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 1207 | 63.55% | 72.91% | 76.14% | 86.50% | 0.6889 |
| BM25 + trigramas | 1207 | 97.02% | 99.09% | 99.50% | 100.00% | 0.9808 |
| Damerau-Levenshtein | 1207 | 91.80% | 92.71% | 93.70% | 100.00% | 0.9264 |
| Jaro-Winkler | 1207 | 95.36% | 97.85% | 98.26% | 100.00% | 0.9670 |
| Token Sort | 1207 | 98.18% | 98.59% | 98.92% | 100.00% | 0.9854 |
| Token Set | 1207 | 98.59% | 99.83% | 99.83% | 100.00% | 0.9923 |
| Random Forest | 1207 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |

## Complementar: fonetica_simulada

| Método | N | Top-1 | Top-3 | Top-5 | Recall@100 | MRR@100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 79 | 69.62% | 93.67% | 97.47% | 100.00% | 0.8142 |
| BM25 + trigramas | 79 | 92.41% | 96.20% | 100.00% | 100.00% | 0.9513 |
| Damerau-Levenshtein | 79 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| Jaro-Winkler | 79 | 97.47% | 100.00% | 100.00% | 100.00% | 0.9873 |
| Token Sort | 79 | 89.87% | 93.67% | 96.20% | 100.00% | 0.9242 |
| Token Set | 79 | 98.73% | 100.00% | 100.00% | 100.00% | 0.9937 |
| Random Forest | 79 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |

## Complementar: grafia_documentada

| Método | N | Top-1 | Top-3 | Top-5 | Recall@100 | MRR@100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 10 | 20.00% | 50.00% | 60.00% | 100.00% | 0.3933 |
| BM25 + trigramas | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| Damerau-Levenshtein | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| Jaro-Winkler | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| Token Sort | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| Token Set | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| Random Forest | 10 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |

## Complementar: historica_simulada

| Método | N | Top-1 | Top-3 | Top-5 | Recall@100 | MRR@100 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| BM25 | 90 | 44.44% | 64.44% | 71.11% | 90.00% | 0.5629 |
| BM25 + trigramas | 90 | 93.33% | 97.78% | 97.78% | 100.00% | 0.9571 |
| Damerau-Levenshtein | 90 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| Jaro-Winkler | 90 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |
| Token Sort | 90 | 98.89% | 98.89% | 98.89% | 100.00% | 0.9894 |
| Token Set | 90 | 94.44% | 100.00% | 100.00% | 100.00% | 0.9722 |
| Random Forest | 90 | 100.00% | 100.00% | 100.00% | 100.00% | 1.0000 |

## Comparações pareadas com o Random Forest

| Recorte | Comparador | Ganhos RF Top-1 | Perdas RF Top-1 | Diferença MRR |
| --- | --- | ---: | ---: | ---: |
| fonetica_simulada | BM25 | 24 | 0 | +0.1858 |
| fonetica_simulada | BM25 + trigramas | 6 | 0 | +0.0487 |
| fonetica_simulada | Damerau-Levenshtein | 0 | 0 | +0.0000 |
| fonetica_simulada | Jaro-Winkler | 2 | 0 | +0.0127 |
| fonetica_simulada | Token Set | 1 | 0 | +0.0063 |
| fonetica_simulada | Token Sort | 8 | 0 | +0.0758 |
| grafia_documentada | BM25 | 8 | 0 | +0.6067 |
| grafia_documentada | BM25 + trigramas | 0 | 0 | +0.0000 |
| grafia_documentada | Damerau-Levenshtein | 0 | 0 | +0.0000 |
| grafia_documentada | Jaro-Winkler | 0 | 0 | +0.0000 |
| grafia_documentada | Token Set | 0 | 0 | +0.0000 |
| grafia_documentada | Token Sort | 0 | 0 | +0.0000 |
| historica_simulada | BM25 | 50 | 0 | +0.4371 |
| historica_simulada | BM25 + trigramas | 6 | 0 | +0.0429 |
| historica_simulada | Damerau-Levenshtein | 0 | 0 | +0.0000 |
| historica_simulada | Jaro-Winkler | 0 | 0 | +0.0000 |
| historica_simulada | Token Set | 5 | 0 | +0.0278 |
| historica_simulada | Token Sort | 1 | 0 | +0.0106 |
| teste | BM25 | 440 | 0 | +0.3111 |
| teste | BM25 + trigramas | 36 | 0 | +0.0192 |
| teste | Damerau-Levenshtein | 99 | 0 | +0.0736 |
| teste | Jaro-Winkler | 56 | 0 | +0.0330 |
| teste | Token Set | 17 | 0 | +0.0077 |
| teste | Token Sort | 22 | 0 | +0.0146 |

## Interpretação e rastreabilidade

As taxas são descritivas; não foi realizado teste de significância estatística.
O conjunto complementar é exploratório, com ruas de treino, validação, desenvolvimento e teste.
As categorias documentada e simuladas não são agregadas em uma única taxa.
A grafia documentada tem fonte municipal, mas o vínculo com o ID é inferência textual.
O resumo JSON separa novidade da consulta, partição original, tipos de variação e médias por nome.
Precision@K, também salva, é diferente da presença de algum relevante no Top-K.
O número de candidatos empatados no maior escore de cada métrica está em empates.csv.
Os métodos originais reproduziram as métricas anteriores por consulta; no complemento,
também reproduziram os rankings completos. O arquivo do modelo não mudou.
Caminhos e hashes dos dados de entrada estão em resumo.json; os caches originais são preservados.
