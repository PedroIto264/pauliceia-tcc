"""Compara similaridades isoladas nos candidatos já coletados, sem treino ou Docker."""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import json
import math
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid

from iniciar import PASTA, HASH_BACKUP
from preparar_historico import ler_csv, salvar_csv, sha
from testar_modelo import MODELO_ESCOLHIDO


TESTE = PASTA / ".local/testes/20261119T062452Z-8e4f5696"
HISTORICO = PASTA / ".local/historico/20261121T125413Z-e8ab4237"
# Todos os métodos abaixo são definidos antes de executar esta comparação.
ISOLADAS = ("damerau_levenshtein", "jaro_winkler", "token_sort", "token_set")
METODOS = ("bm25", "bm25_trigramas", *ISOLADAS, "random_forest")
ROTULOS = {"bm25": "BM25", "bm25_trigramas": "BM25 + trigramas",
           "damerau_levenshtein": "Damerau-Levenshtein", "jaro_winkler": "Jaro-Winkler",
           "token_sort": "Token Sort", "token_set": "Token Set", "random_forest": "Random Forest"}


def ler_json(caminho):
    return json.loads(caminho.read_text(encoding="utf8"))


def validar_cache(casos, registros, nomes):
    import numpy as np

    cache = {}
    for item in registros:
        chave = (item["id_consulta"], item["metodo"])
        if chave in cache or chave[0] not in casos or chave[1] not in ("bm25", "bm25_trigramas"):
            raise ValueError("Cache com consulta/método duplicado ou desconhecido.")
        ids, scores = item["ids"], item["scores"]
        if (len(ids) != len(scores) or len(ids) > 100 or len(ids) != len(set(ids))
                or not set(ids) <= nomes.keys()
                or any(not np.isfinite(s) or s < 0 for s in scores)):
            raise ValueError("IDs ou escores inválidos no cache.")
        cache[chave] = item
    esperado = {(ident, metodo) for ident in casos for metodo in ("bm25", "bm25_trigramas")}
    if cache.keys() != esperado:
        raise ValueError("Cache incompleto.")
    return cache


def avaliar_conjunto(casos, registros, nomes, modelo, particao):
    import numpy as np
    from avaliar_gabarito import medir
    from modelo_rf import ATRIBUTOS, matriz, ordenar, pontuar

    cache = validar_cache(casos, registros, nomes)
    tri = {ident: cache[(ident, "bm25_trigramas")] for ident in casos}
    x, _, _, blocos = matriz(casos, tri, nomes, particao)
    linhas = []
    for caso in casos.values():
        ids = cache[(caso["id_consulta"], "bm25")]["ids"]
        linhas.append(dict(caso, metodo="bm25", ranking="|".join(ids),
                           **medir(ids, caso["ids_relevantes"].split("|"))))
    linhas += ordenar(blocos)
    empates = []
    for metodo in ISOLADAS:
        # Mesma representação float32 fornecida ao RF; ranking decrescente por
        # similaridade, sem peso do Elasticsearch além do desempate estável.
        scores = x[:, ATRIBUTOS.index(metodo)]
        linhas += ordenar(blocos, scores, metodo)
        for caso, ids, inicio, fim in blocos:
            fatia = scores[inicio:fim]
            quantidade = int(np.count_nonzero(fatia == fatia.max())) if len(fatia) else 0
            empates.append({"id_consulta": caso["id_consulta"], "particao": particao,
                            "tipo": caso["tipo"], "metodo": metodo,
                            "candidatos_empatados_no_maior_escore": quantidade})
    linhas += ordenar(blocos, pontuar(modelo, x), "random_forest")
    for linha in linhas:
        if linha["metodo"] in (*ISOLADAS, "random_forest"):
            ids = linha["ranking"].split("|") if linha["ranking"] else []
            if set(ids) != set(tri[linha["id_consulta"]]["ids"]):
                raise ValueError("A reordenação alterou o conjunto de candidatos.")
    return linhas, empates


