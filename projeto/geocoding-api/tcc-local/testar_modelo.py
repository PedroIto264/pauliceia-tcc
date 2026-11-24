"""Compara o modelo escolhido com os dois métodos de busca no teste reservado."""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid

from iniciar import PASTA


MODELO_ESCOLHIDO = PASTA / ".local" / "modelos" / "20261119T061951Z-cbab31c0"


def ler_csv(caminho):
    with caminho.open(encoding="utf-8-sig", newline="") as arq:
        return list(csv.DictReader(arq, delimiter=";"))


def abrir_modelo(pasta):
    import joblib
    import numpy as np
    import rapidfuzz
    import sklearn
    from modelo_rf import ATRIBUTOS

    resumo = json.loads((pasta / "resumo.json").read_text(encoding="utf8"))
    arquivo = pasta / "modelo.joblib"
    if hashlib.sha256(arquivo.read_bytes()).hexdigest() != resumo["modelo_sha256"]:
        raise ValueError("O modelo diverge do arquivo selecionado na validação.")
    for nome, versao in (("numpy", np.__version__), ("sklearn", sklearn.__version__),
                        ("rapidfuzz", rapidfuzz.__version__)):
        if resumo["versoes"][nome] != versao:
            raise ValueError(f"A versão de {nome} difere da usada no treinamento.")
    # Os dados e a implementação das similaridades devem ser os mesmos do treino.
    if (pasta / "extrair_logradouros.py").read_bytes() != (PASTA / "extrair_logradouros.py").read_bytes():
        raise ValueError("A normalização mudou desde o treinamento.")
    pacote = joblib.load(arquivo)
    modelo = pacote["modelo"]
    if pacote["atributos"] != ATRIBUTOS or resumo["atributos"] != ATRIBUTOS:
        raise ValueError("Os atributos divergem do treinamento.")
    if modelo.n_jobs != 1 or modelo.get_params() != resumo["parametros"]:
        raise ValueError("Os parâmetros divergem da configuração escolhida.")
    origem = PASTA / ".local" / "avaliacoes" / resumo["avaliacao_origem"]
    for nome in ("gabarito_ampliado.csv", "resumo.json"):
        if hashlib.sha256((origem / nome).read_bytes()).hexdigest() != resumo["entradas_sha256"][nome]:
            raise ValueError("A referência da avaliação de treino foi alterada.")
    return modelo, resumo, origem


