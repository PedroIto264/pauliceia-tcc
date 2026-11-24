"""Gera tabelas LaTeX a partir das execuções congeladas; não executa experimentos."""
from pathlib import Path
from collections import defaultdict
import csv
import hashlib
import json

ARTIGO = Path(__file__).resolve().parent
RAIZ = ARTIGO.parent
COMPARACAO = RAIZ / '.local/comparacoes_metricas/20261121T125929Z-28ccbb72'
PORTAL = RAIZ / '.local/validacoes_portal/20261122T071548Z-83ecdd42'
NOMES = {
    'bm25': 'BM25', 'bm25_trigramas': 'BM25 + trigramas',
    'damerau_levenshtein': 'Damerau--Levenshtein', 'jaro_winkler': 'Jaro--Winkler',
    'token_sort': 'Token Sort', 'token_set': 'Token Set', 'random_forest': 'Random Forest',
}
TIPOS = {
    'original': 'Original', 'normalizacao': 'Normalização', 'abreviacao': 'Abreviação',
    'omissao': 'Omissão', 'substituicao': 'Substituição', 'insercao': 'Inserção',
    'transposicao': 'Transposição', 'duas_omissoes': 'Duas omissões', 'ordem': 'Ordem',
}


def ler_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def numero(valor, casas=2):
    return f'{valor:.{casas}f}'.replace('.', ',')


def tabela(nome, legenda, colunas, cabecalho, linhas, nota=''):
    texto = '\n'.join([
        '% Gerado por gerar_tabelas.py a partir dos resultados congelados.',
        r'\begin{table}[tb]', r'\caption{' + legenda + '}',
        r'\label{tab:' + nome + '}', r'\centering', r'\small',
        r'\setlength{\tabcolsep}{3pt}', r'\begin{tabular}{' + colunas + '}',
        r'\toprule', ' & '.join(cabecalho) + r' \\', r'\midrule',
        *[' & '.join(map(str, l)) + r' \\' for l in linhas],
        r'\bottomrule', r'\end{tabular}',
        (r'\par\smallskip{\footnotesize ' + nota + '}') if nota else '',
        r'\end{table}', '',
    ])
    (ARTIGO / 'Tabelas' / (nome + '.tex')).write_text(texto, encoding='utf-8')


def main():
    (ARTIGO / 'Tabelas').mkdir(exist_ok=True)
    manifesto_path = RAIZ / 'dados/gabarito_manifesto.json'
    comp_path = COMPARACAO / 'resumo.json'
    csv_path = COMPARACAO / 'resultados.csv'
    portal_path = PORTAL / 'resumo.json'
    manifesto, comp, portal = map(ler_json, (manifesto_path, comp_path, portal_path))
    assert comp['modelo_sha256'] == portal['modelo_sha256']
    assert portal['completa'] and not portal['interrupcao']
    modelo = RAIZ / '.local/modelos' / comp['modelo'] / 'modelo.joblib'
    assert hashlib.sha256(modelo.read_bytes()).hexdigest() == comp['modelo_sha256']
    teste = {r['metodo']: r for r in comp['teste']}
    assert all(r['consultas'] == 1207 for r in teste.values())
    tabela('particoes', 'Separação do conjunto principal por grupos de nomes.', 'lrrr',
           ['Partição', 'Grupos', 'Nomes', 'Consultas'],
           [[p.capitalize(), *[v[k] for k in ('grupos', 'nomes', 'consultas')]]
            for p, v in manifesto['por_particao'].items()])
    tabela('principal', 'Teste reservado: médias por consulta (1.207 consultas).', 'lrrr',
           ['Método', r'Top-1 (\%)', r'R@100 (\%)', 'MRR@100'],
           [[n, numero(teste[m]['media_por_consulta']['acerto_1']*100),
             numero(teste[m]['media_por_consulta']['recall_100']*100),
             numero(teste[m]['media_por_consulta']['rr_100'],4)] for m,n in NOMES.items()],
           'As quatro similaridades isoladas foram comparadas após o teste original, sem modificar o modelo.')
    tabela('posicoes', 'Posições iniciais no teste: acerto (H) e precisão (P), em porcentagem.', 'lrrrr',
           ['Método', 'H@3', 'H@5', 'P@3', 'P@5'],
           [[n, *[numero(teste[m]['media_por_consulta'][k]*100)
                   for k in ('acerto_3','acerto_5','precision_3','precision_5')]] for m,n in NOMES.items()])
    selecionados = ['bm25','bm25_trigramas','damerau_levenshtein','random_forest']
    tabela('tipos', r'Top-1 por transformação no teste (\%).', 'lrrrrr',
           ['Transformação','n','BM25','Tri.','DL','RF'],
           [[nome, teste['bm25']['por_tipo'][tipo]['consultas'],
             *[numero(teste[m]['por_tipo'][tipo]['acerto_1']*100) for m in selecionados]]
            for tipo,nome in TIPOS.items()],
           'Tri.: BM25 com trigramas; DL: Damerau--Levenshtein; RF: Random Forest.')
    with csv_path.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f, delimiter=';'))
    grupos = defaultdict(list)
    for r in rows:
        if r.get('tipo') in {'grafia_documentada','historica_simulada','fonetica_simulada'}:
            grupos[(r['metodo'],r['tipo'])].append(float(r['acerto_1']))
    categorias = [('grafia_documentada',10),('historica_simulada',90),('fonetica_simulada',79)]
    for m in NOMES:
        for categoria,n in categorias:
            assert len(grupos[m,categoria]) == n, (m,categoria,len(grupos[m,categoria]))
    tabela('complementar', r'Top-1 no complemento exploratório (\%).', 'lrrr',
           ['Método','Doc. (10)','Hist. (90)','Fon. (79)'],
           [[nome,*[numero(100*sum(grupos[m,c])/n) for c,n in categorias]] for m,nome in NOMES.items()],
           'Doc.: grafias documentadas; Hist. e Fon.: variantes históricas e fonéticas simuladas.')
    # Os nomes das medidas abaixo seguem o resumo da validação ao vivo.
    linhas = []
    for chave,rotulo in [('busca','Busca'),('pontos','Pontos'),('fluxos','Busca + pontos')]:
        bloco = portal[chave]
        medidas = bloco['tempo_respostas_corretas']
        linhas.append([rotulo, f"{bloco['corretas']}/{bloco['tentativas']}",
                       numero(medidas['mediana_ms']),numero(medidas['p95_ms']),numero(medidas['media_ms'])])
    tabela('latencia', 'Validação local: verificações e tempos HTTP em ms.', 'lrrrr',
           ['Etapa','Corretas','Mediana','P95','Média'], linhas,
           'Busca: 112 consultas em três rodadas. Fluxos: 20 casos em três rodadas. Aquecimento excluído.')
    entradas = [manifesto_path,comp_path,csv_path,portal_path,modelo]
    registro = {
        'modelo_sha256': comp['modelo_sha256'],
        'entradas': {str(p.relative_to(RAIZ)).replace('\\','/'):hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in entradas},
        'tabelas': {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                    for p in sorted((ARTIGO/'Tabelas').glob('*.tex'))},
        'nota': 'Tabelas derivadas dos artefatos existentes; nenhum experimento foi reexecutado.',
    }
    (ARTIGO/'proveniencia_tabelas.json').write_text(json.dumps(registro,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Seis tabelas geradas e modelo conferido.')


if __name__ == '__main__':
    main()
