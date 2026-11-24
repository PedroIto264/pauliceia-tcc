# Publicar no GitHub

Abra **esta pasta `pauliceia-tcc`**, que contém o README principal e `.git`.
Os arquivos foram preparados para um único repositório na branch `main`.
Nenhum remoto foi configurado e nenhum envio foi feito.

## GitHub Desktop

1. Use **File → Add local repository** e selecione esta pasta.
2. Revise a lista de alterações e crie o primeiro commit, por exemplo:
   `Organiza implementação, experimentos e artigo do TCC`.
3. Use **Publish repository**, com o nome `pauliceia-tcc`, escolha a visibilidade
   desejada e publique na sua conta.

## Terminal

Crie um repositório vazio na sua conta do GitHub, sem README, licença ou
`.gitignore` automáticos. Depois execute os comandos abaixo na pasta deste
projeto, substituindo `SEU_USUARIO` pelo nome da sua conta:

```powershell
git status --short
git add .
git commit -m "Organiza implementação, experimentos e artigo do TCC"
git remote add origin https://github.com/SEU_USUARIO/pauliceia-tcc.git
git push -u origin main
```

O nome e e-mail do commit devem estar configurados na sua instalação do Git.
O login no GitHub é feito na sua própria conta pelo terminal ou pelo Desktop.

## O que fica somente nesta máquina

- `dados/backup_dev.sql` (contém dados privados do dump original).
- Arquivos de senhas e demais conteúdo de `.local`.
- Dependências, ambientes virtuais, caches e executáveis locais.

As cópias públicas selecionadas das evidências estão em `artefatos/reproducao`.
O artigo e os slides estão em `docs`. Não use `git add -f` para contornar as
exclusões. Quem clonar terá os fontes e as evidências, mas precisará obter o
backup autorizado para executar o portal completo.
