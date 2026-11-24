# Decisões e limites a incorporar ao artigo

Este documento organiza a implementação realizada e os limites adotados no
artigo. A primeira versão já foi redigida no template fornecido, com sete páginas,
e está disponível em `docs/artigo.pdf` na raiz do repositório, para revisão.

## Implementação das métricas em Python

A proposta prevê Painless para incorporar métricas ao indexador. A implementação
real usa Elasticsearch para recuperar os candidatos e um serviço Python para
calcular similaridades e aplicar o Random Forest. Não foi implementada uma
versão equivalente das distâncias em Painless.

A escolha mantém as mesmas funções, normalização, versões das bibliotecas e
representação dos atributos no experimento e no serviço online. O serviço
carrega o modelo selecionado e confere sua assinatura. Isso evita manter uma
segunda implementação das métricas em outra linguagem, cuja equivalência
numérica teria de ser demonstrada separadamente.

A arquitetura de duas etapas e a combinação supervisionada das medidas foram
preservadas. A alteração da tecnologia deve ser explicitada no método e alinhada
com a orientadora. Não há evidência de que Python seja mais rápido que Painless:
essa comparação não foi realizada. A validação local do portal foi concluída:
a busca teve mediana de 14,97 ms e P95 de 33,09 ms em 336 requisições medidas.

## Unidade de avaliação e dados

O experimento principal avalia a recuperação de nomes em 853 registros, com
847 nomes normalizados. Os IDs que compartilham o mesmo nome normalizado são
considerados textualmente relevantes. A ambiguidade física de ruas homônimas
não é resolvida por essa definição.

O gabarito ampliado tem 6.136 consultas, compostas por nomes do catálogo e
transformações sintéticas. Os grupos foram separados para evitar que variantes
do mesmo grupo estivessem simultaneamente em treino e teste. O índice contém
o catálogo completo porque os nomes precisam existir para serem recuperados.
O teste reservado tem 1.207 consultas; o modelo foi escolhido pela validação.

O complemento de 179 consultas foi construído depois de conhecidos os resultados
do teste. É exploratório, inclui ruas de diferentes partições e identifica consultas
repetidas. Dez consultas têm grafias verificadas em fontes municipais digitais;
o vínculo ao ID no catálogo é inferência textual sem revisão histórica independente.
As outras são variações históricas ou fonéticas simuladas. Não são consultas reais
de usuários, erros de OCR observados ou transcrições de fala.

Os resultados não validam integralmente os séculos XIX e XX, todos os lotes ou
livros de emplacamento mencionados na proposta. O artigo deve descrever o recorte
do backup efetivamente usado e não supor representatividade de toda a base Pauliceia.

## Resultados e alegações sustentadas

O RF teve 100% de Top-1 no teste reservado, com 36 acertos adicionais em relação
aos trigramas. Na comparação posterior das métricas isoladas, Token Set chegou
a 98,59%; o RF teve 17 acertos adicionais, sem perdas nesse conjunto.

No complemento, Damerau-Levenshtein também teve 100% nas três categorias,
empatando com o RF. Nas dez grafias documentadas, os trigramas já tiveram 100%.
Portanto, não cabe afirmar que RF supera qualquer métrica em qualquer cenário,
nem que o acréscimo de aprendizado de máquina é necessário em todos os recortes.

Acerto@K informa a presença de algum relevante nos K primeiros resultados;
Precision@K informa a fração de resultados relevantes nessas K posições.
Ambas são calculadas, junto com Recall@100 e MRR@100. Médias por consulta e por
nome são preservadas, com resultados por tipo de transformação. As diferenças
relatadas são descritivas, sem teste de significância estatística.

O modelo continua congelado. Experimentos complementares não substituem nem
ampliam retroativamente o teste reservado. A comparação de métricas isoladas
não é uma remoção controlada de atributos do RF e não prova a contribuição causal
individual de cada atributo.

## Portal e geometrias

O protótipo foi integrado ao portal local. A busca sugere ruas com seus IDs e o
usuário seleciona uma delas antes de consultar os pontos por número e ano.
O novo fluxo consulta pontos cadastrados; o algoritmo legado de interpolação
permanece fora da avaliação ampliada.

A validação espacial compara a resposta do portal com coordenadas
lidas diretamente do backup. Ela testa a correspondência com os dados originais,
não a exatidão geográfica em relação a uma fonte externa. A medição de tempo
cobre HTTP pelo proxy do portal e o fluxo de duas chamadas, excluindo renderização
no navegador e interação humana. Os 219 controles espaciais concordaram com
o backup. Os 60 fluxos (três rodadas de 20 casos) passaram, com mediana de
20,58 ms e P95 de 46,99 ms. As 336 buscas medidas correspondem a três rodadas
de 112 consultas, após aquecimento. Não são observações de usuários reais ou
teste de concorrência. A execução e seus limites estão em `VALIDACAO_PORTAL.md`.
