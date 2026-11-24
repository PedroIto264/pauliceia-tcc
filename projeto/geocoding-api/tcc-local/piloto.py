"""Indexa o catálogo e compara a API existente e duas buscas por nome."""

import csv
import hashlib
import json
import os
import subprocess
import sys
from tempfile import NamedTemporaryFile
from urllib.parse import quote
from urllib.request import urlopen

from extrair_logradouros import extrair
from iniciar import BACKUP, HASH_BACKUP, COMPOSE, PASTA, URL, configurar, psql, conferir_api, conferir_banco


GABARITO = PASTA / "dados" / "gabarito_piloto.csv"
SAIDA = PASTA / "dados" / "resultado_piloto.csv"
K = 100
INDICE_CONFIG = {
    "settings": {
        "number_of_shards": 1, "number_of_replicas": 0,
        "analysis": {
            "filter": {"tri": {"type": "ngram", "min_gram": 3, "max_gram": 3}},
            "analyzer": {
                "palavras": {"type": "custom", "tokenizer": "standard",
                             "filter": ["lowercase", "asciifolding"]},
                "trigramas": {"type": "custom", "tokenizer": "standard",
                              "filter": ["lowercase", "asciifolding", "tri"]},
            },
        },
    },
    "mappings": {"dynamic": "strict", "properties": {
        "id": {"type": "integer"},
        "nome": {"type": "text", "analyzer": "palavras", "similarity": "BM25",
                 "fields": {"tri": {"type": "text", "analyzer": "trigramas", "similarity": "BM25"}}},
    }},
}


def ndjson(linhas):
    return "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in linhas).encode("utf8")


def elastic(metodo, caminho, corpo=None, aceitar_404=False):
    cmd = COMPOSE + ["exec", "-T", "elasticsearch", "curl", "-sS", "--max-time", "60",
                     "-w", "\n%{http_code}", "-X", metodo, "http://localhost:9200/" + caminho]
    dados = None
    if corpo is not None:
        lote = isinstance(corpo, bytes)
        dados = corpo if lote else json.dumps(corpo).encode()
        cmd += ["-H", "Content-Type: application/" + ("x-ndjson" if lote else "json"),
                "--data-binary", "@-"]
    saida = subprocess.run(cmd, input=dados, capture_output=True)
    if saida.returncode:
        raise RuntimeError(saida.stderr.decode("utf8", errors="replace"))
    bruto, status = saida.stdout.rsplit(b"\n", 1)
    if status == b"404" and aceitar_404:
        return None
    resposta = json.loads(bruto)
    if int(status) >= 400:
        raise RuntimeError(f"Elasticsearch HTTP {status.decode()}: {resposta}")
    return resposta


def documentos():
    conteudo = BACKUP.read_bytes()
    if hashlib.sha256(conteudo).hexdigest() != HASH_BACKUP:
        raise ValueError("O backup difere da base usada para o piloto.")
    return [{"id": r["id"], "nome": r["nome_original"]} for r in extrair(conteudo)
            if r["nome_normalizado"] not in {"", "nao oficial", "n.o"}]


def indexar(docs):
    assinatura = hashlib.sha256(ndjson([INDICE_CONFIG, *docs])).hexdigest()[:16]
    indice = "pauliceia-ruas-" + assinatura
    if elastic("GET", indice, aceitar_404=True) is None:
        elastic("PUT", indice, INDICE_CONFIG)
    linhas = []
    for doc in docs:
        linhas.extend(({"index": {"_id": str(doc["id"])}}, doc))
    carga = elastic("POST", indice + "/_bulk?refresh=wait_for", ndjson(linhas))
    if carga["errors"] or len(carga["items"]) != len(docs):
        raise RuntimeError("A carga do catalogo teve falhas.")
    if elastic("GET", indice + "/_count")["count"] != len(docs):
        raise RuntimeError("A contagem do indice difere do catalogo.")
    alias = "pauliceia-catalogo"
    anteriores = elastic("GET", "_alias/" + alias, aceitar_404=True) or {}
    acoes = [{"remove": {"index": nome, "alias": alias}} for nome in anteriores if nome != indice]
    if indice not in anteriores:
        acoes.append({"add": {"index": indice, "alias": alias}})
    if acoes:
        elastic("POST", "_aliases", {"actions": acoes})
    print(f"Indice conferido: {len(docs)} registros.", flush=True)
    return indice


