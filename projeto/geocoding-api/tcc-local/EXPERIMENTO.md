# Avaliação da busca por nomes

A avaliação complementar de grafias documentadas e simulações históricas/fonéticas
está descrita em [HISTORICO.md](HISTORICO.md). Ela utiliza o modelo congelado e
tem caráter exploratório, sem substituir ou ampliar retroativamente o teste reservado.

A comparação executada entre as quatro similaridades isoladas e o Random Forest
está em [COMPARACAO_METRICAS.md](COMPARACAO_METRICAS.md). Ela reutiliza os candidatos
salvos e registra os ganhos no teste original e os empates no conjunto complementar.

O protocolo de latência HTTP e correspondência dos pontos com o backup está em
[VALIDACAO_PORTAL.md](VALIDACAO_PORTAL.md), com coleta ao vivo concluída e resultados conferidos.
As decisões e limitações para a redação estão em [METODOLOGIA_FINAL.md](METODOLOGIA_FINAL.md).

O gabarito ampliado contém consultas de nome de logradouro e os IDs relevantes
no catálogo do backup analisado. A unidade avaliada é a recuperação do nome.
Número, ano e geometria são avaliados pelo piloto de geocodificação e pelo portal.

## Dados e relevância

O catálogo pesquisável contém 853 registros e 847 nomes normalizados.
São excluídos da indexação os cinco registros sem nome e os 15 registros
identificados como `nao oficial` ou `n.o`.

Todos os IDs de um mesmo nome normalizado são relevantes para a consulta.
Essa equivalência é textual. A identificação do local físico requer contexto
adicional quando vários registros compartilham um nome.

`preparar_gabarito.py` usa o backup com SHA-256 registrado em
`dados/gabarito_manifesto.json` e a semente textual `pauliceia-tcc-v1`.
Cada consulta informa seu ID, grupo, partição, nome de referência, IDs relevantes,
tipo de variação e origem.

As consultas originais vêm do cadastro. As demais são transformações sintéticas
com resposta atribuída pelo nome que as originou.

| Tipo | Transformação |
| --- | --- |
| normalizacao | Remoção de acentos e padronização dos espaços, quando alteram a grafia |
| abreviacao | Substituição do tipo de logradouro por uma abreviação predefinida |
| omissao | Remoção de uma letra |
| substituicao | Troca de uma letra pela seguinte no alfabeto, com retorno de z para a |
| insercao | Duplicação de uma letra |
| transposicao | Inversão de duas letras adjacentes distintas |
| duas_omissoes | Remoção de uma letra em cada uma de duas palavras |
| ordem | Inversão da ordem das palavras após o tipo de logradouro |

As edições de caracteres atingem palavras de pelo menos quatro letras,
excluindo tipos de logradouro, conectivos e os marcadores par/ímpar.
A posição de cada edição é determinada por hash. A inserção sempre duplica
uma letra, e a substituição segue a regra alfabética acima.

O gabarito registra essas escolhas para permitir medir separadamente cada
transformação. A frequência das transformações foi determinada pelo gerador.
Uma avaliação de consultas reais e variantes históricas equivalentes exige
exemplos com proveniência documental ou julgamento humano adicional.
As grafias históricas já presentes no cadastro são preservadas nos nomes originais.

Variantes que coincidem com outro nome cadastrado ou que foram geradas para
nomes de referência diferentes são excluídas e registradas em
`dados/consultas_ambiguas.csv`. A versão inicial produziu zero exclusões.
Variantes textualmente repetidas para o mesmo nome também são deduplicadas.
Ambiguidades semânticas mais sutis ainda podem exigir revisão humana.

## Partições

O agrupamento considera o nome normalizado, a equivalência de ordem de palavras
e a remoção do marcador final par/ímpar. Todos os registros e variantes do grupo
recebem a mesma partição. Esse agrupamento conserva os tipos de logradouro.
Relações históricas de renomeação que dependam de documentação adicional devem
ser incorporadas em uma versão posterior do protocolo.

As seis ruas do piloto ficam em desenvolvimento. Os demais grupos são ordenados
por hash com a semente fixa e distribuídos em aproximadamente 60% para treino,
20% para validação e 20% para teste.

| Partição | Grupos | Nomes normalizados | Consultas |
| --- | ---: | ---: | ---: |
| Desenvolvimento | 6 | 6 | 43 |
| Treino | 496 | 505 | 3.681 |
| Validação | 166 | 169 | 1.205 |
| Teste | 166 | 167 | 1.207 |
| Total | 834 | 847 | 6.136 |

