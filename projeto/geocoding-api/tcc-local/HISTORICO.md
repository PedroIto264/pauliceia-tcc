# Avaliação complementar de grafias históricas e aproximações fonéticas

Preparação e avaliação concluídas em 21/11/2026. Execução:
`20261121T125413Z-e8ab4237`, em `.local/historico`.
Os hashes dos arquivos salvos foram conferidos e o modelo permanece inalterado.

## Resultados observados

| Categoria | Consultas | Top-1 BM25 | Top-1 BM25 + trigramas | Top-1 Random Forest |
| --- | ---: | ---: | ---: | ---: |
| Grafia documentada | 10 | 20,00% | 100,00% | 100,00% |
| Histórica simulada | 90 | 44,44% | 93,33% | 100,00% |
| Fonética simulada | 79 | 69,62% | 92,41% | 100,00% |

O Random Forest corrigiu 12 primeiros resultados em relação aos trigramas:
seis históricos simulados e seis fonéticos simulados, sem perder acertos.
Nos dez casos documentados houve empate entre trigramas e Random Forest;
esse recorte não demonstra benefício adicional da reordenação supervisionada.
O BM25 deixou nove alvos históricos simulados fora do Top-100. Trigramas e
Random Forest tiveram Recall@100 de 100% em cada uma das três categorias.

Exemplos de posições antes e depois da reordenação:

| Consulta | Referência | Trigramas | Random Forest | Exposição da rua |
| --- | --- | ---: | ---: | --- |
| rua pirai | Rua Pirahy | 7 | 1 | Treino |
| rua paraiba | rua parahyba | 6 | 1 | Treino |
| rua artur prado | rua arthur prado | 2 | 1 | Teste |
| rua doutor roza | Rua Doutor Rosa | 5 | 1 | Teste |

Há sete consultas normalizadas já presentes no gabarito ampliado ou no piloto.
Das 33 consultas referentes a ruas da partição original de teste, 32 são novas:
12 fonéticas simuladas, 19 históricas simuladas e uma documentada.
Nesse recorte de 32, os trigramas acertaram 30 primeiras posições e o RF acertou 32.
O recorte permanece exploratório, pois foi selecionado após conhecer o teste anterior.
As outras consultas envolvem ruas de treino, validação ou desenvolvimento e devem
ser interpretadas com essa exposição explícita. Não há comprovação de desempenho
universal, nem validação independente da identidade espacial dos pares documentados.

## Objetivo e recorte

Aplicar BM25, BM25 com trigramas e o Random Forest já selecionado a consultas
direcionadas às diferenças de grafia encontradas no catálogo do Pauliceia.
O modelo permanece congelado e os resultados do teste reservado permanecem intactos.
Este estudo foi concebido depois de conhecidos os resultados do teste; é exploratório.

O gabarito inicial contém 179 consultas sobre 168 nomes normalizados:

| Categoria | Consultas | O que representa |
| --- | ---: | --- |
| grafia_documentada | 10 | Grafia localizada em fonte municipal digital e associada textualmente a um registro do backup |
| historica_simulada | 90 | Transformações controladas de tokens do catálogo, inspiradas em diferenças ortográficas |
| fonetica_simulada | 79 | Aproximações de escrita motivadas por som, construídas artificialmente |

As simulações foram selecionadas antes da coleta dos novos rankings. Não foram
escolhidas por desempenho. As regras estão em `preparar_historico.py` e no manifesto.
Elas não constituem uma proposta de normalização automática do banco: por exemplo,
sobrenomes com letras dobradas podem conservar legalmente sua grafia.

## Fontes e vínculo com o catálogo

`dados/fontes_historicas.json` registra sete fontes municipais, URL, título,
localizador, pequeno trecho, data de consulta e o ID esperado no backup.
Exemplos: consulta `rua teodoro sampaio` para o registro `rua theodoro sampaio`;
consulta `rua santa ifigênia` para `rua santa ephigenia`.

