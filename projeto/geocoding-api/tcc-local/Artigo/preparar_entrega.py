"""Verifica fontes e gera leitura Markdown e ZIP para compilação do artigo."""
from pathlib import Path
import json
import re
import zipfile

P = Path(__file__).resolve().parent
SECOES = ['Introducao','Metodologia','Resultados','Discussao','Conclusao']


def campos_bib(texto):
    """Lê os campos entre chaves deste BibTeX, incluindo chaves aninhadas."""
    campos = {}
    posicao = 0
    while True:
        encontrado = re.search(r'(\w+)\s*=\s*\{',texto[posicao:])
        if not encontrado:
            break
        inicio = posicao + encontrado.end()
        fim = inicio
        nivel = 1
        while fim < len(texto) and nivel:
            if texto[fim] == '{': nivel += 1
            if texto[fim] == '}': nivel -= 1
            fim += 1
        assert nivel == 0, 'Campo BibTeX incompleto'
        campos[encontrado[1]] = texto[inicio:fim-1]
        posicao = fim
    return campos


def expandir(texto):
    return re.sub(r'\\input\{([^}]+)\}',
                  lambda m: expandir((P/(m[1]+'.tex')).read_text(encoding='utf-8')), texto)


def main():
    original = (P/'main.tex').read_text(encoding='utf-8')
    completo = expandir(original)
    bib = (P/'referencias.bib').read_text(encoding='utf-8')
    referencias = dict(re.findall(r'@\w+\{([^,]+),\s*(.*?)\n\}', bib, re.S))
    citadas = []
    for grupo in re.findall(r'\\cite\{([^}]+)\}',completo):
        for chave in grupo.split(','):
            assert chave in referencias, f'Referência ausente: {chave}'
            if chave not in citadas: citadas.append(chave)
    labels = re.findall(r'\\label\{([^}]+)\}',completo)
    assert len(labels) == len(set(labels)), 'Rótulos duplicados'
    assert set(re.findall(r'\\ref\{([^}]+)\}',completo)) <= set(labels)
    pilha = []
    for op,env in re.findall(r'\\(begin|end)\{([^}]+)\}',completo):
        if op == 'begin': pilha.append(env)
        else:
            assert pilha and pilha.pop() == env, f'Ambiente inconsistente: {env}'
    assert not pilha
    saldo = 0
    for token in re.findall(r'(?<!\\)[{}]',completo):
        saldo += 1 if token == '{' else -1
        assert saldo >= 0, 'Chave de fechamento inesperada'
    assert saldo == 0, 'Chaves desbalanceadas'
    for f in [P/'main.tex',P/'referencias.bib',*list((P/'Secoes').glob('*.tex')),
              *list((P/'Tabelas').glob('*.tex'))]:
        assert '\ufffd' not in f.read_text(encoding='utf-8'), f'Acentuação corrompida: {f}'

    numeros = {label:i+1 for i,label in enumerate(labels)}

    def converter(t):
        t = re.sub(r'\\cite\{([^}]+)\}',lambda m:'['+', '.join(str(citadas.index(k)+1) for k in m[1].split(','))+']',t)
        t = re.sub(r'\\ref\{([^}]+)\}',lambda m:str(numeros[m[1]]),t)
        t = re.sub(r'\\section\{([^}]+)\}',r'## \1',t)
        t = re.sub(r'\\subsection\{([^}]+)\}',r'### \1',t)
        t = re.sub(r'\\emph\{([^}]+)\}',r'*\1*',t)
        t = re.sub(r'\\texttt\{([^}]+)\}',r'`\1`',t)
        t = re.sub(r'\\begin\{align\}(.*?)\\end\{align\}',
                   lambda m:'\n$$\n\\begin{aligned}'+m[1]+'\\end{aligned}\n$$\n',t,flags=re.S)
        t = re.sub(r'\\begin\{equation\}(.*?)\\end\{equation\}',
                   lambda m:'\n$$\n'+m[1]+'\n$$\n',t,flags=re.S)
        return t.replace(r'\%', '%').replace(r'\_', '_').replace('~',' ').replace('--','–').replace('``','“').replace("''",'”')

    def tabela(match):
        t=(P/(match[1]+'.tex')).read_text(encoding='utf-8')
        caption=re.search(r'\\caption\{([^}]+)\}',t)[1]
        label=re.search(r'\\label\{([^}]+)\}',t)[1]
        conteudo=t.split(r'\toprule')[1].split(r'\bottomrule')[0]
        linhas=[l.strip()[:-2].strip() for l in conteudo.splitlines() if l.strip().endswith('\\')]
        cols=[l.split(' & ') for l in linhas]
        md='\n\n**Tabela '+str(numeros[label])+'. '+converter(caption)+'**\n\n'
        md+='| '+' | '.join(map(converter,cols[0]))+' |\n'
        md+='| '+' | '.join(['---']*len(cols[0]))+' |\n'
        for row in cols[1:]: md+='| '+' | '.join(map(converter,row))+' |\n'
        nota=re.search(r'\\footnotesize (.*?)\}',t,re.S)
        if nota: md+='\n'+converter(nota[1])+'\n'
        return md+'\n'

    titulo=re.search(r'\\title\{([^}]+)\}',original)[1]
    resumo=re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}',original,re.S)[1].strip()
    md='# '+titulo+'\n\n'
    md+='**Primeira versão para revisão — 22/11/2026.**\n\n'
    md+='Pedro Henrique Ito Boa Sorte · Daniela Leal Musa  \nUniversidade Federal de São Paulo — Instituto de Ciência e Tecnologia  \nE-mails pendentes.\n\n'
    md+='Esta cópia facilita a leitura. O arquivo de diagramação é `main.tex`; a contagem final de páginas depende da compilação em LaTeX.\n\n'
    md+='## Resumo\n\n'+converter(resumo)+'\n\n'
    md+='**Palavras-chave:** recuperação de informação; toponímia histórica; similaridade textual; Random Forest; Pauliceia.\n\n'
    for nome in SECOES:
        t=(P/'Secoes'/(nome+'.tex')).read_text(encoding='utf-8')
        t=re.sub(r'\\input\{([^}]+)\}',tabela,t)
        md+=converter(t)+'\n\n'
    md+='## Referências\n\n'
    for i,chave in enumerate(citadas,1):
        campos=campos_bib(referencias[chave])
        assert campos.get('author') and campos.get('title'), f'Referência incompleta: {chave}'
        def c(k): return campos.get(k,'').replace('{','').replace('}','').replace('--','–')
        dados=[c('author').replace(' and ','; '),c('title'),c('journal') or c('howpublished')]
        if c('volume'): dados.append('v. '+c('volume'))
        if c('number'): dados.append('n. '+c('number'))
        if c('pages'): dados.append('p. '+c('pages'))
        if c('year'): dados.append(c('year'))
        link=('https://doi.org/'+c('doi')) if c('doi') else c('url')
        md+=f'{i}. '+'. '.join(d for d in dados if d)+'.'
        if link: md+=f' [Fonte]({link}).'
        if c('note'): md+=' '+c('note')+'.'
        md+='\n\n'
    (P/'LEITURA_ARTIGO.md').write_text(md,encoding='utf-8')
    status={'referencias_citadas':len(citadas),'tabelas':len(labels),
            'estrutura_tex':'entradas, ambientes, chaves e referências internas conferidos',
            'escopo':'checagem estática dos fontes; este script não compila nem conta páginas',
            'verificacao_pdf_publicado':'docs/verificacao_pdf.json, na raiz do repositório',
            'limite_paginas':10,'emails':'pendentes por orientação do autor'}
    (P/'verificacao_editorial.json').write_text(json.dumps(status,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    arquivos=[P/'main.tex',P/'IEEEtran.cls',P/'referencias.bib',P/'LEITURA_ARTIGO.md',
              P/'LEIA-ME.md',P/'compilar.py',P/'proveniencia_tabelas.json',P/'verificacao_editorial.json',
              *sorted((P/'Secoes').glob('*.tex')),*sorted((P/'Tabelas').glob('*.tex'))]
    with zipfile.ZipFile(P/'artigo_primeira_versao.zip','w',zipfile.ZIP_DEFLATED) as z:
        for f in arquivos:
            assert f.is_file(), f'Arquivo de entrega ausente: {f}'
            z.write(f,f.relative_to(P))
    print(f'Leitura e ZIP gerados; {len(citadas)} referências e {len(labels)} tabelas verificadas.')


if __name__=='__main__':
    main()
