# Ranking por similaridade para recuperação de nomes de logradouros históricos no Pauliceia

**Primeira versão para revisão — 22/11/2026.**

Pedro Henrique Ito Boa Sorte · Daniela Leal Musa  
Universidade Federal de São Paulo — Instituto de Ciência e Tecnologia  
E-mails pendentes.

Esta cópia facilita a leitura. O arquivo de diagramação é `main.tex`; a contagem final de páginas depende da compilação em LaTeX.

## Resumo

A recuperação de nomes de logradouros em bases históricas precisa tolerar diferenças de escrita sem confundir nomes semelhantes. Este trabalho avaliou uma arquitetura de duas etapas no Pauliceia: recuperação de até 100 candidatos com BM25 e trigramas de caracteres, seguida de reordenação por Random Forest com sete atributos de similaridade. Um catálogo de 853 registros, correspondentes a 847 nomes normalizados, originou 6.136 consultas, incluindo 5.289 variantes sintéticas. A separação por grupos de nomes reservou 1.207 consultas para teste. Nesse conjunto, o acerto na primeira posição passou de 63,55% com BM25 para 97,02% com trigramas e 100,00% com Random Forest. Em comparação adicional, Token Set alcançou 98,59%. Um conjunto exploratório de 179 consultas, com dez grafias documentadas e 169 variantes simuladas, produziu empate entre Random Forest e Damerau–Levenshtein. A integração local ao portal apresentou mediana de 14,97 ms em 336 buscas medidas; 219 controles de pontos concordaram com o backup. Os resultados sustentam o benefício da combinação de medidas para as transformações e o catálogo avaliados. Não estabelecem acurácia universal nem validação histórica independente das correspondências e coordenadas.

**Palavras-chave:** recuperação de informação; toponímia histórica; similaridade textual; Random Forest; Pauliceia.

## Introdução

O projeto Pauliceia 2.0 articula pesquisa histórica, informação geográfica e colaboração para o mapeamento da história de São Paulo. Ferla et al. [1] apresentam sua concepção como uma iniciativa de código aberto associada às humanidades digitais, à história pública e à ciência aberta. Nesse contexto, localizar um endereço envolve relacionar a expressão fornecida pelo pesquisador aos registros disponíveis e, posteriormente, consultar a informação espacial e temporal correspondente. A recuperação do nome é, portanto, uma etapa importante para o acesso ao acervo georreferenciado.

Os nomes presentes em um cadastro podem diferir da consulta por acentuação, abreviações, omissões, transposições e outras alterações de escrita. Há também grafias distintas registradas em fontes documentais. A igualdade literal é insuficiente para acomodar essas diferenças. Por outro lado, aceitar indiscriminadamente nomes parecidos pode aproximar logradouros distintos, sobretudo quando compartilham parte das palavras. O problema investigado consiste em ordenar os nomes candidatos para favorecer a referência esperada, sem assumir que semelhança textual comprova identidade geográfica ou histórica.

Na recuperação lexical, BM25 atribui escores aos documentos a partir da correspondência entre termos, com tratamento de frequência e comprimento [2]. Essa representação pode perder evidência quando uma pequena alteração modifica um termo inteiro. A indexação adicional por trigramas permite compartilhar fragmentos de caracteres entre expressões diferentes. Contudo, recuperar a referência entre os candidatos e colocá-la na primeira posição são objetivos distintos: uma lista pode ter cobertura adequada e ainda exigir que o usuário procure a opção correta em posições pouco visíveis.

A combinação de similaridades já possui antecedentes na literatura. Santos, Murrieta-Flores e Martins [3] avaliaram medidas textuais para correspondência de topônimos e sua combinação por aprendizado supervisionado, com resultados favoráveis a conjuntos de árvores de decisão. Esse antecedente fundamenta a abordagem, mas não determina seu desempenho no catálogo e nas consultas do Pauliceia. Nosso estudo investiga essa aplicação por meio de recuperação em duas etapas, avaliação por posição e integração a um portal existente. Não propõe a combinação supervisionada de medidas como uma técnica inédita.

A pergunta de pesquisa é: *em que medida a reordenação supervisionada de candidatos recuperados por BM25 e trigramas melhora a recuperação de nomes de logradouros no recorte disponível do Pauliceia?* Para respondê-la, comparamos BM25, BM25 com trigramas e Random Forest em consultas separadas por grupos de nomes. Também comparamos reordenadores baseados em uma única similaridade e examinamos um conjunto complementar de grafias documentadas e transformações simuladas. A avaliação da integração verificou a correspondência das sugestões com o processamento offline, a entrega dos pontos cadastrados e a latência HTTP local.

As contribuições são a implementação reproduzível dessa arquitetura no protótipo local, a comparação empírica dos métodos no catálogo estudado e a explicitação dos limites entre recuperação textual, atendimento pelo portal e validação histórica. No teste reservado, a reordenação corrigiu as 36 falhas de primeira posição dos trigramas. Já no complemento, uma medida isolada empatou com o modelo supervisionado. Esses resultados motivam uma análise das condições em que a combinação ajuda, sem generalizar o desempenho observado para toda a documentação histórica ou para consultas reais ainda não avaliadas.