**Documentada** qualifica a ocorrência da grafia da consulta. O vínculo com o
ID do catálogo é uma inferência de curadoria textual, sem revisão independente.
Não significa que a fonte contém o ID do Pauliceia, certifica a extensão da via
no período estudado ou comprova que um usuário fez essa consulta.
Ementas digitais de leis antigas podem ter ortografia atualizada; a data da lei
não é prova de que a grafia da ementa já era usada naquele ano.
Nenhum fac-símile histórico foi transcrito para esta versão do gabarito.

As dez grafias estão ligadas a Avenida Hygienopolis, Rua Theodoro Sampaio,
Rua Santa Ephigenia, Rua Arthur Azevedo, Rua Bella Cintra, Rua Barão de Tatuhy,
Rua Humayta, Rua do Triumpho, Travessa do Commercio e Becco dos Afflictos.
As fontes são páginas do Catálogo de Legislação Municipal e do São Paulo Urbanismo;
os endereços completos e trechos consultados estão no JSON de fontes.

## Controles de avaliação

- IDs relevantes incluem todos os registros com o mesmo nome normalizado.
- Correspondência textual não resolve homônimos físicos, número, ano ou geometria.
- Cada caso conserva o grupo e a partição original da rua. Há 111 consultas de
  ruas de treino, 29 de validação, 33 de teste e 6 de desenvolvimento.
- `consulta_preexistente` informa se a consulta normalizada já aparece no gabarito
  ampliado ou no piloto. Casos repetidos são identificados e não apresentados como novos.
- O resumo separa categorias e também partição original e consulta nova/repetida.
- A escolha intencional dos casos e sua pequena escala impedem tratar as taxas como
  estimativas representativas de todas as grafias históricas de São Paulo.
- Simulações idênticas a uma consulta documentada são deduplicadas, com prioridade
  para a documentada. Exclusões e suas razões são preservadas em `exclusoes.csv`.
- Colisões com outro nome cadastrado ou com alvos diferentes são excluídas pelo gerador.
- O alvo não é inserido artificialmente nos candidatos. Ausência no Top-100 conta como falha.
- O mesmo índice, os mesmos atributos, versões e modelo do experimento anterior
  são conferidos; não há chamada de treinamento neste fluxo.

## Execução

O gabarito já está preparado. Com Docker Desktop iniciado, execute no PowerShell:

```powershell
python projeto/geocoding-api/tcc-local/avaliar_historico.py
```

O script usa automaticamente o ambiente Python do treinamento e inicia o serviço
Elasticsearch existente. Coleta até 100 candidatos por método e consulta e aplica
o modelo selecionado. Não altera o serviço de busca do portal.

Conferência sem Docker nem coleta:

```powershell
python avaliar_historico.py --verificar
```

Para reproduzir apenas a preparação, execute `python preparar_historico.py` nesta pasta.
Regenerar os dados após alterar fontes ou regras define uma nova versão do experimento;
não substitui uma avaliação anterior nem deve servir para ocultar casos difíceis.

## Saídas e interpretação

Cada execução concluída cria uma pasta em `.local/historico` com:

- `relatorio.md`: tabelas por categoria, limites e falhas do Random Forest.
- `resumo.json`: métricas por consulta e por nome, discriminadas por categoria,
  partição original e repetição; hashes, versões e configurações.
- `resultados.csv`: métricas e ranking completo por consulta e método.
- `comparacao.csv`: posições nos três métodos, primeiro resultado do RF, ganhos,
  perdas e distinção entre falha de recuperação e de ordenação.
- `candidatos.jsonl.gz`: IDs e escores originais retornados pelo Elasticsearch.
- Cópias de fontes, gabarito, exclusões, manifesto e scripts utilizados.

Acerto@K é a presença de algum relevante entre os K primeiros; Precision@K é a
fração dos K resultados que são relevantes. Não são métricas intercambiáveis.
`elastic_took_ms` é apenas o tempo informado pelo Elasticsearch, não o tempo total
do portal nem a duração do Random Forest.

Esta etapa complementa os testes ortográficos da proposta. Para uma avaliação
histórica independente ainda são necessários exemplos com vínculo histórico/espacial
revisado, idealmente extraídos de documentos ou consultas reais. Os casos fonéticos
continuam sendo simulações grafêmicas, sem validação linguística ou gravação de fala.
