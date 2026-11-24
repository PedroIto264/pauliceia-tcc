# Roteiro de demonstração do TCC

Roteiro de aproximadamente 12 a 15 minutos, com aprofundamento técnico opcional.
Os comandos são para PowerShell. Execute-os na mesma janela para manter as
variáveis definidas na preparação. As falas são sugestões para explicar o trabalho.

## Antes da reunião: preparar o ambiente

Abra o Docker Desktop e aguarde o Engine iniciar. Abra o PowerShell e execute:

```powershell
$repo = 'C:\Users\Usuario\Documents\Codex\2026-11-02\esse-o-pdf-do-meu-tcc\pauliceia-tcc'
Set-Location $repo
$tcc = Join-Path $repo 'projeto/geocoding-api/tcc-local'
$teste = Join-Path $repo 'artefatos/reproducao/testes/20261119T062452Z-8e4f5696'
$modelo = Join-Path $repo 'artefatos/reproducao/modelos/20261119T061951Z-cbab31c0'
docker info --format 'Docker Engine {{.ServerVersion}} | {{.OSType}}'
python preparar.py
```

O banco já foi restaurado na máquina usada no desenvolvimento. Com seus volumes
e credenciais preservados, inicie o portal:

```powershell
python projeto/geocoding-api/tcc-local/site_local.py
```

Em uma máquina sem a restauração, disponibilize o backup autorizado em
`dados/backup_dev.sql` e execute `python projeto/geocoding-api/tcc-local/iniciar.py`
antes de `site_local.py`. Consulte [COMO_RODAR.md](COMO_RODAR.md) para os detalhes.

Aguarde as mensagens de sucesso e abra:

- Portal: http://127.0.0.1:3180/portal/explore
- PowerPoint de um slide, já entregue separadamente.
- Pasta `pauliceia-tcc` no editor de código, por **Arquivo → Abrir pasta**.
- Artigo em `docs/artigo.pdf`.

Se o comando `code` estiver disponível, a pasta também pode ser aberta por:

```powershell
code .
```

Faça as buscas de demonstração antes da reunião. Não é necessário retreinar o
modelo, coletar novamente o teste ou reconstruir os resultados para apresentar.

## 1. Apresentar o objetivo — 1 minuto

**Abrir:** o slide único.

**Fala sugerida:**

> O objetivo é melhorar a busca de nomes de logradouros históricos no Pauliceia,
> considerando erros de escrita e variações de grafia. Adaptei o portal e a API
> existentes, implementei recuperação com Elasticsearch e uma reordenação com
> Random Forest. Vou mostrar a busca funcionando e as evidências da comparação.

Apresente as três etapas: recuperar candidatos, reordenar, apresentar sugestões.
Não comece pelo ano do endereço: o foco do trabalho é a recuperação textual.

## 2. Mostrar a busca funcionando — 2 minutos

**Abrir:** o portal, na busca aproximada.

1. Digite `rua ancheita` e acione a busca. Mostre Rua Anchieta em primeiro lugar.
2. Substitua por `rua cotsa`. Mostre Rua Costa em primeiro lugar.
3. Opcionalmente, pesquise `beco dos aflitos` para mostrar Becco dos Afflictos.

**Fala sugerida:**

> A consulta não precisa ser idêntica ao nome cadastrado. O sistema recupera até
> 100 candidatos, reordena com o modelo e apresenta cinco sugestões. Estes
> exemplos mostram o comportamento; a melhoria é medida no conjunto de teste.

A busca já está usando o modelo escolhido. Para comparar com os outros métodos,
use os resultados congelados na próxima etapa; não há necessidade de trocar a
configuração do portal durante a reunião.

## 3. Mostrar um exemplo concreto de melhoria — 1 minuto

**Abrir:** o PowerShell preparado anteriormente.

```powershell
Import-Csv (Join-Path $teste 'mudancas_teste.csv') -Delimiter ';' -Encoding UTF8 |
    Where-Object { $_.consulta -in @('rua ancheita', 'rua cotsa') } |
    Format-Table consulta, nome_referencia, posicao_trigramas, posicao_rf -AutoSize
```

Para `rua ancheita`, o registro do teste mostra posição **3** com trigramas e
posição **1** com o RF. O comando exibe também o caso de `rua cotsa`.

**Fala sugerida:**

> Aqui está a comparação registrada para a mesma consulta. O candidato correto
> já estava na lista recuperada; o Random Forest melhorou sua posição. Ele não
> consegue recuperar uma rua que tenha ficado fora dos 100 candidatos iniciais.

## 4. Apresentar os resultados gerais — 2 minutos

**Abrir:** o slide e, se necessário, `resumo.json` na pasta indicada por `$teste`.