## Metodologia

### Delineamento, catálogo e relevância

Realizamos um estudo experimental de recuperação textual, seguido de avaliações complementares e validação funcional do protótipo. Utilizamos uma cópia local do banco disponibilizado para o projeto. Dos 873 registros de logradouros, excluímos cinco sem nome e 15 com marcadores genéricos, como “nao oficial” e “n.o”. O índice resultante contém 853 registros e 847 nomes normalizados. Trata-se do recorte disponível nesse backup, sem pressupor cobertura integral do acervo Pauliceia, dos séculos XIX e XX ou dos livros de emplacamento mencionados no planejamento.

A normalização para agrupamento e cálculo das similaridades aplicou decomposição Unicode NFD, remoção de marcas de acentuação, conversão por `casefold` e regularização dos espaços. Mantivemos os nomes originais para exibição e não modernizamos suas grafias no cadastro. Cada consulta recebeu como relevantes todos os IDs com o mesmo nome normalizado de sua referência. Essa decisão avalia a correspondência textual: registros homônimos podem representar situações espaciais diferentes, que o nome isolado não resolve.

### Consultas e separação dos dados

O conjunto principal reuniu 6.136 consultas: 847 nomes do cadastro e 5.289 variantes sintéticas. Geramos variantes de normalização, abreviação do tipo de logradouro, omissão, substituição, inserção e transposição de caracteres, duas omissões em palavras distintas e inversão da ordem das palavras após o primeiro termo. As posições de edição foram determinadas por hash e semente fixa. A substituição utilizou a letra seguinte no alfabeto e a inserção repetiu um caractere. Portanto, esses exemplos representam perturbações controladas; não reproduzem frequências observadas de erros de teclado, OCR ou uso real.

As regras tiveram condições de aplicação, de modo que nem todo nome recebeu todas as variantes. O gerador removeu uma repetição e verificou colisões entre consultas e referências distintas; não houve exclusões por ambiguidade nessa execução. As nove categorias totalizaram 847 originais, 22 normalizações, 834 abreviações, 834 omissões, 834 substituições, 834 inserções, 834 transposições, 491 casos de duas omissões e 606 inversões de ordem.

Para reduzir a transferência de variantes relacionadas entre partições, agrupamos nomes após normalização, desconsiderando a ordem das palavras e os sufixos de lado par/ímpar. Reservamos os seis grupos utilizados no piloto para desenvolvimento. Os demais foram ordenados por hash com a semente `pauliceia-tcc-v1` e distribuídos aproximadamente em 60% para treino, 20% para validação e 20% para teste. A Tabela 1 apresenta as quantidades efetivas. Consultas do conjunto de desenvolvimento não participaram do ajuste nem da seleção do modelo.



**Tabela 1. Separação do conjunto principal por grupos de nomes.**

| Partição | Grupos | Nomes | Consultas |
| –- | –- | –- | –- |
| Desenvolvimento | 6 | 6 | 43 |
| Treino | 496 | 505 | 3681 |
| Validacao | 166 | 169 | 1205 |
| Teste | 166 | 167 | 1207 |



O índice manteve o catálogo completo em todas as etapas, porque recuperar um nome exige que ele esteja indexado. A separação incidiu sobre os grupos de consultas e seus rótulos para ajuste e seleção, não sobre a disponibilidade dos documentos candidatos. Consequentemente, nomes associados às consultas de teste podem aparecer como candidatos negativos em consultas de treino. O classificador recebeu medidas numéricas de similaridade, sem IDs ou nomes como atributos categóricos. O protocolo avalia generalização para novos grupos de consultas dentro de um catálogo fixo, não para outro catálogo.

### Recuperação de candidatos

Configuramos o Elasticsearch 8.19.4 com um fragmento primário e sem réplicas. O campo de palavras utilizou tokenização `standard`, conversão para minúsculas e `asciifolding`. Um segundo campo acrescentou um filtro de n-gramas com tamanho mínimo e máximo iguais a três, aplicado aos tokens. Ambos usaram BM25 com os parâmetros padrão, $k_1=1{,}2$ e $b=0{,}75$ [2].

A referência BM25 consultou apenas o campo de palavras. A alternativa BM25 com trigramas utilizou `multi_match` do tipo `most_fields`, combinando os escores dos dois campos sem pesos adicionais [4]. Cada método recuperou até 100 candidatos, ordenados por escore decrescente e ID crescente no desempate. O limite foi mantido nos experimentos e no serviço, sem busca posterior por valores alternativos. BM25 e trigramas podem produzir conjuntos distintos; todos os reordenadores operaram sobre a mesma lista obtida pelos trigramas.

### Similaridades e reordenação supervisionada

Representamos cada par consulta–candidato por sete atributos: similaridades normalizadas de Damerau–Levenshtein, Jaro–Winkler e Levenshtein; Token Sort e Token Set divididos por 100; escore do Elasticsearch dividido pelo maior escore da consulta; e razão entre o menor e o maior comprimento das strings. Usamos RapidFuzz 3.14.3 e matrizes `float32`, com as mesmas funções no experimento e no serviço online.

