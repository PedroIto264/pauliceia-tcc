"""Regressões da integração entre recuperação, reordenação e contrato HTTP."""

from io import BytesIO
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from servico_modelo import Atendimento, BuscaModelo


class BuscaOnlineTest(unittest.TestCase):
    def setUp(self):
        self.busca = BuscaModelo.__new__(BuscaModelo)
        self.busca.modelo = object()
        self.busca.resumo = {"indice": "indice-congelado"}
        self.busca.elasticsearch = "http://elasticsearch:9200"

    def test_recupera_cem_e_reordena_antes_de_limitar_a_cinco(self):
        hits = [{"_source": {"id": i, "nome": f"rua exemplo {i}"}, "_score": float(101 - i)}
                for i in range(1, 101)]
        resposta = {"_shards": {"failed": 0}, "hits": {"hits": hits}}
        with (
            patch("servico_modelo.urlopen", return_value=BytesIO(json.dumps(resposta).encode())) as http,
            patch("servico_modelo.pontuar", return_value=np.arange(100, dtype=float)) as pontuar,
        ):
            candidatos = self.busca.buscar("rua exmplo")
        self.assertEqual([c["id"] for c in candidatos], [100, 99, 98, 97, 96])
        request = http.call_args.args[0]
        corpo = json.loads(request.data)
        self.assertEqual(corpo["size"], 100)
        self.assertEqual(corpo["query"]["multi_match"]["fields"], ["nome", "nome.tri"])
        self.assertEqual(corpo["sort"], [{"_score": "desc"}, {"id": "asc"}])
        self.assertEqual(request.full_url, "http://elasticsearch:9200/indice-congelado/_search")
        self.assertEqual(pontuar.call_args.args[1].shape, (100, 7))
        self.assertEqual(pontuar.call_args.args[1].dtype, np.float32)

    def test_lista_vazia_empates_e_ids_repetidos(self):
        self.assertEqual(self.busca.reordenar("rua teste", []), [])
        hits = [{"_source": {"id": i, "nome": "rua teste"}, "_score": 1.0} for i in (2, 1)]
        with patch("servico_modelo.pontuar", return_value=np.array([.5, .5])):
            self.assertEqual([c["id"] for c in self.busca.reordenar("rua teste", hits)], [2, 1])
        with self.assertRaises(ValueError):
            self.busca.reordenar("rua teste", [hits[0], hits[0]])

    def test_http_rejeita_nome_invalido_e_sinaliza_falha(self):
        handler = Atendimento.__new__(Atendimento)
        handler.server = SimpleNamespace(busca=Mock())
        handler.responder = Mock()
        handler.path = "/candidatos?nome=rua&nome=outra"
        handler.do_GET()
        self.assertEqual(handler.responder.call_args.args[0], 400)
        handler.server.busca.buscar.assert_not_called()
        handler.path = "/candidatos?nome=rua%20teste"
        handler.server.busca.buscar.side_effect = OSError("Serviço indisponível")
        with patch("servico_modelo.logging.exception"):
            handler.do_GET()
        self.assertEqual(handler.responder.call_args.args[0], 503)


if __name__ == "__main__":
    unittest.main()