def conferir_reproducao(linhas, anteriores):
    from avaliar_gabarito import METRICAS

    base = {(r["id_consulta"], r["metodo"]): r for r in anteriores}
    atuais = {(r["id_consulta"], r["metodo"]): r for r in linhas
              if r["metodo"] in ("bm25", "bm25_trigramas", "random_forest")}
    if len(base) != len(anteriores) or base.keys() != atuais.keys():
        raise ValueError("Referência incompleta ou duplicada.")
    for chave, r in atuais.items():
        antigo = base[chave]
        for campo in ("consulta", "nome_referencia", "ids_relevantes", "particao", "tipo", "grupo"):
            if r[campo] != antigo[campo]:
                raise ValueError(f"Consulta ou relevância mudou: {chave}, {campo}")
        for metrica in METRICAS:
            if not math.isclose(float(antigo[metrica]), r[metrica], rel_tol=0, abs_tol=1e-12):
                raise ValueError(f"Métrica anterior não reproduzida: {chave}, {metrica}")
        posicao = int(antigo["primeira_posicao"]) if antigo["primeira_posicao"] else None
        if posicao != r["primeira_posicao"] or ("ranking" in antigo and antigo["ranking"] != r["ranking"]):
            raise ValueError(f"Ranking anterior não reproduzido: {chave}")


def comparar_rf(linhas, nomes):
    grupos = defaultdict(dict)
    for r in linhas:
        grupos[(r["particao"], r["id_consulta"])][r["metodo"]] = r
    pares = []
    for metodos in grupos.values():
        rf = metodos["random_forest"]
        for metodo in METODOS[:-1]:
            r = metodos[metodo]
            ids = r["ranking"].split("|") if r["ranking"] else []
            pares.append({"particao": r["particao"], "id_consulta": r["id_consulta"],
                          "consulta": r["consulta"], "nome_referencia": r["nome_referencia"],
                          "tipo": r["tipo"], "particao_original": r.get("particao_original", "teste"),
                          "consulta_preexistente": r.get("consulta_preexistente", ""),
                          "metodo": metodo, "posicao_metodo": r["primeira_posicao"],
                          "posicao_rf": rf["primeira_posicao"],
                          "primeiro_metodo": nomes[ids[0]] if ids else "",
                          "ganho_rf_top1": rf["acerto_1"] - r["acerto_1"],
                          "diferenca_rr": rf["rr_100"] - r["rr_100"]})
    return pares


def resumo_pares(pares):
    grupos = defaultdict(list)
    for p in pares:
        recorte = "teste" if p["particao"] == "teste" else p["tipo"]
        grupos[(recorte, p["metodo"])].append(p)
    return [dict(recorte=recorte, metodo=metodo, consultas=len(valores),
                 ganhos_rf=sum(p["ganho_rf_top1"] > 0 for p in valores),
                 perdas_rf=sum(p["ganho_rf_top1"] < 0 for p in valores),
                 diferenca_mrr=sum(p["diferenca_rr"] for p in valores) / len(valores))
            for (recorte, metodo), valores in sorted(grupos.items())]


