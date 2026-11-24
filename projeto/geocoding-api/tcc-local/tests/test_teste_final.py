"""Verifica o fluxo de teste reservado com um modelo congelado e dados artificiais."""

import contextlib
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from avaliar_gabarito import medir
import testar_modelo


class ModeloCongelado:
    classes_ = np.array([0, 1])

    def fit(self, *args, **kwargs):
        raise AssertionError("A avaliação final tentou ajustar o modelo.")

    def predict_proba(self, x):
        return np.column_stack([1 - x[:, 0], x[:, 0]])


class TesteFinalTest(unittest.TestCase):
    def test_compara_tres_metodos_e_preserva_falha_de_recuperacao(self):
        casos = {
            "a": {"id_consulta": "a", "grupo": "alfa", "particao": "teste",
                  "nome_referencia": "rua alfa", "consulta": "rua alfa",
                  "ids_relevantes": "1", "tipo": "fixture", "origem": "fixture"},
            "b": {"id_consulta": "b", "grupo": "beta", "particao": "teste",
                  "nome_referencia": "rua beta", "consulta": "rua beta",
                  "ids_relevantes": "2", "tipo": "fixture", "origem": "fixture"},
        }
        cache = {"a": {"ids": ["2", "1"], "scores": [2.0, 1.0]},
                 "b": {"ids": ["1"], "scores": [1.0]}}
        nomes = {"1": "rua alfa", "2": "rua beta"}
        meta = {"gabarito_sha256": "fixture", "backup_sha256": "fixture", "indice": "fixture",
                "indice_config": {}, "elasticsearch": "fixture", "particoes": ["teste"]}
        with tempfile.TemporaryDirectory() as temporario:
            pasta = Path(temporario)
            modelo, origem, coleta = [pasta / n for n in ("modelo", "origem", "coleta")]
            for p in (modelo, origem, coleta):
                p.mkdir()
            (modelo / "modelo.joblib").write_bytes(b"modelo congelado")
            meta_modelo = dict(meta, modelo_sha256=hashlib.sha256(b"modelo congelado").hexdigest(),
                              parametros={}, versoes={})
            (origem / "resumo.json").write_text(json.dumps(meta))
            (origem / "resultados.csv").write_text("id_consulta\nconsulta_de_treino\n")
            (coleta / "resumo.json").write_text(json.dumps(meta))
            (coleta / "gabarito_ampliado.csv").write_text("fixture")
            (coleta / "candidatos.jsonl.gz").write_bytes(b"fixture")
            linhas = [
                dict(c, metodo="bm25", **medir(cache[k]["ids"], c["ids_relevantes"].split("|")))
                for k, c in casos.items()
            ]
            with (coleta / "resultados.csv").open("w", newline="", encoding="utf-8-sig") as arq:
                writer = csv.DictWriter(arq, fieldnames=linhas[0], delimiter=";")
                writer.writeheader()
                writer.writerows(linhas)
            for nome in ("testar_modelo.py", "modelo_rf.py", "avaliar_gabarito.py", "extrair_logradouros.py"):
                (pasta / nome).write_text("# fixture")
            with (
                patch.object(testar_modelo, "PASTA", pasta),
                patch.object(testar_modelo, "abrir_modelo", return_value=(ModeloCongelado(), meta_modelo, origem)),
                patch("modelo_rf.carregar", return_value=(meta, casos, cache, nomes)) as carregar,
                patch("piloto.documentos", return_value=[{"id": int(k), "nome": v} for k, v in nomes.items()]),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                destino = testar_modelo.avaliar(modelo, coleta)
            carregar.assert_called_once_with(coleta, ("teste",))
            resultado = json.loads((destino / "resumo.json").read_text(encoding="utf8"))
            self.assertEqual(resultado["top1_corrigidos"], 1)
            self.assertEqual(resultado["top1_perdidos"], 0)
            self.assertEqual(resultado["alvo_ausente_top100"], 1)
            self.assertEqual(resultado["falhas_ordenacao_rf"], 0)
            self.assertEqual(len(resultado["resultados"]), 3)
            self.assertEqual(len(testar_modelo.ler_csv(destino / "resultados.csv")), 6)
            self.assertEqual((modelo / "modelo.joblib").read_bytes(), b"modelo congelado")


if __name__ == "__main__":
    unittest.main()
