"""Verifica comparação pareada, empates e alvos ausentes sem treinamento."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from comparar_metricas import avaliar_conjunto, conferir_reproducao, validar_cache, ISOLADAS


class ModeloCongelado:
    classes_ = np.array([0, 1])

    def fit(self, *args, **kwargs):
        raise AssertionError("Comparação não pode treinar.")

    def predict_proba(self, x):
        return np.column_stack([1 - x[:, 0], x[:, 0]])


class ComparacaoTest(unittest.TestCase):
    def setUp(self):
        self.nomes = {"1": "rua alfa beta", "2": "rua beta alfa", "3": "rua gama"}
        self.casos = {}
        for ident, alvo in (("empate", "1"), ("ausente", "3"), ("vazio", "3")):
            self.casos[ident] = {"id_consulta": ident, "grupo": ident, "particao": "teste",
                                 "consulta": self.nomes[alvo], "nome_referencia": self.nomes[alvo],
                                 "ids_relevantes": alvo, "tipo": "fixture", "origem": "fixture"}
        self.cache = []
        for ident in self.casos:
            for metodo in ("bm25", "bm25_trigramas"):
                ids = [] if ident == "vazio" else ["2", "1"]
                self.cache.append({"id_consulta": ident, "metodo": metodo,
                                   "ids": ids, "scores": [2., 1.] if ids else []})

    def test_ties_and_missing_targets_keep_candidate_set(self):
        linhas, empates = avaliar_conjunto(self.casos, self.cache, self.nomes, ModeloCongelado(), "teste")
        self.assertEqual(len(linhas), 21)
        por_chave = {(r["id_consulta"], r["metodo"]): r for r in linhas}
        for metodo in ISOLADAS:
            self.assertEqual(por_chave[("ausente", metodo)]["recall_100"], 0)
            self.assertEqual(por_chave[("ausente", metodo)]["rr_100"], 0)
            self.assertEqual(por_chave[("vazio", metodo)]["ranking"], "")
            self.assertEqual(por_chave[("empate", metodo)]["recall_100"], 1)
        for metodo in ("token_sort", "token_set"):
            self.assertEqual(por_chave[("empate", metodo)]["ranking"], "2|1")
            self.assertEqual(por_chave[("empate", metodo)]["primeira_posicao"], 2)
        self.assertEqual(por_chave[("empate", "damerau_levenshtein")]["ranking"], "1|2")
        self.assertEqual(por_chave[("empate", "random_forest")]["ranking"], "1|2")
        self.assertTrue(any(r["id_consulta"] == "empate" and r["metodo"] == "token_set"
                            and r["candidatos_empatados_no_maior_escore"] == 2 for r in empates))

    def test_rejects_duplicate_and_incomplete_cache(self):
        for cache in (self.cache + [self.cache[0]], self.cache[:-1]):
            with self.assertRaises(ValueError):
                validar_cache(self.casos, cache, self.nomes)

    def test_reproduction_detects_metric_and_label_changes(self):
        linhas, _ = avaliar_conjunto(self.casos, self.cache, self.nomes, ModeloCongelado(), "teste")
        base = [dict(r) for r in linhas if r["metodo"] in ("bm25", "bm25_trigramas", "random_forest")]
        conferir_reproducao(linhas, base)
        base[0]["acerto_1"] = 1 - base[0]["acerto_1"]
        with self.assertRaises(ValueError):
            conferir_reproducao(linhas, base)


if __name__ == "__main__":
    unittest.main()