Damerau–Levenshtein considera operações de edição, incluindo transposições adjacentes; sua similaridade normalizada utiliza o maior comprimento como referência [5]. Token Sort ordena as palavras antes da comparação, enquanto Token Set considera palavras únicas e comuns. Essas funções empregam a similaridade Indel normalizada do RapidFuzz, e não devem ser descritas simplesmente como distância de Levenshtein sobre tokens [6]. As diferentes representações fornecem sinais que podem responder de maneira distinta a alterações locais e à ordem das palavras.

Treinamos um Random Forest, família de modelos baseada na combinação de árvores [7], para classificar pares como relevantes ou não relevantes. A implementação `RandomForestClassifier`, do scikit-learn 1.7.2 [8], recebeu 347.363 pares, dos quais 3.678 relevantes. Cada par teve peso inversamente proporcional ao número de candidatos de sua consulta, e as classes foram balanceadas em cada amostra bootstrap com `balanced_subsample`. A diferença entre consultas e pares positivos decorre da quantidade de relevantes recuperados, que pode ser nula ou maior que um.

Fixamos 200 árvores e semente 42. A grade combinou profundidade máxima 12 ou ilimitada com mínimo de dois ou cinco exemplos por folha; os demais parâmetros permaneceram nos padrões da versão registrada. Selecionamos a configuração pelo maior MRR médio por nome na validação, com desempate pelo acerto na primeira posição por nome e, depois, pela ordem da grade. O modelo selecionado teve profundidade 12 e mínimo de dois exemplos por folha. O treinamento usou até quatro tarefas paralelas e a previsão uma tarefa, preservando a ordem de soma das árvores.

A saída da classe relevante em `predict_proba` foi utilizada como escore de ordenação, sem assumir calibração probabilística. Empates conservaram a ordem dos trigramas. O modelo foi serializado, e as previsões antes e depois da leitura do arquivo foram comparadas. Após a seleção pela validação, o modelo permaneceu congelado para o teste e as avaliações adicionais.

Como comparadores adicionais, reordenamos os candidatos por Damerau–Levenshtein, Jaro–Winkler, Token Sort e Token Set individualmente, com o mesmo desempate. Essa comparação foi acrescentada após a observação do teste original, sem retreinamento, novos pesos ou escolha de hiperparâmetros. Ela compara métodos finais; não constitui remoção controlada de atributos do Random Forest, que recebe sete medidas.

### Métricas de recuperação

Para uma consulta $q$, sejam $G_q$ o conjunto de IDs relevantes e $L_q^k$ os IDs nas primeiras $k$ posições. Calculamos o acerto em $k$ posições, a precisão e a cobertura:

$$
\begin{aligned}
 H@k(q) &= \mathbf{1}[G_q\cap L_q^k\ne\varnothing],\\
 P@k(q) &= \frac{|G_q\cap L_q^k|}{k},\\
 R@100(q) &= \frac{|G_q\cap L_q^{100}|}{|G_q|}.
\end{aligned}
$$

O recíproco da posição do primeiro relevante, limitado aos 100 candidatos, foi definido por

$$

 RR@100(q)=\begin{cases}1/r_q,&r_q\leq100,\\0,&\text{sem relevante recuperado},\end{cases}

$$

em que $r_q$ é a primeira posição relevante. MRR@100 corresponde à média de $RR@100$. Reportamos Top-1 como a média de $H@1$, além de $H@3$, $H@5$, $P@1$, $P@3$, $P@5$ e Recall@100. Uma consulta sem alvo entre os candidatos continuou contribuindo com zero para acerto e MRR. A reordenação não introduziu IDs ausentes.

As tabelas principais usam médias por consulta. Também preservamos médias por nome e resultados por transformação. Acerto@K e Precision@K têm interpretações diferentes: encontrar uma referência entre cinco sugestões não torna todas as cinco relevantes. As comparações de ganhos e perdas são descritivas, sem testes de significância ou intervalos de confiança. As variantes de uma mesma referência não são observações independentes para inferência estatística.

### Avaliação complementar e fontes documentais

Após o teste original, construímos um complemento exploratório de 179 consultas referentes a 168 nomes: 90 variantes históricas simuladas, 79 fonéticas simuladas e dez grafias documentadas. As simulações aplicaram substituições textuais controladas. O grupo chamado fonético não resulta de gravações de fala ou validação fonológica, e o grupo histórico simulado não corresponde a ocorrências documentais verificadas para cada transformação.

As dez consultas documentadas foram associadas a sete fontes municipais digitais. As ementas da Lei 1.734/1913 e do Ato 3.330/1930 registram, respectivamente, Higienópolis e Teodoro Sampaio [9, 10]. Outras fontes registram Santa Ifigênia [11], Artur Azevedo [12], Bela Cintra, Barão de Tatuí, Humaitá e Triunfo [13], Travessa do Comércio [14] e Beco dos Aflitos [15]. O manifesto preservou URL, trecho localizador, consulta e ID associado.

