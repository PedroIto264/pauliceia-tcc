# Conferência da preparação para publicação — 23/11/2026

- Repositório consolidado na branch `main`, sem remoto configurado e sem Git
  aninhado nos componentes. Nenhum commit ou envio foi realizado nesta preparação.
- Dump SQL, credenciais, `.local`, dependências e executáveis não constam no índice Git.
- Os 65 artefatos congelados mantêm seus hashes também nos blobs preparados no Git.
- A busca pelos valores das credenciais locais e por padrões de tokens GitHub,
  chaves AWS e chaves privadas não encontrou ocorrências nos arquivos preparados.
- Uma cópia extraída exclusivamente do índice Git, sem o banco privado, passou
  pela preparação dos artefatos, carregamento do modelo de 200 árvores,
  conferência das referências de treino e pelos **14 testes unitários**.
- As seis tabelas do artigo foram regeneradas nessa cópia. Seu conteúdo textual
  coincide com as tabelas da versão utilizada no PDF já compilado.
- A sintaxe de `routes/index.js` passou por `node --check`, e a configuração
  Docker Compose passou por `config --quiet` com as variáveis locais existentes.
- Os novos arquivos principais passaram pela verificação de espaços do Git.
  Avisos de espaços em fontes herdados foram preservados; não houve reformatação
  geral do código nem alteração dos snapshots congelados.

Essas verificações não reiniciaram os serviços Docker nem repetiram a validação
do navegador. As evidências da validação HTTP anterior estão preservadas em
`artefatos/reproducao/validacoes_portal`. Para executar a partir desta pasta,
seguir os comandos do README principal.

O PDF tem sete páginas e permanece em revisão, com os e-mails pendentes. A
assinatura e o registro de paginação estão em `verificacao_pdf.json`.