def escrever_relatorio(resumo):
    texto = ["# Comparação de métricas isoladas", "",
             "Comparação adicional realizada após conhecer o teste original. Nenhum ajuste do modelo.",
             "As quatro similaridades e o RF reordenam os mesmos candidatos BM25 + trigramas (até 100).",
             "BM25 aparece como referência de recuperação própria, com candidatos potencialmente diferentes.",
             "Empates preservam a ordem dos trigramas; por isso, não se trata de busca isolada em todo o catálogo.",
             "As similaridades usam a mesma precisão float32 dos atributos do RF.",
             "Este experimento compara métodos; não mede causalmente a contribuição de cada atributo no RF.", ""]
    conjuntos = [("Teste reservado original (1.207 consultas)", resumo["teste"])]
    conjuntos += [(f"Complementar: {r['categoria']}", r["resultados"]) for r in resumo["complementar"]
                  if r["particao_original"] == "todas"]
    for titulo, resultados in conjuntos:
        texto += [f"## {titulo}", "",
                  "| Método | N | Top-1 | Top-3 | Top-5 | Recall@100 | MRR@100 |",
                  "| --- | ---: | ---: | ---: | ---: | ---: | ---: |"]
        por_metodo = {r["metodo"]: r for r in resultados}
        for metodo in METODOS:
            r = por_metodo[metodo]
            m = r["media_por_consulta"]
            texto.append(f"| {ROTULOS[metodo]} | {r['consultas']} | {m['acerto_1']:.2%} | "
                         f"{m['acerto_3']:.2%} | {m['acerto_5']:.2%} | {m['recall_100']:.2%} | {m['rr_100']:.4f} |")
        texto.append("")
    texto += ["## Comparações pareadas com o Random Forest", "",
              "| Recorte | Comparador | Ganhos RF Top-1 | Perdas RF Top-1 | Diferença MRR |",
              "| --- | --- | ---: | ---: | ---: |"]
    for p in resumo["comparacoes_rf"]:
        texto.append(f"| {p['recorte']} | {ROTULOS[p['metodo']]} | {p['ganhos_rf']} | "
                     f"{p['perdas_rf']} | {p['diferenca_mrr']:+.4f} |")
    texto += ["", "## Interpretação e rastreabilidade", "",
              "As taxas são descritivas; não foi realizado teste de significância estatística.",
              "O conjunto complementar é exploratório, com ruas de treino, validação, desenvolvimento e teste.",
              "As categorias documentada e simuladas não são agregadas em uma única taxa.",
              "A grafia documentada tem fonte municipal, mas o vínculo com o ID é inferência textual.",
              "O resumo JSON separa novidade da consulta, partição original, tipos de variação e médias por nome.",
              "Precision@K, também salva, é diferente da presença de algum relevante no Top-K.",
              "O número de candidatos empatados no maior escore de cada métrica está em empates.csv.",
              "Os métodos originais reproduziram as métricas anteriores por consulta; no complemento,",
              "também reproduziram os rankings completos. O arquivo do modelo não mudou.",
              "Caminhos e hashes dos dados de entrada estão em resumo.json; os caches originais são preservados.", ""]
    return "\n".join(texto)