O catálogo completo permanece pesquisável em todas as partições.
A separação se aplica às consultas e aos exemplos de correspondência usados no
aprendizado. Os nomes do teste precisam existir no índice para serem recuperados.

Os seis casos de desenvolvimento já foram usados para inspecionar o comportamento
dos métodos. O treino servirá à estimação dos parâmetros do modelo, a validação
à escolha das configurações, e o teste à avaliação final da configuração escolhida.
As partições foram fixadas antes da coleta dos resultados do gabarito ampliado.

## Execução

Na pasta `tcc-local`, execute os comandos em sequência.

```powershell
python preparar_gabarito.py
python avaliar_gabarito.py
```

O segundo comando inicia o Elasticsearch pelo Docker e coleta as partições de
treino e validação. As opções de partição podem ser consultadas com `--help`.
O comando imprime progresso a cada lote de 40 consultas.

Cada execução concluída recebe um diretório próprio em `.local/avaliacoes`.
Falhas interrompem a execução antes da publicação desse diretório.

- `resultados.csv` contém uma linha por consulta e método.
- `candidatos.jsonl.gz` contém os IDs e escores dos até 100 candidatos, inclusive
  consultas em que nenhum resultado relevante foi recuperado.
- `resumo.json` registra métricas, versão do Elasticsearch, configuração do índice,
  partições, hashes e identificação da execução.
- `gabarito_ampliado.csv` guarda a versão utilizada na execução.

## Comparação

BM25 usa o campo de palavras. BM25 com trigramas combina esse campo com o campo
de trigramas por `multi_match` do tipo `most_fields`, com pesos iguais.
Ambos usam a mesma análise de caixa e acentos, o mesmo catálogo e até 100
candidatos. Empates são resolvidos por ID crescente.

As métricas são calculadas sobre os conjuntos de IDs relevantes.

- Acerto@K vale um quando pelo menos um resultado relevante aparece nas primeiras
  K posições.
- Recall@100 é a fração dos IDs relevantes recuperados entre os 100 candidatos.
- Precision@K é o número de IDs relevantes nas primeiras K posições dividido por K.
- MRR@100 é a média do inverso da posição do primeiro resultado relevante.
  Consultas sem acerto entre os 100 candidatos contribuem com zero.

O resumo informa médias por consulta, médias com o mesmo peso para cada nome e
resultados por tipo de variação. `elastic_took_ms` mede o tempo informado pelo
Elasticsearch para aquela busca. O tempo total percebido pelo usuário também
envolve rede, API e interface.

O Random Forest usa os candidatos recuperados por BM25 com trigramas.
Consultas cujo alvo fique fora dos 100 candidatos continuam contando na avaliação.
O treinamento supervisionado recebe o cache produzido por esta coleta.

## Treinamento do Random Forest

O script `treinar_modelo.py` recebe o diretório de uma avaliação concluída.
Ele cria um ambiente Python em `.local/venv-modelo` e instala as versões
de `requirements-modelo.txt`. O cálculo das similaridades deste treinamento
é feito em Python com RapidFuzz. A proposta original prevê Painless para
incorporação das métricas no indexador. A execução online adotada usa um serviço
Python que reutiliza as mesmas funções e versões do treinamento.

```powershell
python treinar_modelo.py .local/avaliacoes/20261119T053434Z-74227fef
```

Cada exemplo é um par entre consulta e candidato recuperado por BM25 com trigramas.
O alvo vale um quando o ID está entre os registros relevantes do gabarito.
As consultas de treino fornecem os exemplos usados no ajuste das árvores.
A validação fornece as métricas usadas para escolher a configuração.

São calculados sete atributos com nomes normalizados pela mesma função do catálogo.

- Similaridade de Damerau-Levenshtein, incluindo transposições.
- Similaridade de Jaro-Winkler.
- Token Sort Ratio dividido por 100.
- Token Set Ratio dividido por 100.
- Similaridade de Levenshtein.
- Escore do Elasticsearch dividido pelo maior escore da consulta.
- Razão entre o comprimento menor e o maior das duas strings.

Os IDs identificam a relevância e a saída. Os atributos fornecidos ao modelo são
somente as sete medidas acima. Os pares de cada consulta recebem peso de
1 dividido pelo número de candidatos. Os rótulos de classe são balanceados
em cada amostra bootstrap com `balanced_subsample`.