A evidência documental atesta a ocorrência da grafia consultada. O vínculo dessa grafia ao ID do backup foi uma inferência textual sem revisão histórica independente. Ementas digitais de normas antigas podem refletir modernizações editoriais; a data da norma não foi tratada como comprovação da grafia no documento original. Não inferimos continuidade da extensão física da rua a partir dessas ocorrências.

O complemento incluiu nomes de diferentes partições e sete consultas já presentes nos conjuntos anteriores, incluindo o piloto. Identificamos separadamente 32 consultas novas ligadas a nomes do teste original. Nenhuma dessas avaliações foi usada para modificar o modelo. A construção posterior e a exposição anterior de parte dos nomes impedem tratar as 179 consultas como um novo teste independente.

### Integração e validação do portal

O portal local passou a apresentar cinco sugestões com nome e ID após a recuperação de 100 candidatos e a reordenação. O usuário seleciona uma rua e informa número e ano; a API consulta os pontos cadastrados no PostgreSQL/PostGIS. O novo fluxo não interpola coordenadas. Os intervalos temporais são inclusivos; ano final nulo ou zero é interpretado como 2000, convenção herdada da API e não evidência histórica adicional.

A arquitetura usou Elasticsearch para recuperação e um serviço Python para similaridades e previsão. O planejamento inicial previa Painless no indexador; essa implementação não foi realizada. O serviço Python permitiu compartilhar funções, versões e representação numérica com o experimento, evitando uma segunda implementação cuja equivalência precisaria ser verificada. Não comparamos desempenho de Python com Painless. O serviço carrega o modelo uma vez, verifica sua assinatura e fornece identificação do modelo na resposta; indisponibilidade resulta em erro explícito.

A amostra de latência foi fixada antes da medição: 112 consultas, sendo 82 do teste e 30 do complemento. Após uma chamada de aquecimento por consulta, executamos três rodadas sequenciais, totalizando 336 buscas medidas. O cronômetro monotônico abrangeu a requisição HTTP pelo proxy local, o processamento e a leitura do JSON. A busca incluiu API, Elasticsearch, similaridades e previsão. Foram usadas novas conexões HTTP, sem concorrência. O P95 foi calculado por interpolação linear na posição $(n-1)\times0{,}95$ dos tempos ordenados.

Para a verificação espacial, um leitor independente da rota extraiu coordenadas e intervalos do backup. Dos 5.872 registros de pontos, 20 não tinham geometria ou ano inicial necessários, restando 5.852 no oráculo. Um registro com ano inicial 199 foi sinalizado e preservado, sem correção presumida; endereços associados a essa anomalia não serviram como âncoras da seleção temporal. Os 219 controles incluíram 103 respostas com coordenadas e 116 vazias, abrangendo 37 ruas e um ID inexistente. Houve nove casos com múltiplas coordenadas e 21 com numeração decimal. A comparação usou conjuntos de coordenadas, sem dependência da ordem, e tolerância de $10^{-9}$ grau por componente.

Também executamos três rodadas de 20 fluxos compostos por busca, seleção explícita do ID esperado entre as sugestões e consulta de pontos. Os 60 fluxos não representam 60 endereços independentes. A medição excluiu renderização do navegador, digitação e decisão humana. A verificação espacial avaliou fidelidade ao backup, sem levantamento externo para medir erro geográfico em metros.

### Ambiente e rastreabilidade

O ambiente local utilizou contêineres Linux, PostgreSQL 16/PostGIS 3.5, Elasticsearch 8.19.4 e API Node.js 22, integrada à interface Vue/OpenLayers. O treinamento registrou Python 3.13.3, NumPy 2.2.5, scikit-learn 1.7.2 e RapidFuzz 3.14.3. O cliente da medição HTTP registrou Windows 11 e 16 processadores lógicos; modelo de CPU, memória e recursos atribuídos aos contêineres não foram registrados no protocolo. Os tempos devem ser interpretados nesse limite de caracterização do ambiente.

Os artefatos locais incluem consultas, partições, candidatos, escores, métricas individuais, parâmetros, versões e hashes das entradas e do modelo. As avaliações adicionais reutilizaram os candidatos salvos e verificaram a reprodução dos resultados anteriores. Essa rastreabilidade permite conferir as tabelas e repetir os procedimentos com os mesmos arquivos, sem implicar publicação de todo o banco de origem.


## Resultados

### Seleção e teste reservado

Na validação, com 1.205 consultas, BM25 apresentou Top-1 de 60,50%, e a inclusão dos trigramas elevou esse resultado para 95,19%. As quatro configurações de Random Forest tiveram Top-1 de 99,42% e MRR por nome de 0,9942. O desempate selecionou a primeira configuração da grade. Em relação aos trigramas, o modelo acrescentou 52 acertos de primeira posição e perdeu um; portanto, o desempenho na validação não foi perfeito.

No teste reservado, os trigramas elevaram a cobertura média dos relevantes nos 100 candidatos de 86,50% para 100,00%. A Tabela 2 apresenta os resultados de recuperação e reordenação. BM25 acertou 767 das 1.207 consultas na primeira posição, os trigramas acertaram 1.171 e o Random Forest acertou 1.207. O modelo corrigiu as 36 falhas restantes dos trigramas, sem perdas, aumentando Top-1 em 2,98 pontos percentuais. Não houve alvo ausente dos candidatos dos trigramas nesse teste.