| Método | Top-1 no teste | Recall@100 | MRR@100 |
| --- | ---: | ---: | ---: |
| BM25 | 63,55% | 86,50% | 0,6889 |
| BM25 + trigramas | 97,02% | 100,00% | 0,9808 |
| Random Forest | 100,00% | 100,00% | 1,0000 |

**Fala sugerida:**

> São 1.207 consultas de teste. O RF colocou um resultado relevante em primeiro
> lugar em todas elas: foram 36 acertos adicionais em relação aos trigramas,
> sem perdas. Isso vale para este conjunto controlado e não garante 100% em
> novos dados ou consultas reais.

Se ela pedir para ver as linhas que originaram a comparação:

```powershell
Import-Csv (Join-Path $teste 'resultados.csv') -Delimiter ';' -Encoding UTF8 |
    Where-Object { $_.consulta -eq 'rua ancheita' } |
    Format-Table consulta, metodo, primeira_posicao, acerto_1, recall_100, rr_100 -AutoSize
```

Definições: Top-1 é acerto na primeira posição; MRR é a média do inverso da
primeira posição relevante; Recall@100 é a fração dos IDs relevantes recuperada
nos 100. A métrica que pergunta apenas se houve algum relevante é `acerto_100`.

## 5. Explicar os dados e a separação — 1 a 2 minutos

**Abrir no editor:**

- `projeto/geocoding-api/tcc-local/dados/gabarito_manifesto.json`;
- `projeto/geocoding-api/tcc-local/preparar_gabarito.py`.

No manifesto, mostre `consultas`, `por_particao` e `por_tipo`. No Python, procure
`variantes`, `grupo_nome` e `montar` usando a busca do editor.

**Fala sugerida:**

> O catálogo tem 853 registros pesquisáveis e 847 nomes normalizados. Gerei
> 6.136 consultas com nomes originais e transformações controladas, como omissão,
> substituição e transposição de letras. Separei os grupos relacionados para
> manter suas variantes na mesma partição. Treino ajusta o modelo; validação
> escolhe a configuração; teste avalia o modelo escolhido.

Partições: 43 desenvolvimento, 3.681 treino, 1.205 validação, 1.207 teste.
O catálogo completo permanece indexado em todas as etapas. A avaliação mede
novos grupos de consultas dentro desse catálogo, não transferência para outro
banco. As regras sintéticas são semelhantes entre as partições.

## 6. Mostrar o núcleo técnico — 2 a 3 minutos

**Primeiro arquivo:** `projeto/geocoding-api/tcc-local/modelo_rf.py`.

| Procurar no editor | Mostrar e explicar |
| --- | --- |
| `def atributos` | As sete entradas: Damerau–Levenshtein, Jaro–Winkler, Token Sort, Token Set, Levenshtein, escore relativo e razão de comprimentos. |
| `def matriz` | Cada exemplo é um par consulta–candidato; o rótulo é relevante ou não relevante. |
| `CONFIGURACOES` | Grade de profundidade 12/sem limite e mínimo de 2/5 exemplos por folha. |
| `def selecionar` | Treino com 200 árvores; seleção por MRR por nome na validação, depois Top-1. |
| `def pontuar` | O escore de `predict_proba` da classe relevante é usado para ordenar. |

**Fala sugerida:**

> O modelo não tem uma classe para cada rua. Ele aprende a distinguir pares
> relevantes dos demais a partir de sete medidas numéricas. Uso o escore da
> classe relevante para ordenar os candidatos. Os IDs das ruas não são atributos
> do modelo, e esse escore não é uma probabilidade calibrada de verdade histórica.

O escolhido tem profundidade 12, mínimo de 2 por folha, 200 árvores e semente 42.
Se ela perguntar pelo arquivo treinado, abra o `resumo.json` da pasta `$modelo`;
ele contém `parametros`, `versoes`, `tentativas` e `modelo_sha256`. O arquivo
`modelo.joblib` é binário e não precisa ser aberto como texto.

**Segundo arquivo:** `projeto/geocoding-api/tcc-local/servico_modelo.py`.

Mostre `buscar` e `reordenar`. A busca usa `size: 100`, os campos `nome` e
`nome.tri` e `multi_match` com `most_fields`; depois reordena e retorna `[:5]`.

**Fala sugerida:**

> O serviço usa as mesmas funções de atributos do experimento. Carrega o modelo
> salvo e confere assinatura, versões e parâmetros antes de atender às buscas.
> Os empates preservam a ordem anterior do Elasticsearch.

Se ela pedir a configuração dos trigramas, abra `piloto.py` e mostre
`INDICE_CONFIG`: grupos de três caracteres, conversão para minúsculas e
tratamento de acentos. A palavra `costa`, por exemplo, gera `cos`, `ost`, `sta`.