def executar():
    from avaliar_gabarito import resumir
    from avaliar_historico import conferir_funcoes_modelo, resumir_recortes
    from extrair_logradouros import normalizar
    from modelo_rf import carregar
    from piloto import documentos
    from testar_modelo import abrir_modelo

    modelo, meta_modelo, origem = abrir_modelo(MODELO_ESCOLHIDO)
    conferir_funcoes_modelo()
    treino = ler_json(origem / "resumo.json")
    meta_teste = ler_json(TESTE / "resumo.json")
    coleta = PASTA / ".local/avaliacoes" / meta_teste["avaliacao"]
    fontes = {}
    def conferir_arquivo(caminho, esperado=None):
        atual = sha(caminho)
        if esperado is not None and atual != esperado:
            raise ValueError(f"Entrada alterada: {caminho}")
        fontes[str(caminho.resolve())] = atual
    for nome, esperado in meta_teste["entradas_sha256"].items():
        conferir_arquivo(coleta / nome, esperado)
    for nome in ("resumo.json", "resultados.csv"):
        conferir_arquivo(TESTE / nome)
    meta_hist = ler_json(HISTORICO / "resumo.json")
    conferir_arquivo(HISTORICO / "resumo.json")
    for nome, esperado in meta_hist["arquivos_sha256"].items():
        conferir_arquivo(HISTORICO / nome, esperado)
    for meta in (meta_teste, meta_hist):
        if meta["modelo_sha256"] != meta_modelo["modelo_sha256"]:
            raise ValueError("Modelo diferente entre experimentos.")
    meta_coleta, casos_teste, _, _ = carregar(coleta, ("teste",))
    if meta_coleta["particoes"] != ["teste"] or meta_coleta["gabarito_sha256"] != meta_modelo["gabarito_sha256"]:
        raise ValueError("O conjunto reservado não corresponde ao modelo.")
    for meta in (meta_coleta, meta_hist):
        for chave in ("indice", "indice_config", "elasticsearch", "k"):
            if meta[chave] != treino[chave]:
                raise ValueError(f"Configuração incompatível: {chave}")
    if meta_hist["manifesto"]["backup_sha256"] != HASH_BACKUP:
        raise ValueError("Backup histórico incompatível.")
    casos_hist_lista = ler_csv(HISTORICO / "gabarito.csv")
    casos_hist = {r["id_consulta"]: r for r in casos_hist_lista}
    if len(casos_hist) != len(casos_hist_lista) or any(r["particao"] != "complementar" for r in casos_hist_lista):
        raise ValueError("Gabarito complementar inválido.")
    docs = documentos()
    nomes = {str(d["id"]): normalizar(d["nome"]) for d in docs}
    linhas, empates = [], []
    for pasta, casos, particao, anteriores in (
        (coleta, casos_teste, "teste", TESTE / "resultados.csv"),
        (HISTORICO, casos_hist, "complementar", HISTORICO / "resultados.csv"),
    ):
        with gzip.open(pasta / "candidatos.jsonl.gz", "rt", encoding="utf8") as arquivo:
            cache = [json.loads(linha) for linha in arquivo]
        print(f"Comparando sete métodos: {particao}, {len(casos)} consultas...", flush=True)
        resultados, ties = avaliar_conjunto(casos, cache, nomes, modelo, particao)
        conferir_reproducao(resultados, ler_csv(anteriores))
        linhas += resultados
        empates += ties
    pares = comparar_rf(linhas, {str(d["id"]): d["nome"] for d in docs})
    resumo = {"modelo": MODELO_ESCOLHIDO.name, "modelo_sha256": meta_modelo["modelo_sha256"],
              "versoes": meta_modelo["versoes"], "metodos": METODOS,
              "protocolo": "Comparacao adicional pos-teste, sem treino; atributos float32; empate pela ordem dos trigramas",
              "teste": resumir([r for r in linhas if r["particao"] == "teste"]),
              "complementar": resumir_recortes([r for r in linhas if r["particao"] == "complementar"]),
              "comparacoes_rf": resumo_pares(pares), "entradas_sha256": fontes}
    raiz = PASTA / ".local/comparacoes_metricas"
    raiz.mkdir(parents=True, exist_ok=True)
    destino = raiz / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    resumo["execucao"] = destino.name
    with TemporaryDirectory(prefix="em-andamento-", dir=raiz) as temporario:
        trabalho = Path(temporario)
        campos = list(dict.fromkeys(k for r in linhas for k in r))
        salvar_csv(trabalho / "resultados.csv", linhas, campos)
        salvar_csv(trabalho / "comparacoes_rf.csv", pares, list(pares[0]))
        salvar_csv(trabalho / "empates.csv", empates, list(empates[0]))
        for nome in ("comparar_metricas.py", "modelo_rf.py", "avaliar_gabarito.py", "avaliar_historico.py",
                     "extrair_logradouros.py", "testar_modelo.py", "preparar_historico.py",
                     "requirements-modelo.txt", "piloto.py", "preparar_gabarito.py"):
            (trabalho / nome).write_bytes((PASTA / nome).read_bytes())
        (trabalho / "relatorio.md").write_text(escrever_relatorio(resumo), encoding="utf8")
        resumo["arquivos_sha256"] = {p.name: sha(p) for p in sorted(trabalho.iterdir())}
        (trabalho / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        if sha(MODELO_ESCOLHIDO / "modelo.joblib") != meta_modelo["modelo_sha256"]:
            raise ValueError("O modelo mudou durante a comparação.")
        for caminho, esperado in fontes.items():
            if sha(Path(caminho)) != esperado:
                raise ValueError("Uma entrada mudou durante a comparação.")
        trabalho.rename(destino)
    for r in resumo["teste"]:
        m = r["media_por_consulta"]
        print(f"teste / {r['metodo']}: Top-1 {m['acerto_1']:.2%}, MRR@100 {m['rr_100']:.4f}")
    print(f"Comparacao salva em: {destino}")
    return destino


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    python = PASTA / ".local/venv-modelo" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if Path(sys.prefix).resolve() != python.parent.parent.resolve():
        subprocess.run([str(python), str(Path(__file__).resolve())], check=True)
    else:
        executar()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Comparacao interrompida: {erro}")