**Tabela 2. Teste reservado: médias por consulta (1.207 consultas).**

| Método | Top-1 (%) | R@100 (%) | MRR@100 |
| –- | –- | –- | –- |
| BM25 | 63,55 | 86,50 | 0,6889 |
| BM25 + trigramas | 97,02 | 100,00 | 0,9808 |
| Damerau–Levenshtein | 91,80 | 100,00 | 0,9264 |
| Jaro–Winkler | 95,36 | 100,00 | 0,9670 |
| Token Sort | 98,18 | 100,00 | 0,9854 |
| Token Set | 98,59 | 100,00 | 0,9923 |
| Random Forest | 100,00 | 100,00 | 1,0000 |

As quatro similaridades isoladas foram comparadas após o teste original, sem modificar o modelo.



Na comparação adicional das similaridades isoladas, Token Set obteve o maior Top-1, com 1.190 acertos. O Random Forest acrescentou 17 acertos em relação a esse método, diferença de 1,41 ponto percentual. Token Sort, Jaro–Winkler e Damerau–Levenshtein alcançaram, respectivamente, 1.185, 1.151 e 1.108 acertos. Todos os reordenadores conservaram Recall@100 de 100,00%, pois compartilharam os candidatos dos trigramas.

A média por nome preservou a tendência: Top-1 foi 61,59% para BM25, 96,89% para trigramas e 100,00% para Random Forest. Isso reduz a possibilidade de que a comparação principal seja explicada apenas pela quantidade desigual de variantes por nome, embora não substitua uma avaliação em novos dados.

### Posições iniciais e tipos de transformação

A Tabela 3 distingue a presença de um relevante nas posições iniciais da proporção de relevantes nessas posições. Com Random Forest, Acerto@3 e Acerto@5 foram 100,00%, enquanto Precision@3 e Precision@5 foram 33,66% e 20,20%. Esses valores são compatíveis com consultas que geralmente têm apenas um ID relevante. Não representam uma queda do acerto da primeira sugestão para 20%.



**Tabela 3. Posições iniciais no teste: acerto (H) e precisão (P), em porcentagem.**

| Método | H@3 | H@5 | P@3 | P@5 |
| –- | –- | –- | –- | –- |
| BM25 | 72,91 | 76,14 | 24,41 | 15,29 |
| BM25 + trigramas | 99,09 | 99,50 | 33,36 | 20,10 |
| Damerau–Levenshtein | 92,71 | 93,70 | 31,23 | 18,94 |
| Jaro–Winkler | 97,85 | 98,26 | 32,95 | 19,85 |
| Token Sort | 98,59 | 98,92 | 33,20 | 19,98 |
| Token Set | 99,83 | 99,83 | 33,61 | 20,17 |
| Random Forest | 100,00 | 100,00 | 33,66 | 20,20 |



A Tabela 4 detalha o comportamento por transformação. No conjunto de 167 consultas originais, todos os métodos acertaram a primeira posição. As diferenças apareceram nas variantes. Os trigramas falharam em 17 transposições, nove casos de duas omissões, cinco substituições, quatro omissões e uma abreviação. O Random Forest corrigiu esses casos.



**Tabela 4. Top-1 por transformação no teste (%).**

| Transformação | n | BM25 | Tri. | DL | RF |
| –- | –- | –- | –- | –- | –- |
| Original | 167 | 100,00 | 100,00 | 100,00 | 100,00 |
| Normalização | 2 | 100,00 | 100,00 | 100,00 | 100,00 |
| Abreviação | 166 | 98,19 | 99,40 | 98,80 | 100,00 |
| Omissão | 165 | 47,88 | 97,58 | 100,00 | 100,00 |
| Substituição | 165 | 47,27 | 96,97 | 100,00 | 100,00 |
| Inserção | 165 | 46,67 | 100,00 | 100,00 | 100,00 |
| Transposição | 165 | 46,67 | 89,70 | 100,00 | 100,00 |
| Duas omissões | 97 | 9,28 | 90,72 | 100,00 | 100,00 |
| Ordem | 115 | 100,00 | 100,00 | 15,65 | 100,00 |

Tri.: BM25 com trigramas; DL: Damerau–Levenshtein; RF: Random Forest.



Das 99 falhas de Damerau–Levenshtein, 97 ocorreram na inversão da ordem de palavras e duas em abreviações. Jaro–Winkler apresentou 44 falhas de ordem, nove de abreviação, uma de omissão e duas de duas omissões. Token Set distribuiu suas 17 falhas entre omissão, transposição, substituição, inserção e duas omissões, sem falhar na categoria de ordem. Esses padrões mostram diferenças de sensibilidade entre as representações.

Um exemplo foi a consulta *rua ameli sa barbosa*. Token Set colocou *rua sa barbosa* antes da referência *rua amelia sa barbosa*; o Random Forest colocou a referência em primeiro. Outro caso, *rua cotsa*, teve a referência *rua costa* recuperada na posição 76 pelos trigramas e promovida para a primeira posição pelo modelo. Os exemplos ilustram ganhos de ordenação dentro de candidatos já recuperados.