A grade inicial tem quatro combinações de profundidade máxima 12 ou sem limite,
e mínimo de dois ou cinco exemplos por folha. Todas usam 200 árvores,
semente 42 e até quatro tarefas paralelas durante o ajuste. As previsões usam
uma tarefa para somar as árvores sempre na mesma ordem e tornar os escores
e desempates reproduzíveis. A escolha maximiza MRR por nome
na validação. Em empate, considera Top-1 por nome e depois a ordem da grade.

A ordenação usa a saída de `predict_proba` para a classe relevante.
Essa saída é usada como escore de ordenação, cuja calibração probabilística
exigiria uma análise própria. Empates preservam a ordem do Elasticsearch.
A lista de candidatos é a mesma em todos os métodos. Consultas sem alvo
recuperado continuam contribuindo com zero para acerto e MRR.

O diretório `.local/modelos` recebe o modelo escolhido, métricas por consulta,
mudanças de posição na validação, resumo das quatro configurações, versões das
bibliotecas, hashes das entradas e cópias dos scripts. A serialização é conferida
comparando as previsões antes e depois da leitura do arquivo salvo.
As métricas de treino descrevem o ajuste na própria base de aprendizado.
A avaliação final será feita com a configuração escolhida e as consultas de teste.

## Teste final reservado

O modelo selecionado foi salvo na execução `20261119T061951Z-cbab31c0`, com
profundidade máxima 12 e mínimo de dois exemplos por folha. O script abaixo
reutiliza esse arquivo e as 1.207 consultas dos 166 grupos reservados para teste.

```powershell
python testar_modelo.py
```

O comando utiliza o ambiente Python do treinamento, coleta BM25 e BM25 com
trigramas no Elasticsearch e aplica o modelo aos candidatos dos trigramas.
O código de teste carrega o modelo selecionado e chama a previsão. A configuração
foi escolhida com os resultados de validação antes desta coleta.

A comparação verifica o hash do modelo e do gabarito, as versões das bibliotecas,
a versão do Elasticsearch, a configuração do índice e a ausência de consultas
de teste nos resultados usados para treino e validação. A coleta original fica
em `.local/avaliacoes`. As métricas dos três métodos, as mudanças de posição e
os hashes de entrada ficam em uma execução própria em `.local/testes`.

Se a coleta terminar e uma etapa posterior falhar, o argumento `--avaliacao`
permite fornecer o diretório já coletado. O resumo inclui resultados por nome,
por consulta e por tipo de variação, além dos acertos ganhos e perdidos e das
falhas da recuperação inicial. A interpretação se refere ao gabarito sintético
e às consultas originais deste catálogo.

## Integração com o portal

O serviço interno `modelo` carrega uma vez o arquivo selecionado
`20261119T061951Z-cbab31c0/modelo.joblib`. Na inicialização, confere o hash,
as versões das bibliotecas, os atributos e os parâmetros salvos.
O arquivo é montado como somente leitura no contêiner.

Ao receber uma consulta, recupera até 100 documentos do índice identificado
no resumo do modelo, calcula os sete atributos e ordena pela saída do Random Forest.
Empates preservam a ordem do Elasticsearch. As cinco primeiras sugestões retornam
ao componente existente do portal, com seus IDs e nomes cadastrados.
O cálculo das similaridades ocorre em Python com RapidFuzz e a previsão usa
scikit-learn, compartilhando as funções do experimento offline.

A API Node encaminha a busca ao endereço configurado em `RERANK_URL` e devolve
o hash do modelo no cabeçalho `X-Pauliceia-Modelo`. Uma falha do serviço resulta
em HTTP 503, permitindo à interface informar a indisponibilidade.
O serviço Python e o Elasticsearch ficam na rede interna do Compose.

```powershell
python site_local.py
```

O comando constrói o serviço e a API e confere a resposta pelo proxy do portal.
Os casos `rua ancheita` e `rua cotsa` devem colocar `rua anchieta` e `rua costa`
em primeiro lugar. No experimento de teste, a Rua Costa ocupava a posição 76
antes da reordenação. O comando também verifica o ponto de Becco dos Afflictos,
número 11, em 1940, e a ausência de ponto para o mesmo número em 1800.

A reordenação do serviço foi comparada com o ranking completo do experimento
offline nas 1.207 consultas de teste, utilizando o cache de candidatos coletado.
Os rankings completos coincidiram em todas essas consultas.

A implementação das métricas segue a documentação do
[RapidFuzz](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html) e da
[distância de Damerau-Levenshtein](https://rapidfuzz.github.io/RapidFuzz/Usage/distance/DamerauLevenshtein.html).
Os parâmetros do classificador seguem a documentação do
[scikit-learn 1.7](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.RandomForestClassifier.html).