## 7. Mostrar a integração e a avaliação complementar — 1 a 2 minutos

Para demonstrar a resposta da API, execute:

```powershell
Invoke-RestMethod 'http://127.0.0.1:3130/api/geocoding/candidatos?nome=rua%20cotsa' |
    Format-Table id, nome -AutoSize
```

**Fala sugerida:**

> A resposta é produzida pelo serviço e consumida pelo portal. A API Node faz a
> ligação; a interface apresenta os candidatos e permite selecionar a rua.

Se ela quiser ver esse caminho no código:

- `projeto/geocoding-api/routes/index.js`: rota `/candidatos`;
- `projeto/frontend/src/views/components/map/BuscaSimilar.vue`: método `buscar`;
- `projeto/geocoding-api/tcc-local/compose.yaml`: serviços Docker.

Para as avaliações adicionais, abra os relatórios abaixo; não é necessário
reexecutar os experimentos:

| Relatório | O que explicar |
| --- | --- |
| `artefatos/reproducao/historico/20261121T125413Z-e8ab4237/relatorio.md` | Complemento exploratório de 179 consultas: 10 grafias documentadas, 90 históricas simuladas e 79 fonéticas simuladas. RF e Damerau–Levenshtein acertaram todas. |
| `artefatos/reproducao/comparacoes_metricas/20261121T125929Z-28ccbb72/relatorio.md` | Comparação com similaridades isoladas, posterior ao teste e sem retreinar o RF. |
| `artefatos/reproducao/validacoes_portal/20261122T071548Z-83ecdd42/relatorio.md` | Busca 336/336, pontos 219/219 e fluxos 60/60; tempos medidos localmente, sequenciais e com aquecimento. |

Consulta por ano é opcional: Becco dos Afflictos, nº 11, 1940 retorna ponto;
1800 não retorna. Explique que isso verifica integração com o banco e não prova
que o endereço não existia em 1800 nem que o RF é superior.

## 8. Executar os testes, se solicitado — cerca de 1 minuto

Na preparação deste roteiro, a nova pasta não tinha `.venv`. Na máquina do autor
há um ambiente Python já instalado na pasta de trabalho original. Para usá-lo
com os testes do novo repositório, na mesma janela PowerShell:

```powershell
$pythonTestes = Join-Path (Split-Path $repo -Parent) 'projeto/geocoding-api/tcc-local/.local/venv-modelo/Scripts/python.exe'
& $pythonTestes -m unittest discover -s projeto/geocoding-api/tcc-local/tests -v
```

Esse caminho é específico desta máquina. Em outro computador, prepare o
ambiente virtual conforme [COMO_RODAR.md](COMO_RODAR.md) antes da reunião.

**Fala sugerida:**

> Estes testes verificam comportamentos como ordenação, persistência do modelo,
> tratamento de candidatos e comparação de coordenadas. A execução anterior
> passou nos 14 testes. Eles complementam a avaliação experimental e a validação
> HTTP; não demonstram, sozinhos, a precisão de recuperação.

## 9. Encerrar com entregas e pontos de alinhamento — 1 minuto

**Abrir:** `docs/artigo.pdf` e `COMO_RODAR.md`.

**Fala sugerida:**

> A implementação está integrada localmente, os resultados estão preservados
> com hashes e há instruções de execução. O artigo tem sete páginas e está em
> revisão. Preciso alinhar a implementação em Python/RapidFuzz no lugar do
> Painless previsto e o recorte efetivo do backup. A avaliação é majoritariamente
> sintética; as associações históricas não tiveram revisão independente e a
> geometria foi conferida com o próprio banco. Gostaria de validar se esse recorte
> e a forma de apresentá-lo estão adequados ao trabalho.

Não afirme que houve implantação em produção, validação histórica completa,
desempenho sob carga ou que os 100% se aplicam a qualquer consulta.

## Se houver pouco tempo ou uma falha ao vivo

Em cinco minutos: slide → duas buscas no portal → comparação de posições no CSV
→ tabela geral → limites e artigo.

Se o portal falhar, informe que a demonstração ao vivo não está disponível naquele
momento e apresente o código e os resultados registrados. Não apresente arquivos
de execuções anteriores como se fossem respostas produzidas naquela reunião.

Para diagnóstico, sem apagar volumes:

```powershell
docker compose --env-file projeto/geocoding-api/tcc-local/.local/docker.env -f projeto/geocoding-api/tcc-local/compose.yaml --profile site ps
docker compose --env-file projeto/geocoding-api/tcc-local/.local/docker.env -f projeto/geocoding-api/tcc-local/compose.yaml --profile site logs --tail 40
```
