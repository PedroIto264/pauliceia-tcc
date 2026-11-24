"""Protege relevância, exposição anterior e falhas de recuperação no complemento."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preparar_historico import construir
from avaliar_historico import reordenar, resumir_recortes, comparar, relatorio
from avaliar_gabarito import medir


class ModeloSomentePrevisao:
    classes_ = np.array([0, 1])

    def fit(self, *args, **kwargs):
        raise AssertionError("Não pode treinar na avaliação complementar.")

    def predict_proba(self, x):
        return np.column_stack([1 - x[:, 0], x[:, 0]])


class HistoricoTest(unittest.TestCase):
    def test_fontes_duplicatas_colisoes_e_particoes(self):
        docs = [{"id": 1, "nome": "Rua Theodoro"}, {"id": 2, "nome": "rua bella"},
                {"id": 3, "nome": "rua bela"}, {"id": 4, "nome": "rua theodoro"}]
        anteriores = [{"nome_referencia": d["nome"], "consulta": d["nome"], "tipo": "original",
                       "grupo": str(d["id"]), "particao": "treino"} for d in docs[:3]]
        anteriores.append(dict(anteriores[0], consulta="rua teodoro", tipo="omissao"))
        fontes = {"fontes": [{"id": "fixture", "casos": [
            {"id_rua": 1, "consulta": "Rua Teodoro", "regra": "th -> t"}]}]}
        aceitas, excluidas = construir(docs, anteriores, fontes)
        self.assertEqual(len(aceitas), 1)
        self.assertEqual(aceitas[0]["tipo"], "grafia_documentada")
        self.assertEqual(aceitas[0]["ids_relevantes"], "1|4")
        self.assertEqual(aceitas[0]["particao_original"], "treino")
        self.assertEqual(aceitas[0]["consulta_preexistente"], "treino")
        motivos = {c["motivo"] for c in excluidas}
        self.assertIn("consulta_coincide_com_outro_nome_do_catalogo", motivos)
        self.assertIn("consulta_alvo_duplicados_prioridade_documentada", motivos)

    def test_reordenacao_nao_injeta_alvo_ausente_e_separa_categorias(self):
        docs = [{"id": 1, "nome": "rua alfa"}, {"id": 2, "nome": "rua beta"}]
        casos = [{"id_consulta": "a", "grupo": "a", "particao": "complementar",
                  "nome_referencia": "rua alfa", "consulta": "rua alfa", "ids_relevantes": "1",
                  "tipo": "grafia_documentada", "fonte_id": "fixture",
                  "particao_original": "treino", "consulta_preexistente": "treino"},
                 {"id_consulta": "b", "grupo": "b", "particao": "complementar",
                  "nome_referencia": "rua beta", "consulta": "rua beta", "ids_relevantes": "2",
                  "tipo": "fonetica_simulada", "fonte_id": "",
                  "particao_original": "teste", "consulta_preexistente": ""}]
        cache = [{"id_consulta": "a", "metodo": "bm25_trigramas", "ids": ["2", "1"], "scores": [2., 1.]},
                 {"id_consulta": "b", "metodo": "bm25_trigramas", "ids": [], "scores": []}]
        rf = reordenar(ModeloSomentePrevisao(), casos, cache, docs)
        self.assertEqual(rf[0]["primeira_posicao"], 1)
        self.assertEqual(rf[1]["acerto_100"], 0)
        self.assertEqual(rf[1]["rr_100"], 0)
        self.assertEqual(rf[1]["ranking"], "")
        linhas = list(rf)
        for caso, c in zip(casos, cache):
            for metodo in ("bm25", "bm25_trigramas"):
                linhas.append(dict(caso, metodo=metodo, ranking="|".join(c["ids"]),
                                   **medir(c["ids"], caso["ids_relevantes"].split("|"))))
        recortes = resumir_recortes(linhas)
        self.assertEqual({r["categoria"] for r in recortes}, {"grafia_documentada", "fonetica_simulada"})
        self.assertTrue(any(r["particao_original"] == "treino" and r["consulta"] == "repetida" for r in recortes))
        self.assertTrue(any(r["particao_original"] == "teste" and r["consulta"] == "nova" for r in recortes))
        comparacao = comparar(linhas, {"1": "rua alfa", "2": "rua beta"})
        self.assertEqual(comparacao[0]["ganho_top1"], 1)
        self.assertEqual(comparacao[1]["status"], "alvo_fora_dos_100")
        texto = relatorio({"recortes": recortes, "modelo_sha256": "fixture"}, comparacao)
        self.assertIn("alvo_fora_dos_100", texto)
        self.assertIn("não prova espacial", texto)


if __name__ == "__main__":
    unittest.main()