def avaliar(pasta_modelo, pasta_avaliacao):
    from avaliar_gabarito import METRICAS, resumir
    from modelo_rf import carregar, matriz, ordenar, pontuar
    from piloto import documentos

    modelo, resumo_modelo, origem = abrir_modelo(pasta_modelo)
    resumo_coleta, casos, cache, nomes = carregar(pasta_avaliacao, ("teste",))
    resumo_treino = json.loads((origem / "resumo.json").read_text(encoding="utf8"))
    for chave in ("gabarito_sha256", "backup_sha256", "indice"):
        if resumo_coleta[chave] != resumo_modelo[chave]:
            raise ValueError(f"{chave} difere entre treino e teste.")
    if resumo_coleta["indice_config"] != resumo_treino["indice_config"]:
        raise ValueError("A configuração do índice mudou entre treino e teste.")
    if resumo_coleta["elasticsearch"] != resumo_treino["elasticsearch"]:
        raise ValueError("A versão do Elasticsearch mudou entre treino e teste.")
    if resumo_coleta["particoes"] != ["teste"]:
        raise ValueError("Informe a coleta dedicada à partição de teste.")
    ids_treino = {c["id_consulta"] for c in ler_csv(origem / "resultados.csv")}
    if ids_treino.intersection(casos):
        raise ValueError("Há consultas de teste presentes na avaliação de treino.")

    print(f"Aplicando o modelo escolhido a {len(casos)} consultas de teste...", flush=True)
    x, _, _, blocos = matriz(casos, cache, nomes, "teste")
    linhas_rf = ordenar(blocos, pontuar(modelo, x), "random_forest")
    linhas_tri = ordenar(blocos)
    bm25 = [r for r in ler_csv(pasta_avaliacao / "resultados.csv") if r["metodo"] == "bm25"]
    if len(bm25) != len(casos) or {r["id_consulta"] for r in bm25} != casos.keys():
        raise ValueError("As consultas da referência BM25 estão incompletas.")
    for linha in bm25:
        if linha["particao"] != "teste":
            raise ValueError("A referência BM25 contém outra partição.")
        for metrica in METRICAS:
            linha[metrica] = float(linha[metrica])
        linha["primeira_posicao"] = int(linha["primeira_posicao"]) if linha["primeira_posicao"] else None
    linhas = bm25 + linhas_tri + linhas_rf
    anteriores = {r["id_consulta"]: r for r in linhas_tri}
    catalogo = {str(r["id"]): r["nome"] for r in documentos()}
    alteracoes = []
    for rf in linhas_rf:
        anterior = anteriores[rf["id_consulta"]]
        if rf["primeira_posicao"] == anterior["primeira_posicao"]:
            continue
        alteracoes.append({
            "id_consulta": rf["id_consulta"], "consulta": rf["consulta"],
            "nome_referencia": rf["nome_referencia"], "tipo": rf["tipo"],
            "posicao_trigramas": anterior["primeira_posicao"], "posicao_rf": rf["primeira_posicao"],
            "primeiro_trigramas": catalogo[anterior["ranking"].split("|")[0]],
            "primeiro_rf": catalogo[rf["ranking"].split("|")[0]],
        })
    corrigidos = sum(r["acerto_1"] > anteriores[r["id_consulta"]]["acerto_1"] for r in linhas_rf)
    perdidos = sum(r["acerto_1"] < anteriores[r["id_consulta"]]["acerto_1"] for r in linhas_rf)
    resumo = {
        "modelo": pasta_modelo.name, "modelo_sha256": resumo_modelo["modelo_sha256"],
        "avaliacao": pasta_avaliacao.name, "gabarito_sha256": resumo_modelo["gabarito_sha256"],
        "consultas": len(casos), "grupos": len({c["grupo"] for c in casos.values()}),
        "nomes": len({c["nome_referencia"] for c in casos.values()}),
        "parametros": resumo_modelo["parametros"], "versoes": resumo_modelo["versoes"],
        "resultados": resumir(linhas), "top1_corrigidos": corrigidos, "top1_perdidos": perdidos,
        "alvo_ausente_top100": sum(r["acerto_100"] == 0 for r in linhas_tri),
        "falhas_ordenacao_rf": sum(r["acerto_100"] == 1 and r["acerto_1"] == 0 for r in linhas_rf),
        "entradas_sha256": {
            nome: hashlib.sha256((pasta_avaliacao / nome).read_bytes()).hexdigest()
            for nome in ("candidatos.jsonl.gz", "gabarito_ampliado.csv", "resultados.csv", "resumo.json")
        },
    }
    raiz = PASTA / ".local" / "testes"
    raiz.mkdir(parents=True, exist_ok=True)
    destino = raiz / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    with TemporaryDirectory(prefix="em-andamento-", dir=raiz) as temporario:
        trabalho = Path(temporario)
        campos = list(casos[next(iter(casos))]) + ["metodo", "primeira_posicao", *METRICAS]
        with (trabalho / "resultados.csv").open("w", encoding="utf-8-sig", newline="") as arq:
            writer = csv.DictWriter(arq, fieldnames=campos, delimiter=";", extrasaction="ignore")
            writer.writeheader()
            writer.writerows(linhas)
        with (trabalho / "mudancas_teste.csv").open("w", encoding="utf-8-sig", newline="") as arq:
            writer = csv.DictWriter(arq, fieldnames=["id_consulta", "consulta", "nome_referencia", "tipo",
                                   "posicao_trigramas", "posicao_rf", "primeiro_trigramas", "primeiro_rf"],
                                   delimiter=";")
            writer.writeheader()
            writer.writerows(alteracoes)
        (trabalho / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        for nome in ("testar_modelo.py", "modelo_rf.py", "avaliar_gabarito.py", "extrair_logradouros.py"):
            (trabalho / nome).write_bytes((PASTA / nome).read_bytes())
        if hashlib.sha256((pasta_modelo / "modelo.joblib").read_bytes()).hexdigest() != resumo_modelo["modelo_sha256"]:
            raise RuntimeError("O arquivo do modelo foi alterado durante a avaliação.")
        trabalho.rename(destino)
    for r in resumo["resultados"]:
        m = r["media_por_consulta"]
        print(f"teste / {r['metodo']}: Top-1 {m['acerto_1']:.2%}, "
              f"Recall@100 {m['recall_100']:.2%}, MRR@100 {m['rr_100']:.4f}")
    print(f"Teste: {corrigidos} acertos novos, {perdidos} acertos perdidos.")
    print(f"Alvo fora dos 100 candidatos: {resumo['alvo_ausente_top100']}; "
          f"falhas de ordenacao do RF: {resumo['falhas_ordenacao_rf']}.")
    print(f"Teste final salvo em: {destino}")
    return destino


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--modelo", type=Path, default=MODELO_ESCOLHIDO)
    parser.add_argument("--avaliacao", type=Path, help="Reutiliza uma coleta de teste já concluída.")
    args = parser.parse_args()
    python = PASTA / ".local" / "venv-modelo" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if Path(sys.prefix).resolve() != python.parent.parent.resolve():
        if not python.is_file():
            raise ValueError("O ambiente Python do treinamento não foi encontrado.")
        subprocess.run([str(python), str(Path(__file__).resolve()), *sys.argv[1:]], check=True)
        return
    pasta_modelo = args.modelo.resolve()
    abrir_modelo(pasta_modelo)
    pasta_avaliacao = args.avaliacao
    if pasta_avaliacao is None:
        from avaliar_gabarito import executar
        pasta_avaliacao = executar({"teste"})
    avaliar(pasta_modelo, pasta_avaliacao.resolve())


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Teste interrompido: {erro}")
