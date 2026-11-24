# Validação de latência HTTP e correspondência espacial

Coleta ao vivo concluída em 22/11/2026, execução `20261122T071548Z-83ecdd42`,
em `.local/validacoes_portal`. Os hashes dos artefatos foram conferidos e o
modelo permaneceu inalterado. Não houve interrupções ou falhas registradas.

## Resultados da execução local

| Etapa | Verificações corretas | Mediana (ms) | P95 (ms) | Média (ms) |
| --- | ---: | ---: | ---: | ---: |
| Busca pelo proxy do portal | 336/336 | 14,97 | 33,09 | 18,85 |
| Consulta de pontos | 219/219 | 3,92 | 22,54 | 6,60 |
| Busca e obtenção dos pontos | 60/60 | 20,58 | 46,99 | 27,06 |

As 112 chamadas de aquecimento também passaram, mas não integram as 336 buscas
medidas. Estas representam três rodadas das mesmas 112 consultas; os 60 fluxos
representam três rodadas dos mesmos 20 casos, não 60 endereços independentes.

Nas buscas, as cinco sugestões e o identificador do modelo coincidiram com a
referência offline. Nos 219 controles espaciais, as respostas coincidiram com
o backup, incluindo 103 casos com pontos e 116 sem pontos. Os nove casos com
múltiplas coordenadas e os 21 com número decimal também passaram.

O P95 observado do fluxo de duas chamadas foi de aproximadamente 47 ms.
Este é um resultado do ambiente local, com execução sequencial e serviços
aquecidos. Não estima desempenho sob carga, acesso pela internet ou tempo de
renderização do navegador. A concordância espacial mede fidelidade ao backup,
não exatidão histórica independente das coordenadas cadastradas.

## Amostra fixada antes da medição

`dados/validacao_portal/protocolo.json` contém consultas, respostas esperadas,
endereços, anos, coordenadas, IDs dos pontos e limites da avaliação.
O manifesto registra seu SHA-256. Não se alteram amostras pelos tempos observados.

| Controle | Quantidade |
| --- | ---: |
| Consultas de busca | 112 |
| Aquecimento: uma chamada por consulta | 112 |
| Buscas medidas: três rodadas | 336 |
| Casos espaciais, uma chamada por caso | 219 |
| Fluxos busca → seleção do ID → pontos | 20 |
| Execuções desses fluxos: três rodadas | 60 |

As consultas vêm dos rankings RF já salvos na comparação de métricas.
São escolhidas por hash com semente fixa: até dez por tipo de variação e conjunto.
Há 82 do teste original e 30 do complemento (dez de cada categoria).
A amostra é estratificada, não representa a frequência natural de buscas reais.
As cinco sugestões esperadas, com IDs e nomes, estão congeladas no protocolo.

## Medição de tempo

O cronômetro monotônico começa antes da requisição HTTP e termina depois da
leitura e interpretação do JSON. A chamada passa pelo mesmo proxy do portal:
`http://127.0.0.1:3180/api/geocoding/candidatos`.
Inclui transporte local, proxy, API Node, Elasticsearch, cálculo das similaridades
e previsão do Random Forest. Não separa os tempos de cada componente.

Ficam fora: desenho do mapa e de sugestões, atraso de digitação, interação humana
e carregamento inicial do navegador. Não se deve chamar esse número de tempo
total percebido pelo usuário. O fluxo de duas chamadas mede busca e obtenção
dos pontos com seleção explícita do ID esperado entre as sugestões.

As requisições são sequenciais, com nova conexão HTTP. Há uma conferência inicial
do serviço, um aquecimento de cada consulta e três rodadas medidas, com ordem
determinística diferente em cada rodada. Não é teste de concorrência, carga,
inicialização dos contêineres nem comparação de velocidade entre modelos.
Durante os fluxos de duas chamadas o serviço já terá passado pelas buscas anteriores;
o endpoint de pontos também terá sido exercitado pelos controles espaciais.

São salvos tempos individuais, média, mediana, P95, mínimo e máximo.
P95 usa interpolação linear na posição `(n-1)*0,95` dos valores ordenados.
Aquecimento aparece separado. O resumo discrimina tempos de todas as tentativas
e tempos apenas das respostas corretas; falhas não são silenciosamente removidas.
Há também resultados por tipo de consulta e conjunto original/complementar.

## Referência espacial independente da rota

O gerador lê somente os campos necessários de `public.places_pilot_area2` no
backup cujo hash já foi fixado. Decodifica POINT EWKB 2D em EPSG:4326 com a
biblioteca padrão Python. Não usa a resposta do endpoint como verdade de referência.

O backup contém 5.872 registros nessa tabela. Vinte não possuem geometria ou
ano inicial necessário, restando 5.852 registros no oráculo. O registro 5948
tem ano inicial `199`: essa informação é mantida, sinalizada e não corrigida
para uma data presumida. Endereços com esse ano não são âncoras da amostra temporal.

Números são convertidos à forma decimal mais curta que preserva seu float8,
pois a rota compara `number::float`. Isso permite consultar `2.1` mesmo quando
o dump representa o número como `2.10000000000000009`, sem mudar seu valor binário.
O ano final ausente ou zero é interpretado como 2000, conforme o contrato
existente da API. Essa convenção técnica não comprova validade histórica até 2000.

Os 219 controles cobrem 37 ruas cadastradas, além de um ID inexistente:

- 103 casos esperam coordenadas; 116 esperam lista vazia.
- Nove casos esperam mais de uma coordenada distinta.
- 21 casos consultam números decimais.
- Incluem começo, interior e fim de intervalos, ano anterior a todos os registros,
  ano posterior a todos, limite convencional 2000 e consultas sem número cadastrado.

Casos coincidentes são deduplicados. O nome de uma categoria indica a primeira
regra que produziu o caso; por exemplo, um caso de início também pode ter múltiplos pontos.
As coordenadas esperadas incluem todos os pontos aplicáveis, deduplicados, e são
comparadas sem depender da ordem, com tolerância de 1e-9 grau por coordenada.
Coordenadas repetidas, ausentes, extras, não numéricas ou eixos trocados falham.

A concordância com o backup valida a entrega dos dados cadastrados e os filtros
de ID, número e ano. Não mede erro espacial em metros em relação a levantamento
independente, nem garante identidade histórica de logradouros homônimos.
O fluxo novo usa pontos cadastrados: a interpolação da rota legada não é avaliada.

## Execução

Com Docker Desktop iniciado, abra PowerShell e execute:

```powershell
Set-Location projeto/geocoding-api/tcc-local
python site_local.py
python validar_portal.py
```

O primeiro comando Python inicia e confere o portal. Execute o segundo depois
que o primeiro terminar com sucesso. A validação não modifica o banco nem treina
ou troca o modelo. Para conferir os arquivos sem acessar o portal:

```powershell
python validar_portal.py --verificar
```

Cada execução iniciada após a conferência do serviço grava uma pasta própria em
`.local/validacoes_portal`, com `relatorio.md`, `resumo.json`, registros individuais
em JSON, protocolo e scripts. Cinco falhas consecutivas interrompem a coleta e
preservam os resultados parciais. Falhas isoladas também ficam registradas e fazem
o comando terminar indicando que a execução precisa ser examinada.

Os 14 testes automatizados passaram. Eles verificam a leitura das coordenadas,
equivalência numérica, limites inclusivos, ano final aberto, deduplicação,
rejeição de coordenadas inválidas, separação das falhas nos tempos e gravação dos
fluxos. Os testes com transporte simulado não substituem a coleta ao vivo.