### Complemento exploratório

A Tabela 5 separa as três categorias complementares. Random Forest e Damerau–Levenshtein acertaram as 179 consultas na primeira posição. Nas dez grafias documentadas, os trigramas e todos os reordenadores já atingiram 100,00%; BM25 atingiu 20,00%. Esse grupo não demonstrou ganho adicional do modelo sobre os trigramas.



**Tabela 5. Top-1 no complemento exploratório (%).**

| Método | Doc. (10) | Hist. (90) | Fon. (79) |
| –- | –- | –- | –- |
| BM25 | 20,00 | 44,44 | 69,62 |
| BM25 + trigramas | 100,00 | 93,33 | 92,41 |
| Damerau–Levenshtein | 100,00 | 100,00 | 100,00 |
| Jaro–Winkler | 100,00 | 100,00 | 97,47 |
| Token Sort | 100,00 | 98,89 | 89,87 |
| Token Set | 100,00 | 94,44 | 98,73 |
| Random Forest | 100,00 | 100,00 | 100,00 |

Doc.: grafias documentadas; Hist. e Fon.: variantes históricas e fonéticas simuladas.



Nas variantes históricas simuladas, os trigramas tiveram Top-1 de 93,33% e MRR@100 de 0,9571. Nas fonéticas simuladas, os valores foram 92,41% e 0,9513. O Random Forest corrigiu seis falhas de cada categoria, sem perdas. O Recall@100 do BM25 foi 90,00% no grupo histórico simulado e 100,00% nos outros dois; trigramas e reordenadores tiveram cobertura completa nas três categorias.

No recorte de 32 consultas novas associadas a nomes do teste original, os trigramas acertaram 30 e o Random Forest 32. Esse resultado permanece exploratório, pois o conjunto foi elaborado depois da avaliação principal. O empate de Damerau–Levenshtein com o modelo no complemento contrasta com sua dificuldade nas inversões de ordem do teste reservado.

### Correspondência funcional, espacial e latência

Os rankings completos produzidos pela função utilizada no serviço coincidiram com o processamento offline nas 1.207 consultas do teste, usando o cache de candidatos. Na validação HTTP ao vivo, as cinco sugestões e o identificador do modelo coincidiram com as referências nas 336 buscas medidas. As 112 chamadas de aquecimento também passaram e foram contabilizadas separadamente.

Os 219 controles espaciais concordaram com o backup, incluindo respostas vazias, múltiplos pontos e números decimais. Os 60 fluxos de duas chamadas também passaram. A Tabela 6 apresenta os tempos medidos. A busca teve mediana de 14,97 ms; o fluxo de busca e obtenção dos pontos teve mediana de 20,58 ms e P95 de 46,99 ms.



**Tabela 6. Validação local: verificações e tempos HTTP em ms.**

| Etapa | Corretas | Mediana | P95 | Média |
| –- | –- | –- | –- | –- |
| Busca | 336/336 | 14,97 | 33,09 | 18,85 |
| Pontos | 219/219 | 3,92 | 22,54 | 6,60 |
| Busca + pontos | 60/60 | 20,58 | 46,99 | 27,06 |

Busca: 112 consultas em três rodadas. Fluxos: 20 casos em três rodadas. Aquecimento excluído.



Não houve falhas ou interrupções nessa coleta. Esses resultados demonstram consistência do protótipo local com suas referências e atendimento rápido nas condições sequenciais avaliadas. Não incluem desenho do mapa nem estimam comportamento sob carga ou em acesso remoto.


## Discussão

### Contribuição das duas etapas

Os resultados separam dois efeitos. A inclusão de trigramas ampliou a disponibilidade dos relevantes e produziu a maior parte do ganho sobre a busca por palavras. A reordenação supervisionada atuou sobre as referências recuperadas que ainda estavam em posições inadequadas. Essa distinção é operacionalmente importante: o classificador não consegue corrigir uma ausência na lista inicial. O Recall@100 completo no teste possibilitou o Top-1 completo do Random Forest, mas essa condição não é garantida em outro catálogo ou em consultas diferentes.

O ganho de 36 consultas sobre trigramas é relevante para uma interface que apresenta poucas sugestões. A promoção de *rua costa* da posição 76 para a primeira exemplifica a diferença entre uma referência tecnicamente recuperada e uma opção visível ao usuário. Contudo, a seleção da rua continua explícita. O escore não certifica que o logradouro corresponde ao local pretendido, e não foi estabelecido um limiar de confiança para rejeitar automaticamente consultas sem correspondência.

O melhor desempenho da combinação sobre as medidas isoladas no teste é compatível com a motivação de Santos et al. [3]. Essa compatibilidade é conceitual, sem comparação direta de valores entre estudos, que empregam dados e protocolos distintos. Neste trabalho, a evidência diz respeito à ordenação de candidatos de um catálogo específico. A comparação não identifica qual atributo causou o ganho nem demonstra que o Random Forest é a única combinação capaz de produzi-lo.

### A distribuição das consultas altera a comparação

