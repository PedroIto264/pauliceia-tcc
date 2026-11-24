# Comparação das similaridades isoladas com o Random Forest

Executada em 21/11/2026, identificador `20261121T125929Z-28ccbb72`.
Resultados completos: `.local/comparacoes_metricas/20261121T125929Z-28ccbb72`.

## Protocolo

Foram comparados BM25, BM25 com trigramas, Damerau-Levenshtein, Jaro-Winkler,
Token Sort, Token Set e o Random Forest congelado. As quatro similaridades
reordenam a mesma lista de até 100 candidatos produzida pelos trigramas.
Não há acesso à resposta esperada durante a ordenação. Ausências do alvo
na lista inicial continuam contando como falha.

A normalização, as funções de similaridade e a representação float32 são as
mesmas usadas pelo modelo. A ordenação é decrescente pelo valor de cada
similaridade. Empates conservam a ordem inicial dos trigramas. Assim, os
comparadores são reordenadores por uma única métrica com desempate pelo estágio
anterior; não são buscas independentes sobre o catálogo inteiro.
O BM25 é uma referência separada e pode recuperar outros candidatos.

As quatro métricas foram fixadas no script antes desta execução, de acordo
com os objetivos da proposta. Esta comparação foi adicionada após conhecer
os resultados do teste original; não houve seleção de novos hiperparâmetros,
ajuste de pesos, alteração do índice ou retreinamento.
O conjunto complementar permanece exploratório.

O RF recebe sete atributos: as quatro medidas comparadas, Levenshtein, escore
relativo do Elasticsearch e razão de comprimentos. Este experimento compara
métodos finais. Não é uma remoção controlada de atributos do RF e não permite
atribuir causalmente o ganho a uma medida específica.

## Teste reservado original

| Método | Acertos Top-1 / 1.207 | Top-1 | MRR@100 |
| --- | ---: | ---: | ---: |
| BM25 | 767 | 63,55% | 0,6889 |
| BM25 + trigramas | 1.171 | 97,02% | 0,9808 |
| Damerau-Levenshtein | 1.108 | 91,80% | 0,9264 |
| Jaro-Winkler | 1.151 | 95,36% | 0,9670 |
| Token Sort | 1.185 | 98,18% | 0,9854 |
| Token Set | 1.190 | 98,59% | 0,9923 |
| Random Forest | 1.207 | 100,00% | 1,0000 |

O melhor comparador isolado observado foi Token Set. O RF apresentou 17 acertos
Top-1 adicionais, sem perdas, uma diferença de aproximadamente 1,41 ponto
percentual. Em relação a Token Sort, Jaro-Winkler e Damerau-Levenshtein,
foram respectivamente 22, 56 e 99 acertos adicionais, sem perdas.
Contra os trigramas, reproduziram-se os 36 ganhos já conhecidos.
Essas diferenças são descritivas; não foi executado teste de significância.

Recall@100 foi 100% para os trigramas e todos os reordenadores. Isso decorre
do conjunto de candidatos compartilhado: a reordenação não recupera novos IDs.
O Recall@100 do BM25 foi 86,50%.

Das 99 falhas Top-1 de Damerau-Levenshtein, 97 ocorreram em inversões da ordem
das palavras e duas em abreviações. Jaro-Winkler apresentou 44 falhas em ordem,
nove em abreviações, uma em omissão e duas em duas omissões.
Token Sort apresentou 11 falhas em omissão, nove em transposição e duas em
duas omissões. Token Set apresentou cinco em omissão, quatro em transposição,
três em substituição, três em inserção e duas em duas omissões.
Os resultados por variação e por nome estão preservados em `resumo.json`.

Exemplo concreto: para `rua ameli sa barbosa`, Token Set colocou
`rua sa barbosa` em primeiro lugar e a referência `rua amelia sa barbosa` em
segundo. O RF colocou a referência em primeiro. Esse caso ilustra a necessidade
de distinguir nomes parcialmente coincidentes, além de tolerar erros de escrita.

## Avaliação complementar

| Método | Documentadas (10), Top-1 | Históricas simuladas (90), Top-1 | Fonéticas simuladas (79), Top-1 |
| --- | ---: | ---: | ---: |
| BM25 | 20,00% | 44,44% | 69,62% |
| BM25 + trigramas | 100,00% | 93,33% | 92,41% |
| Damerau-Levenshtein | 100,00% | 100,00% | 100,00% |
| Jaro-Winkler | 100,00% | 100,00% | 97,47% |
| Token Sort | 100,00% | 98,89% | 89,87% |
| Token Set | 100,00% | 94,44% | 98,73% |
| Random Forest | 100,00% | 100,00% | 100,00% |

Damerau-Levenshtein empatou com o RF nos 179 casos complementares.
Nas dez grafias documentadas, todos os reordenadores e os trigramas empataram.
Portanto, este recorte não demonstra vantagem adicional do RF sobre
Damerau-Levenshtein. A vantagem observada no teste original está relacionada
ao conjunto mais diverso de transformações, especialmente à ordem das palavras.
Não se deve afirmar superioridade universal do RF sobre métricas isoladas.

As categorias documentada, histórica simulada e fonética simulada são
apresentadas separadamente. O JSON contém recortes por exposição anterior da
rua e repetição da consulta, conforme o protocolo de `HISTORICO.md`.
O vínculo das grafias documentadas aos IDs do catálogo continua sendo inferência
textual sem revisão independente; não houve avaliação geométrica nesta etapa.

## Verificações e reprodução

Foram conferidos os hashes dos caches e gabaritos e a compatibilidade de índice,
versões e modelo entre os experimentos. As métricas originais de BM25, trigramas
e RF coincidiram por consulta. No complemento, os rankings completos também
coincidiram. O arquivo do modelo permaneceu inalterado.
Os dez testes automatizados passaram, incluindo empates, candidatos ausentes,
rejeição de cache incompleto/duplicado e divergência de resultados anteriores.

Para reproduzir, nesta pasta:

```powershell
python comparar_metricas.py
```

O comando usa o ambiente do treinamento, lê os caches locais e salva outra
execução. Não exige Docker nem altera o portal ou os experimentos anteriores.
Saídas: `relatorio.md`, `resumo.json`, `resultados.csv`, `comparacoes_rf.csv`,
`empates.csv` e cópias dos scripts. O resumo registra hashes e caminhos de entrada.
Precision@1/3/5, Acerto@1/3/5, Recall@100 e MRR@100 estão nas saídas detalhadas;
Precision@K não deve ser confundida com Acerto@K.
