"""Compila o template real e verifica o limite de dez páginas quando há pdfinfo."""
from pathlib import Path
import argparse
import json
import re
import shutil
import subprocess
import sys

PASTA = Path(__file__).resolve().parent
FERRAMENTAS = PASTA.parent / '.local' / 'ferramentas'


def localizar(nome, argumento=None):
    if argumento:
        p=Path(argumento)
        if not p.is_file(): raise RuntimeError(f'Executável não encontrado: {p}')
        return str(p)
    encontrado=shutil.which(nome)
    if encontrado: return encontrado
    # A listagem de WindowsApps pode retornar vazia no terminal comum.
    # A cópia portátil dispensa essa listagem e não depende do PATH do aplicativo.
    portatil=FERRAMENTAS/(nome+'.exe')
    if portatil.is_file(): return str(portatil)
    configuracao=FERRAMENTAS/'caminhos.json'
    if configuracao.is_file():
        try:
            caminho=json.loads(configuracao.read_text(encoding='utf-8')).get(nome)
            if caminho and Path(caminho).is_file(): return caminho
        except (OSError,ValueError):
            pass
    # O runtime do aplicativo pode não estar no PATH do terminal do usuário.
    raiz=Path('C:/Program Files/WindowsApps')
    try:
        pacotes=sorted(raiz.glob('OpenAI.CodexPrimaryRuntime.*'),reverse=True)
        for pacote in pacotes:
            base=pacote/'dependencies/native'/('tectonic' if nome=='tectonic' else 'poppler')
            for relativo in [nome+'.exe','bin/'+nome+'.exe','Library/bin/'+nome+'.exe']:
                candidato=base/relativo
                if candidato.is_file(): return str(candidato)
    except OSError:
        pass
    return None


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tectonic',help='Caminho opcional do tectonic.exe')
    parser.add_argument('--pdfinfo',help='Caminho opcional do pdfinfo.exe')
    args=parser.parse_args()
    tex=localizar('tectonic',args.tectonic)
    if not tex:
        raise RuntimeError(f'Tectonic não encontrado. A cópia portátil é procurada em {FERRAMENTAS}. Também é possível informar --tectonic CAMINHO ou compilar main.tex em outra instalação LaTeX.')
    print(f'Compilador: {tex}',flush=True)
    saida=PASTA/'compilado'
    saida.mkdir(exist_ok=True)
    log_path=saida/'main.log'
    log_anterior=log_path.stat().st_mtime_ns if log_path.exists() else None
    resultado=subprocess.run([tex,'--keep-logs','--outdir',str(saida),str(PASTA/'main.tex')],cwd=PASTA)
    if resultado.returncode:
        detalhe='Confira a mensagem do compilador acima.'
        if log_path.exists() and log_path.stat().st_mtime_ns != log_anterior:
            linhas=log_path.read_text(encoding='utf-8',errors='replace').splitlines()
            inicio=next((i for i,l in enumerate(linhas) if l.startswith('!')),None)
            if inicio is not None:
                detalhe='\n'+'\n'.join(linhas[inicio:inicio+14])
            detalhe+=f'\nLog completo: {log_path}'
        raise RuntimeError('Compilação não concluída. '+detalhe)
    pdf=saida/'main.pdf'
    if not pdf.is_file(): raise RuntimeError('O compilador não produziu main.pdf.')
    info=localizar('pdfinfo',args.pdfinfo)
    paginas=None
    if info:
        texto=subprocess.check_output([info,str(pdf)],text=True,errors='replace')
        match=re.search(r'^Pages:\s+(\d+)',texto,re.M)
        if match: paginas=int(match[1])
    log=(saida/'main.log').read_text(encoding='utf-8',errors='replace') if (saida/'main.log').exists() else ''
    alertas=[l for l in log.splitlines() if any(x in l for x in ('Overfull','undefined','Missing character'))]
    registro={'pdf':str(pdf),'paginas':paginas,'limite':10,'alertas_layout_e_referencias':alertas}
    (saida/'verificacao_pdf.json').write_text(json.dumps(registro,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'PDF criado: {pdf}')
    if paginas is None:
        print('Contagem automática indisponível. Confira no leitor PDF se há no máximo dez páginas, incluindo referências.')
    else:
        print(f'Páginas: {paginas} / limite: 10')
        if paginas>10: raise RuntimeError('O PDF excede dez páginas; o texto precisa de ajuste editorial.')
    if alertas: print('Há avisos de diagramação ou referências; veja verificacao_pdf.json antes de entregar.')


if __name__=='__main__':
    try: main()
    except (OSError,RuntimeError,subprocess.SubprocessError) as exc:
        sys.exit(str(exc))