A queda de Damerau–Levenshtein nas inversões de ordem evidencia uma propriedade do conjunto principal: parte das variantes modifica a sequência global de caracteres preservando as palavras. Medidas que reorganizam tokens acomodam esse tipo de transformação. A presença de 115 consultas dessa categoria no teste influencia a diferença agregada entre os métodos; não sabemos sua frequência nas buscas de pesquisadores.

No complemento, Damerau–Levenshtein empatou com o Random Forest. Nas dez grafias documentadas, os próprios trigramas foram suficientes para colocar a referência em primeiro. Assim, os resultados não sustentam a necessidade do aprendizado de máquina em todo recorte. O modelo reuniu desempenho alto nos diferentes tipos do conjunto principal, mas uma solução mais simples pode ser adequada quando as transformações de interesse são mais restritas. Uma decisão de implantação deve considerar essa diferença junto ao custo operacional, que não foi comparado por método.

Os 100% de Top-1 são uma observação sobre 1.207 consultas reservadas, não uma estimativa de ausência de erro em uso geral. O protocolo de grupos reduz compartilhamento direto de variantes entre treino e teste, porém todas as partições foram produzidas pelas mesmas regras de transformação e pelo mesmo catálogo. Um modelo pode aprender regularidades desse gerador que não representem os erros encontrados em documentos ou consultas reais. A inclusão de candidatos negativos do catálogo completo também delimita a generalização avaliada.

### Alcance histórico e espacial

As consultas documentadas acrescentam evidência de uso de grafias em fontes municipais, mas sua quantidade é pequena e sua seleção não constitui amostragem representativa de períodos, regiões ou tipos documentais. A relação com os IDs foi inferida sem revisão independente. Além disso, não se pode atribuir à grafia de uma ementa digital a mesma data e fidelidade paleográfica do ato original. O conjunto permite avaliar a resposta do mecanismo às expressões selecionadas; não valida integralmente a evolução histórica dos nomes.

A distinção se estende às geometrias. Os controles espaciais confirmaram que a API aplica filtros de ID, número e ano de forma compatível com o backup. Como a referência provém desse mesmo banco, a concordância não estabelece exatidão do cadastro em relação ao espaço histórico. Homônimos, mudanças de numeração, alterações de traçado e a própria qualidade das coordenadas demandam fontes externas. A anomalia temporal identificada e a convenção de ano final 2000 reforçam a necessidade de separar consistência computacional e validade histórica.

O artigo, portanto, descreve um componente de recuperação e acesso a pontos cadastrados. Não avalia o algoritmo legado de interpolação, não reconstrói todos os lotes e não substitui o trabalho de curadoria histórica. Essa delimitação preserva a contribuição computacional sem atribuir aos testes evidências que eles não produziram.

### Validade, implantação e próximos estudos

As principais limitações são o catálogo único, a predominância de variantes sintéticas, o gabarito de relevância textual e a ausência de consultas reais e exemplos sem correspondência. A seleção de uma única partição e de uma única semente de treinamento também restringe a avaliação de estabilidade. As análises por consulta e por nome ajudam a caracterizar o desempenho, mas as diferenças permanecem descritivas. Não foram testadas outras famílias de classificadores nem realizada ablação dos sete atributos.

A comparação das métricas isoladas e o complemento ocorreram depois do conhecimento do teste original. O modelo permaneceu congelado, preservando o resultado anterior, mas isso não transforma as avaliações posteriores em confirmação independente. Novos conjuntos devem ser definidos antes da observação de seus resultados, com curadoria separada e regras de amostragem que representem o uso pretendido.

Na integração, compartilhar funções e conferir o modelo reduziu divergências entre experimento e serviço. A latência local observada indica que a implementação em Python foi utilizável no ambiente testado, sem demonstrar superioridade sobre Painless. A caracterização incompleta do hardware, a execução sequencial, o aquecimento e a ausência de renderização limitam comparações de desempenho. Uma implantação mais ampla requer medições com recursos registrados, concorrência, acesso remoto e instrumentação do navegador.

Como continuidade, propomos coletar consultas reais com referência revisada, avaliar documentos históricos transcritos e erros de OCR observados, incorporar contexto temporal e espacial para homônimos e testar consultas ausentes do catálogo. Também são pertinentes uma comparação de custo entre reordenadores, validação externa em outro recorte e análise da contribuição dos atributos. Essas etapas podem esclarecer se os ganhos se mantêm quando a distribuição das consultas se afasta das transformações controladas deste estudo.


## Conclusão

Concluímos que a arquitetura de recuperação por BM25 e trigramas seguida de reordenação supervisionada melhora a priorização de nomes de logradouros para o catálogo e as transformações avaliados no Pauliceia. Os trigramas ampliam a cobertura dos candidatos, e o Random Forest corrige as 36 falhas de primeira posição restantes no teste reservado. A comparação adicional indica ganho de 17 acertos sobre Token Set, o melhor comparador isolado nesse conjunto.

