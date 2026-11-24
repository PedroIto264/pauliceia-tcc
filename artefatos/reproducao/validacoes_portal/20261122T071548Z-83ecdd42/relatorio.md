# Validação HTTP e espacial do portal

Execução completa: **True**. Motivo de interrupção: nenhum.

| Etapa | Tentativas | Corretas | Mediana (ms) | P95 (ms) |
| --- | ---: | ---: | ---: | ---: |
| aquecimento | 112 | 112 | 17.66505 | 38.21321999999999 |
| busca | 336 | 336 | 14.968499999999999 | 33.088075 |
| pontos | 219 | 219 | 3.9168 | 22.543789999999998 |
| fluxos | 60 | 60 | 20.58495 | 46.994344999999996 |

A tabela de tempo considera respostas conferidas e corretas. Falhas e tempos de todas
as tentativas estão no JSON. Aquecimento é separado das três rodadas medidas.

## Escopo

O tempo de busca inclui cliente HTTP local, proxy do portal, API Node, Elasticsearch,
similaridades e Random Forest até a leitura do JSON. Não mede desenho do mapa,
interação humana ou atraso de digitação. São requisições sequenciais com nova conexão.
O fluxo soma busca e consulta dos pontos, com escolha explícita do ID de referência.
Não é teste de carga, concorrência ou tempo de inicialização dos serviços.

A referência espacial foi lida do backup original, independentemente do endpoint.
A concordância confirma a entrega dos dados cadastrados, não sua exatidão histórica
no terreno. A convenção de fim em 2000 não comprova validade histórica até esse ano.
Não foi avaliada a interpolação da rota legada.

Modelo SHA-256: `1e1a2f7fb1521ce49f53d920116aacfdac9191e33c86fa1d77a5838bc3702ba0`.
