# Evidências congeladas

`reproducao/` conserva os arquivos das execuções utilizadas no artigo, incluindo
o modelo treinado, candidatos comprimidos, resultados, resumos e snapshots dos
scripts. `sha256.json` registra a assinatura de cada um dos 65 arquivos.

Execute `python preparar.py` na raiz para verificar esses arquivos e copiá-los
para as pastas `.local` esperadas pelos scripts. Não é necessário retreinar para
usar o modelo selecionado. Não edite os snapshots: novas execuções devem gerar
outras pastas, mantendo a rastreabilidade dos resultados publicados.

| Pasta | Conteúdo |
| --- | --- |
| avaliacoes | Candidatos e avaliações de treino/validação e teste |
| modelos | Modelo escolhido na validação e suas referências |
| testes | Teste reservado de 1.207 consultas |
| historico | Complemento exploratório de 179 consultas |
| comparacoes_metricas | Comparação exploratória de medidas isoladas |
| validacoes_portal | Respostas e medições HTTP do portal local |

Alguns registros conservam caminhos absolutos da máquina de origem como
metadados históricos. Eles não definem a localização atual dos arquivos. O script
de preparação usa caminhos relativos e preserva os bytes dos artefatos. O Git
também preserva as terminações de linha para não invalidar verificações de hash.

Os arquivos públicos não incluem o dump completo nem as senhas de acesso.
O modelo serializado foi produzido neste trabalho; carregue apenas cópias de
origem confiável e confira as assinaturas antes de utilizá-lo.
