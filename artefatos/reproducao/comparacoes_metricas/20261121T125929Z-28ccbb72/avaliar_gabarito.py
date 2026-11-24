"""Coleta rankings reais e métricas do gabarito ampliado no Elasticsearch."""

import argparse
from collections import defaultdict
import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid

from iniciar import COMPOSE, PASTA, configurar
from piloto import documentos, elastic, indexar, ndjson, INDICE_CONFIG
from preparar_gabarito import conferir


K = 100
LOTE = 40
METODOS = ("bm25", "bm25_trigramas")
METRICAS = ("acerto_1", "acerto_3", "acerto_5", "acerto_100", "recall_100",
            "precision_1", "precision_3", "precision_5", "rr_100")


def medir(ids, relevantes):
    ids = [str(i) for i in ids]
    relevantes = set(map(str, relevantes))
    if not relevantes or len(ids) != len(set(ids)):
        raise ValueError("Relevância vazia ou candidato repetido.")
    acertos = [i for i, candidato in enumerate(ids, 1) if candidato in relevantes]
    primeira = acertos[0] if acertos else None
    resultado = {"primeira_posicao": primeira, "rr_100": 1 / primeira if primeira else 0,
                 "recall_100": len(acertos) / len(relevantes)}
    for k in (1, 3, 5, 100):
        total = sum(posicao <= k for posicao in acertos)
        resultado[f"acerto_{k}"] = int(total > 0)
        if k <= 5:
            resultado[f"precision_{k}"] = total / k
    return resultado


def recuperar(indice, casos):
    requisicoes = []
    for caso in casos:
        nome = caso["consulta"]
        for consulta in (
            {"match": {"nome": nome}},
            {"multi_match": {"query": nome, "fields": ["nome", "nome.tri"], "type": "most_fields"}},
        ):
            requisicoes.extend(({}, {"size": K, "_source": False, "query": consulta,
                                    "sort": [{"_score": "desc"}, {"id": "asc"}]}))
    respostas = elastic("POST", indice + "/_msearch", ndjson(requisicoes))["responses"]
    if len(respostas) != len(casos) * len(METODOS):
        raise RuntimeError("O Elasticsearch retornou um lote incompleto.")
    resultados = []
    for i, caso in enumerate(casos):
        for j, metodo in enumerate(METODOS):
            resposta = respostas[i * len(METODOS) + j]
            if "error" in resposta or resposta.get("timed_out") or resposta["_shards"]["failed"]:
                raise RuntimeError(f"Busca incompleta para {caso['id_consulta']}: {resposta}")
            hits = resposta["hits"]["hits"]
            ids = [h["_id"] for h in hits]
            notas = medir(ids, caso["ids_relevantes"].split("|"))
            resultados.append({
                "linha": dict(caso, metodo=metodo, **notas, elastic_took_ms=resposta["took"]),
                "candidatos": {"id_consulta": caso["id_consulta"], "metodo": metodo,
                               "ids": ids, "scores": [h["_score"] for h in hits]},
            })
    return resultados


def medias(linhas):
    return {metrica: sum(l[metrica] for l in linhas) / len(linhas) for metrica in METRICAS}


def resumir(linhas):
    grupos = defaultdict(list)
    for linha in linhas:
        grupos[(linha["particao"], linha["metodo"])].append(linha)
    resumo = []
    for (particao, metodo), conjunto in sorted(grupos.items()):
        por_nome, por_tipo = defaultdict(list), defaultdict(list)
        for linha in conjunto:
            por_nome[linha["nome_referencia"]].append(linha)
            por_tipo[linha["tipo"]].append(linha)
        resumo.append({
            "particao": particao, "metodo": metodo, "consultas": len(conjunto), "nomes": len(por_nome),
            "media_por_consulta": medias(conjunto),
            "media_por_nome": medias([medias(valores) for valores in por_nome.values()]),
            "por_tipo": {tipo: dict(consultas=len(valores), **medias(valores))
                         for tipo, valores in sorted(por_tipo.items())},
        })
    return resumo


def executar(particoes):
    gabarito = PASTA / "dados" / "gabarito_ampliado.csv"
    manifesto = json.loads((gabarito.parent / "gabarito_manifesto.json").read_text(encoding="utf8"))
    if hashlib.sha256(gabarito.read_bytes()).hexdigest() != manifesto["gabarito_sha256"]:
        raise ValueError("O gabarito foi alterado desde a geração do manifesto.")
    with gabarito.open(encoding="utf-8-sig", newline="") as arq:
        todos = list(csv.DictReader(arq, delimiter=";"))
    docs = documentos()
    conferir(todos, docs)
    casos = [c for c in todos if c["particao"] in particoes]
    if not casos:
        raise ValueError("A seleção não contém consultas.")
    configurar()
    subprocess.run(COMPOSE + ["up", "-d", "--wait", "elasticsearch"], check=True)
    indice = indexar(docs)
    versao = elastic("GET", "")["version"]["number"]
    pasta = PASTA / ".local" / "avaliacoes"
    pasta.mkdir(parents=True, exist_ok=True)
    id_execucao = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    destino = pasta / id_execucao
    linhas = []
    # O diretório final só é publicado depois de todos os lotes terem sucesso.
    with TemporaryDirectory(prefix="em-andamento-", dir=pasta) as temporario:
        trabalho = Path(temporario)
        with gzip.open(trabalho / "candidatos.jsonl.gz", "wt", encoding="utf8") as cache:
            for inicio in range(0, len(casos), LOTE):
                for resultado in recuperar(indice, casos[inicio:inicio + LOTE]):
                    linhas.append(resultado["linha"])
                    cache.write(json.dumps(resultado["candidatos"], ensure_ascii=False) + "\n")
                print(f"Consultas coletadas: {min(inicio + LOTE, len(casos))}/{len(casos)}", flush=True)
        with (trabalho / "resultados.csv").open("w", encoding="utf-8-sig", newline="") as arq:
            writer = csv.DictWriter(arq, fieldnames=linhas[0].keys(), delimiter=";")
            writer.writeheader()
            writer.writerows(linhas)
        resumo = {
            "execucao": id_execucao, "gabarito_sha256": manifesto["gabarito_sha256"],
            "backup_sha256": manifesto["backup_sha256"], "indice": indice,
            "elasticsearch": versao, "indice_config": INDICE_CONFIG, "k": K,
            "particoes": sorted(particoes), "resultados": resumir(linhas),
            "scripts_sha256": {
                nome: hashlib.sha256((PASTA / nome).read_bytes()).hexdigest()
                for nome in ("preparar_gabarito.py", "avaliar_gabarito.py", "piloto.py", "extrair_logradouros.py")
            },
        }
        (trabalho / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        # Guarda os arquivos necessários para identificar e reproduzir esta execução.
        (trabalho / "gabarito_ampliado.csv").write_bytes(gabarito.read_bytes())
        trabalho.rename(destino)
    for item in resumo["resultados"]:
        m = item["media_por_consulta"]
        print(f"{item['particao']} / {item['metodo']}: Top-1 {m['acerto_1']:.2%}, "
              f"Recall@100 {m['recall_100']:.2%}, MRR@100 {m['rr_100']:.4f}")
    print(f"Resultados completos: {destino}")
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--particoes", nargs="+", default=["treino", "validacao"],
                        choices=["desenvolvimento", "treino", "validacao", "teste"])
    args = parser.parse_args()
    try:
        executar(set(args.particoes))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Avaliacao interrompida: {erro}")
