# Primeira versão do artigo — 22/11/2026

O artigo foi redigido nas cinco seções do template fornecido, com resumo,
palavras-chave, seis tabelas derivadas dos resultados e 15 referências.
Mantivemos a classe `IEEEtran` em modo `conference`, em duas colunas, sem
reduzir fonte, margens ou espaçamento para forçar o limite de páginas.

## Arquivos

- `main.tex`: arquivo principal do artigo.
- `Secoes/`: introdução, metodologia, resultados, discussão e conclusão.
- `referencias.bib`: bibliografia utilizada, conferida em fontes primárias.
- `Tabelas/`: tabelas geradas dos resultados congelados.
- `LEITURA_ARTIGO.md`: cópia para leitura, sem a diagramação final IEEE.
- `artigo_primeira_versao.zip`: pacote gerado por `preparar_entrega.py`, não versionado.
- O ZIP original do template foi preservado na pasta de trabalho anterior e não integra esta publicação.
- `proveniencia_tabelas.json`: caminhos e hashes das entradas das tabelas.
- `gerar_tabelas.py`: regenera as tabelas no repositório, sem repetir experimentos.
- `preparar_entrega.py`: confere estrutura, gera leitura e empacota os fontes.

## Situação da compilação

O PDF foi compilado e tem **7 páginas**, dentro do limite de dez, incluindo
referências. A cópia para revisão está em `docs/artigo.pdf`, na raiz do
repositório; a conferência está registrada em `docs/verificacao_pdf.json`.
O log registrou avisos de substituição de fontes. O artigo ainda requer revisão
do autor e da orientadora, inclusive da diagramação final e dos e-mails pendentes.

Na tentativa realizada no terminal do autor, o compilador avançou e encontrou
um erro no arquivo de classe do template original: `\def\indexname{Index}TCC`,
na linha 2606. O texto solto `TCC` foi removido da cópia de trabalho; o ZIP
original permanece intacto na pasta de trabalho anterior. O script também passou a apresentar o erro do log
quando disponível, sem atribuir qualquer falha a um problema de conexão.

Para compilar em um terminal com acesso à internet, nesta pasta:

```powershell
python compilar.py
```

O comando procura o Tectonic no PATH ou em uma instalação local informada.
Os executáveis e caches não são distribuídos neste repositório. A primeira
compilação pode precisar baixar recursos do LaTeX. Em caso de sucesso, grava
`compilado/main.pdf` e verifica a quantidade de páginas se `pdfinfo` estiver
disponível. É possível fornecer os executáveis explicitamente:

```powershell
python compilar.py --tectonic "CAMINHO\tectonic.exe" --pdfinfo "CAMINHO\pdfinfo.exe"
```

Também é possível importar `artigo_primeira_versao.zip` no Overleaf ou em outra
instalação LaTeX e selecionar `main.tex` como documento principal. As dependências
utilizadas, incluindo `IEEEtran.bst`, pertencem às distribuições LaTeX usuais.
O ZIP não inclui banco, modelo treinado ou registros individuais dos experimentos.

Depois da compilação, conferir: até dez páginas **incluindo referências**,
acentos, equações, largura das tabelas, distribuição dos elementos flutuantes,
citações resolvidas e ausência de cortes. A checagem estática dos fontes não
substitui essa inspeção do PDF.

## Pontos para revisão do autor e da orientadora

1. Os dois e-mails permanecem explicitamente pendentes, conforme solicitado.
2. O título foi condensado para destacar a recuperação de nomes no Pauliceia.
   Conferir a preferência pelo título curto e a identificação dos autores.
3. A metodologia descreve Python/RapidFuzz no lugar do Painless previsto.
   Alinhar essa mudança e o recorte efetivo com a orientadora.
4. As dez grafias documentadas têm ocorrência em fontes digitais, mas o vínculo
   aos IDs não teve revisão histórica independente. As demais variantes
   complementares são simuladas.
5. As avaliações posteriores ao teste são explicitamente exploratórias. O
   Random Forest não foi retreinado, e o empate com Damerau–Levenshtein no
   complemento está apresentado.
6. A validação espacial verifica fidelidade ao backup; não mede erro geográfico
   contra levantamento independente. O fluxo novo não interpola coordenadas.
7. O protocolo de latência não registrou modelo da CPU, memória nem recursos
   dos contêineres. Não inventamos esses dados nem substituímos o ambiente
   histórico da medição por uma configuração atual presumida.
8. O material está pronto para revisão de conteúdo; diagramação, paginação e
   dados de autoria ainda precisam ser fechados antes da entrega acadêmica.

## Conferência bibliográfica

Consulta realizada em 22/11/2026. Ferla et al. foram conferidos no artigo da
SciELO; Santos et al. no registro institucional da Universidade de Lisboa,
com resumo e dados bibliográficos; Breiman no manuscrito hospedado em Berkeley
e nos metadados do periódico. As afirmações sobre esses trabalhos foram
limitadas ao conteúdo efetivamente acessível, sem importar resultados
numéricos de estudos externos.

As definições operacionais foram conferidas nas documentações oficiais de
Elasticsearch 8.19, scikit-learn 1.7 e RapidFuzz. A documentação pública do
RapidFuzz consultada apresenta versão 3.14.6, enquanto o código e os artefatos
do experimento registram **3.14.3**, versão mantida no artigo. As sete fontes
municipais foram abertas novamente; o manifesto original da avaliação
complementar continua preservado em `../dados/fontes_historicas.json`.

Os links estão em `referencias.bib` e na seção de referências da versão de
leitura. A bibliografia de exemplos do template (`bcc-ict-v1.bib`) foi
preservada, mas não é citada pelo novo `main.tex`.
