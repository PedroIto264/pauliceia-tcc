# Banco de dados local

O arquivo `backup_dev.sql` não é distribuído neste repositório. O dump original
contém tabelas de usuários e outros dados que não são necessários à publicação
do trabalho. Ele e as credenciais locais estão excluídos pelo `.gitignore`.

Para reproduzir o portal com o mesmo recorte, obtenha uma cópia autorizada do
backup usado no trabalho e coloque-a nesta pasta com o nome `backup_dev.sql`.
SHA-256 esperado:

`8004407db214a605561e6c3d8f57643f6f66ad0ada40971ea288757964880fac`

Os scripts de restauração verificam essa assinatura; outro banco exige adaptar
o protocolo e constitui uma nova execução experimental. Os nomes de logradouros,
gabaritos, candidatos e resultados necessários à inspeção do experimento estão
nas pastas públicas `projeto/geocoding-api/tcc-local/dados` e `artefatos`.

Nesta cópia preparada na máquina do autor, o backup foi mantido localmente.
Ele não acompanhará um clone feito pelo GitHub. Não use `git add -f` para incluí-lo.