def posicoes(indice, casos):
    linhas = []
    for caso in casos:
        nome = caso["consulta"]
        for consulta in ({"match": {"nome": nome}},
                         {"multi_match": {"query": nome, "fields": ["nome", "nome.tri"], "type": "most_fields"}}):
            linhas.extend(({}, {"size": K, "_source": False, "query": consulta,
                                "sort": [{"_score": "desc"}, {"id": "asc"}]}))
    respostas = elastic("POST", indice + "/_msearch", ndjson(linhas))["responses"]
    resultado = []
    for caso, dupla in zip(casos, zip(respostas[::2], respostas[1::2], strict=True), strict=True):
        ranks = []
        for resposta in dupla:
            if "error" in resposta or resposta.get("timed_out") or resposta["_shards"]["failed"]:
                raise RuntimeError(f"Busca incompleta: {resposta}")
            ids = [h["_id"] for h in resposta["hits"]["hits"]]
            ranks.append(ids.index(caso["id_rua"]) + 1 if caso["id_rua"] in ids else None)
        resultado.append(ranks)
    return resultado


def pontos_referencia(casos):
    # Valores inteiros do gabarito. Verifica no PostGIS a unicidade da verdade de referência.
    chaves = {tuple(int(c[campo]) for campo in ("id_rua", "id_ponto", "numero", "ano")) for c in casos}
    valores = ", ".join("(" + ", ".join(map(str, chave)) + ")" for chave in sorted(chaves))
    sql = f"""
    WITH casos(rua, ponto, numero, ano) AS (VALUES {valores})
    SELECT c.ponto, ST_AsText(p.geom), p.id FROM casos c
    JOIN public.places_pilot_area2 p ON p.id_street::integer = c.rua AND p.number::float = c.numero
      AND c.ano BETWEEN p.first_year::integer AND coalesce(nullif(p.last_year::integer,0),2000);
    """
    pontos = {}
    for linha in psql("pauliceia", sql.encode()).splitlines():
        esperado, geom, obtido = linha.split("|")
        if esperado != obtido or esperado in pontos or not geom:
            raise ValueError(f"Ponto de referencia ambiguo ou incorreto: {esperado}")
        pontos[esperado] = geom
    if pontos.keys() != {c["id_ponto"] for c in casos}:
        raise ValueError("Faltam pontos de referencia no banco.")
    return pontos


def testar_api(caso, ponto):
    caminho = f"/geolocation/{quote(caso['consulta'], safe='')},{caso['numero']},{caso['ano']}/json"
    with urlopen(URL + caminho, timeout=30) as resposta:
        _, candidatos = json.load(resposta)
    if not isinstance(candidatos, list) or not candidatos or any(
        c.get("status") not in (0, 1) for c in candidatos
    ):
        raise RuntimeError("Resposta inesperada da API de geocodificacao.")
    return int(any(c["status"] == 1 and c.get("geom") == ponto for c in candidatos))


def salvar(linhas):
    arq = NamedTemporaryFile("w", encoding="utf-8-sig", newline="", delete=False, dir=SAIDA.parent)
    try:
        with arq:
            tabela = csv.DictWriter(arq, fieldnames=linhas[0].keys(), delimiter=";")
            tabela.writeheader()
            tabela.writerows(linhas)
        os.replace(arq.name, SAIDA)
    finally:
        if os.path.exists(arq.name):
            os.unlink(arq.name)


def main():
    with GABARITO.open(encoding="utf-8-sig", newline="") as arq:
        casos = list(csv.DictReader(arq, delimiter=";"))
    docs = documentos()
    configurar()
    subprocess.run(COMPOSE + ["up", "-d", "--wait", "api", "elasticsearch"], check=True)
    conferir_api(conferir_banco())
    pontos = pontos_referencia(casos)
    indice = indexar(docs)
    ranks = posicoes(indice, casos)
    linhas = []
    for caso, (bm25, tri) in zip(casos, ranks, strict=True):
        acerto = testar_api(caso, pontos[caso["id_ponto"]])
        linhas.append(dict(caso, api_geometria_correta=acerto, posicao_bm25=bm25, posicao_bm25_tri=tri))
    salvar(linhas)
    print(f"API: {sum(l['api_geometria_correta'] for l in linhas)}/{len(linhas)} geometrias corretas.")
    for campo in ("posicao_bm25", "posicao_bm25_tri"):
        ranks_validos = [l[campo] for l in linhas if l[campo] is not None]
        print(f"{campo}: primeiro lugar {ranks_validos.count(1)}/{len(linhas)}, "
              f"rua presente no top {K}: {len(ranks_validos)}/{len(linhas)}.")
    print(f"Resultado do piloto: {SAIDA}")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Piloto interrompido: {erro}")
