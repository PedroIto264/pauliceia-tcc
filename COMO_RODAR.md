# Como rodar o projeto

Este guia inicia o ambiente local do TCC com o modelo já treinado: banco
PostGIS, Elasticsearch, serviço Random Forest, API e portal Pauliceia.
Os comandos abaixo devem ser executados na raiz do repositório, na pasta
`pauliceia-tcc`, onde estão `preparar.py` e este arquivo.

## 1. Pré-requisitos

- Python 3.13 disponível pelo comando `python`.
- Docker Desktop iniciado, com contêineres Linux e virtualização habilitada.
- Docker Compose disponível pelo comando `docker compose`.
- Internet na primeira execução para baixar imagens e dependências.
- Portas locais 3130 (API) e 3180 (portal) disponíveis.
- Cópia autorizada do backup usado no TCC, conforme a próxima etapa.

Confira o ambiente no PowerShell:

```powershell
python --version
docker compose version
docker info --format 'Docker Engine {{.ServerVersion}} | {{.OSType}}'
```

O último comando deve identificar o tipo `linux`. Para iniciar o portal por
Docker, não é necessário instalar Node.js, PostgreSQL, Elasticsearch ou as
bibliotecas de aprendizado de máquina diretamente no Windows; os Dockerfiles
instalam essas dependências dentro dos contêineres.

## 2. Disponibilizar o banco

Coloque o arquivo do banco neste caminho, relativo à raiz:

```text
dados/backup_dev.sql
```

Os scripts validam o SHA-256 do arquivo. Outro backup não reproduz automaticamente
o mesmo experimento. Sem esse banco, é possível consultar os resultados e
preparar os artefatos, mas não executar o portal completo conforme este guia.

## 3. Preparar os artefatos

```powershell
python preparar.py
```

Esse comando confere os 65 arquivos publicados e copia o modelo, resultados e
referências para `projeto/geocoding-api/tcc-local/.local`. Também verifica o
backup, quando disponível. Não é necessário treinar novamente o Random Forest.

Se o comando informar que o backup está ausente, complete a etapa 2 antes de
continuar. Se apontar um arquivo divergente, confira a cópia utilizada antes
de substituir qualquer resultado local.

## 4. Restaurar e conferir o banco

```powershell
python projeto/geocoding-api/tcc-local/iniciar.py
```

Na primeira execução, o script gera as credenciais locais, inicia os serviços
necessários e restaura o backup. Quando encontra a restauração identificada do
mesmo backup, reutiliza o banco. Ao final, confere um endereço de controle:

```text
Teste OK: Rua Tres de Dezembro, 7 (1933). A geometria da API coincide com a do banco.
```

As credenciais ficam em `projeto/geocoding-api/tcc-local/.local/docker.env`,
excluído do Git.

## 5. Iniciar e abrir o portal

```powershell
python projeto/geocoding-api/tcc-local/site_local.py
```

O script confere o modelo, indexa o catálogo e inicia o portal integrado à API.
Depois de concluir as verificações, deve exibir:

```text
Teste OK: Random Forest ativo no portal; rua ancheita e rua cotsa em primeiro lugar.
Teste OK: o portal encontrou a rua, o ponto de 1940 e a ausencia de ponto em 1800.
Mapa do TCC: http://127.0.0.1:3180/portal/explore
```

Abra [http://127.0.0.1:3180/portal/explore](http://127.0.0.1:3180/portal/explore).

Na busca aproximada, experimente `rua ancheita`, `rua cotsa` ou `beco dos aflitos`.
Selecione a sugestão correspondente e informe número e ano para procurar o
ponto. Para **Becco dos Afflictos, número 11**, há ponto em **1940**; a consulta
em **1800** retorna ausência de ponto. As coordenadas são recuperadas do banco;
esse fluxo não interpola posições inexistentes.

## 6. Usar novamente e encerrar

Nas próximas utilizações, com os artefatos preparados, o banco restaurado e os
volumes preservados, abra o Docker Desktop e execute:

```powershell
python projeto/geocoding-api/tcc-local/site_local.py
```

Para encerrar os serviços e preservar os volumes:

```powershell
docker compose --env-file projeto/geocoding-api/tcc-local/.local/docker.env -f projeto/geocoding-api/tcc-local/compose.yaml --profile site down
```

Use o comando sem `--volumes` ou `-v`, para manter o banco e o índice. O projeto
Compose chama-se `pauliceia-tcc`: a pasta antiga e a nova usam as mesmas portas
e volumes na mesma máquina. Escolha uma única pasta para executar os comandos.

## 7. Consultar o estado e diagnosticar falhas

Depois da configuração inicial, confira os serviços:

```powershell
docker compose --env-file projeto/geocoding-api/tcc-local/.local/docker.env -f projeto/geocoding-api/tcc-local/compose.yaml --profile site ps
```

Para visualizar as últimas mensagens:

```powershell
docker compose --env-file projeto/geocoding-api/tcc-local/.local/docker.env -f projeto/geocoding-api/tcc-local/compose.yaml --profile site logs --tail 80
```

| Situação | O que conferir |
| --- | --- |
| Docker não responde | Abra o Docker Desktop e aguarde o Engine; confira a virtualização e o modo de contêineres Linux. |
| Backup ausente ou diferente | Confira `dados/backup_dev.sql` e a assinatura indicada em `dados/README.md`. |
| Modelo ou resumo não encontrado | Execute `python preparar.py` na raiz antes dos scripts de inicialização. |
| Falha de autenticação no banco | Confira se o `docker.env` corresponde aos volumes existentes; não gere novas senhas para um banco já criado. |
| Porta ocupada | Confira se outra cópia do projeto ou outro serviço está usando 3130 ou 3180. |
| Falha ao baixar imagem ou pacote | Confira a conexão e as mensagens da construção; repita a etapa após resolver a causa. |
| Portal não abre | Confira o estado e os logs, e aguarde as mensagens de sucesso de `site_local.py`. |

## 8. Executar os testes unitários (opcional)

Para testar os scripts Python fora dos contêineres, a partir da raiz no Windows:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r projeto/geocoding-api/tcc-local/requirements-modelo.txt
.venv/Scripts/python.exe -m unittest discover -s projeto/geocoding-api/tcc-local/tests -v
```

Não é necessário ativar o ambiente virtual para esses comandos. Em Linux/macOS,
use `.venv/bin/python` no lugar de `.venv/Scripts/python.exe`.
Os testes unitários não exigem iniciar o Docker nem substituem as verificações
de integração com o banco realizadas pelos scripts das etapas 4 e 5.

Os protocolos dos experimentos estão em
[EXPERIMENTO.md](projeto/geocoding-api/tcc-local/EXPERIMENTO.md),
[HISTORICO.md](projeto/geocoding-api/tcc-local/HISTORICO.md),
[COMPARACAO_METRICAS.md](projeto/geocoding-api/tcc-local/COMPARACAO_METRICAS.md) e
[VALIDACAO_PORTAL.md](projeto/geocoding-api/tcc-local/VALIDACAO_PORTAL.md).
