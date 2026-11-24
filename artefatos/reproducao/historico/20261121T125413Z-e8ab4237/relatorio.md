# Avaliação complementar de grafias

Estudo exploratório construído após o teste reservado; modelo congelado.
Grafias documentadas significam ocorrência em fonte municipal digital. O vínculo
com o catálogo é inferência textual sem revisão independente, não prova espacial.
Simulações não são consultas reais, registros de fala ou erros de OCR observados.
As taxas abaixo não devem ser combinadas com as 1.207 consultas do teste anterior.

| Categoria | Método | Consultas | Top-1 | Recall@100 | MRR@100 |
| --- | --- | ---: | ---: | ---: | ---: |
| fonetica_simulada | bm25 | 79 | 69.62% | 100.00% | 0.8142 |
| fonetica_simulada | bm25_trigramas | 79 | 92.41% | 100.00% | 0.9513 |
| fonetica_simulada | random_forest | 79 | 100.00% | 100.00% | 1.0000 |
| grafia_documentada | bm25 | 10 | 20.00% | 100.00% | 0.3933 |
| grafia_documentada | bm25_trigramas | 10 | 100.00% | 100.00% | 1.0000 |
| grafia_documentada | random_forest | 10 | 100.00% | 100.00% | 1.0000 |
| historica_simulada | bm25 | 90 | 44.44% | 90.00% | 0.5629 |
| historica_simulada | bm25_trigramas | 90 | 93.33% | 100.00% | 0.9571 |
| historica_simulada | random_forest | 90 | 100.00% | 100.00% | 1.0000 |

## Exposição anterior

Os grupos originais de treino, validação, teste e desenvolvimento são preservados.
O resumo JSON separa as métricas por esses grupos e por consulta nova/repetida.
Até o recorte de ruas de teste é exploratório: a seleção ocorreu depois do teste.
Precision@3 e Precision@5 diferem de Acerto@3 e Acerto@5; ambas estão no resumo.

## Falhas do Random Forest

| Consulta | Referência | Primeiro resultado | Motivo |
| --- | --- | --- | --- |

Nenhuma falha Top-1 neste conjunto complementar.

A comparação completa, incluindo acertos ganhos e perdidos, está em comparacao.csv.
As fontes, o gabarito, as exclusões e os scripts usados acompanham esta execução.
Modelo SHA-256: `1e1a2f7fb1521ce49f53d920116aacfdac9191e33c86fa1d77a5838bc3702ba0`.
