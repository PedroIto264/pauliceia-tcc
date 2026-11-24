"""Serviço interno de reordenação para o portal local do TCC."""

import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import logging
import os
from pathlib import Path
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

import joblib
import numpy as np
import rapidfuzz
import sklearn

from extrair_logradouros import normalizar
from modelo_rf import ATRIBUTOS, atributos, pontuar


class BuscaModelo:
    def __init__(self, pasta, elasticsearch):
        self.elasticsearch = elasticsearch.rstrip("/")
        self.resumo = json.loads((pasta / "resumo.json").read_text(encoding="utf8"))
        arquivo = pasta / "modelo.joblib"
        self.sha256 = hashlib.sha256(arquivo.read_bytes()).hexdigest()
        if self.sha256 != self.resumo["modelo_sha256"]:
            raise ValueError("O modelo diverge do arquivo selecionado.")
        for nome, versao in (("numpy", np.__version__), ("sklearn", sklearn.__version__),
                            ("rapidfuzz", rapidfuzz.__version__)):
            if versao != self.resumo["versoes"][nome]:
                raise ValueError(f"A versão de {nome} diverge do treinamento.")
        pacote = joblib.load(arquivo)
        self.modelo = pacote["modelo"]
        if pacote["atributos"] != ATRIBUTOS or self.resumo["atributos"] != ATRIBUTOS:
            raise ValueError("Atributos diferentes do treinamento.")
        if self.modelo.get_params() != self.resumo["parametros"] or self.modelo.n_jobs != 1:
            raise ValueError("Parâmetros diferentes do modelo avaliado.")

    def reordenar(self, nome, hits):
        if not hits:
            return []
        if len(hits) > 100:
            raise ValueError("A recuperação excedeu 100 candidatos.")
        ids = [hit["_source"]["id"] for hit in hits]
        if any(type(i) is not int for i in ids) or len(ids) != len(set(ids)):
            raise ValueError("IDs de candidatos inválidos.")
        scores = [hit["_score"] for hit in hits]
        if any(not isinstance(s, (int, float)) or not np.isfinite(s) or s < 0 for s in scores):
            raise ValueError("Escores de candidatos inválidos.")
        if any(not isinstance(hit["_source"]["nome"], str) for hit in hits):
            raise ValueError("Nomes de candidatos inválidos.")
        consulta = normalizar(nome)
        maior = max(scores)
        x = np.asarray([
            atributos(consulta, normalizar(hit["_source"]["nome"]), hit["_score"], maior)
            for hit in hits
        ], dtype=np.float32)
        ordem = np.argsort(-pontuar(self.modelo, x), kind="stable")
        return [{"id": hits[i]["_source"]["id"], "nome": hits[i]["_source"]["nome"]} for i in ordem]

    def buscar(self, nome):
        corpo = {
            "size": 100,
            "query": {"multi_match": {"query": nome, "fields": ["nome", "nome.tri"], "type": "most_fields"}},
            "sort": [{"_score": "desc"}, {"id": "asc"}],
        }
        requisicao = Request(self.elasticsearch + "/" + self.resumo["indice"] + "/_search",
                             data=json.dumps(corpo).encode("utf8"),
                             headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(requisicao, timeout=5) as resposta:
            dados = json.load(resposta)
        if dados.get("timed_out") or dados["_shards"]["failed"]:
            raise ValueError("A recuperação no índice ficou incompleta.")
        return self.reordenar(nome, dados["hits"]["hits"])[:5]


class Atendimento(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def responder(self, status, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode("utf8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("X-Pauliceia-Modelo", self.server.busca.sha256)
        self.end_headers()
        self.wfile.write(corpo)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == "/saude":
            return self.responder(200, {"modelo": self.server.busca.sha256,
                                        "indice": self.server.busca.resumo["indice"]})
        if url.path != "/candidatos":
            return self.responder(404, {"erro": "Recurso inexistente."})
        valores = parse_qs(url.query).get("nome", [])
        if len(valores) != 1 or not valores[0].strip() or len(valores[0].strip()) > 200:
            return self.responder(400, {"erro": "Informe um nome de até 200 caracteres."})
        try:
            dados = self.server.busca.buscar(valores[0].strip())
        except (OSError, URLError, ValueError, KeyError, TypeError):
            logging.exception("Falha ao consultar ou reordenar candidatos.")
            return self.responder(503, {"erro": "Busca temporariamente indisponível."})
        self.responder(200, dados)


if __name__ == "__main__":
    busca = BuscaModelo(Path(os.environ.get("MODELO_DIR", "/modelo")),
                        os.environ.get("ELASTICSEARCH_URL", "http://elasticsearch:9200"))
    servidor = ThreadingHTTPServer(("0.0.0.0", 8000), Atendimento)
    servidor.busca = busca
    servidor.serve_forever()