O empate com Damerau–Levenshtein no complemento mostra que o benefício adicional depende das características das consultas. A contribuição é uma implementação integrada e uma avaliação reproduzível dessa combinação, com distinção entre correspondência textual e comprovação histórica. A validação local confirma a entrega das sugestões e dos pontos cadastrados nas condições testadas. A extensão das conclusões para uso real exige consultas e correspondências históricas verificadas de forma independente.


## Referências

1. Luis Ferla; Karine Reis Ferreira; Fernando Atique; Andrew G. Britt; Karla Donato Fook; Jeffrey Lesser; Cristiane Miyasaka; Daniela Musa; Thomas D. Rogers; Nandamudi Vijaykumar. Pauliceia 2.0: mapeamento colaborativo da história de São Paulo, 1870–1940. História, Ciências, Saúde–Manguinhos. v. 27. n. 4. p. 1207–1223. 2020. [Fonte](https://doi.org/10.1590/S0104-59702020000500010).

2. Elastic. Similarity module. Elasticsearch Guide 8.19. [Fonte](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/index-modules-similarity.html). Acesso em: 22 nov. 2026.

3. Rui Santos; Patricia Murrieta-Flores; Bruno Martins. Learning to combine multiple string similarity metrics for effective toponym matching. International Journal of Digital Earth. v. 11. n. 9. p. 913–938. 2018. [Fonte](https://doi.org/10.1080/17538947.2017.1371253).

4. Elastic. Multi-match query. Elasticsearch Guide 8.19. [Fonte](https://www.elastic.co/guide/en/elasticsearch/reference/8.19/query-dsl-multi-match-query.html). Acesso em: 22 nov. 2026.

5. RapidFuzz. Damerau Levenshtein. Documentação da biblioteca. [Fonte](https://rapidfuzz.github.io/RapidFuzz/Usage/distance/DamerauLevenshtein.html). Acesso em: 22 nov. 2026. Versão utilizada no experimento: 3.14.3.

6. RapidFuzz. rapidfuzz.fuzz. Documentação da biblioteca. [Fonte](https://rapidfuzz.github.io/RapidFuzz/Usage/fuzz.html). Acesso em: 22 nov. 2026. Versão utilizada no experimento: 3.14.3.

7. Leo Breiman. Random Forests. Machine Learning. v. 45. p. 5–32. 2001. [Fonte](https://doi.org/10.1023/A:1010933404324).

8. scikit-learn. RandomForestClassifier. Documentação 1.7.2. [Fonte](https://scikit-learn.org/1.7/modules/generated/sklearn.ensemble.RandomForestClassifier.html). Acesso em: 22 nov. 2026.

9. São Paulo (Município). Lei n. 1.734, de 23 de agosto de 1913. Catálogo de Legislação Municipal, ementa digital. 1913. [Fonte](https://legislacao.prefeitura.sp.gov.br/lei-1734-de-23-de-agosto-de-1913). Acesso em: 22 nov. 2026.

10. São Paulo (Município). Ato n. 3.330, de 18 de setembro de 1930. Catálogo de Legislação Municipal, ementa digital. 1930. [Fonte](https://legislacao.prefeitura.sp.gov.br/ato-gabinete-do-prefeito-3330-de-18-de-setembro-de-1930). Acesso em: 22 nov. 2026.

11. São Paulo Urbanismo. Rua dos Eletrônicos (Rua Santa Ifigênia). Gestão Urbana SP. [Fonte](https://gestaourbana.prefeitura.sp.gov.br/projetos-urbanos/ruas-tematicas/rua-dos-eletronicos-rua-santa-ifigenia/). Acesso em: 22 nov. 2026.

12. São Paulo (Município). Resolução n. 7, de 4 de novembro de 2003. CONPRESP, Catálogo de Legislação Municipal. 2003. [Fonte](https://legislacao.prefeitura.sp.gov.br/resolucao-secretaria-municipal-da-cultuura-conpre-7-de-4-de-novembro-de-2003/consolidado). Acesso em: 22 nov. 2026.

13. São Paulo (Município). Portaria SMSUB n. 40, de 27 de agosto de 2021. Catálogo de Legislação Municipal, texto consolidado. 2021. [Fonte](https://legislacao.prefeitura.sp.gov.br/portaria-secretaria-municipal-das-subprefeituras-smsub-40-de-27-de-agosto-de-2021/consolidado). Acesso em: 22 nov. 2026.

14. São Paulo (Município). Lei n. 1.552, de 27 de junho de 1912. Catálogo de Legislação Municipal, ementa digital. 1912. [Fonte](https://legislacao.prefeitura.sp.gov.br/lei-1552-de-27-de-junho-de-1912). Acesso em: 22 nov. 2026.

15. São Paulo Urbanismo. Prefeitura inicia obras para requalificar o bairro da Liberdade com calçadas mais largas, travessias seguras e novos espaços de permanência. Prefeitura de São Paulo. [Fonte](https://prefeitura.sp.gov.br/web/sp_urbanismo/w/prefeitura-inicia-obras-para-requalificar-o-bairro-da-liberdade-com-cal%C3%A7adas-mais-largas-travessias-seguras-e-novos-espa%C3%A7os-de-perman%C3%AAncia%C2%A0%C2%A0). Acesso em: 22 nov. 2026.

