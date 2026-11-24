"""Regressão da divergência numérica na conferência do modelo salvo."""

import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import joblib
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import modelo_rf


class PersistenciaModeloTest(unittest.TestCase):
    def test_selecao_e_persistencia_preservam_escores_e_ranking(self):
        rng = np.random.default_rng(42)
        x_treino = rng.random((300, len(modelo_rf.ATRIBUTOS)), dtype=np.float32)
        y_treino = (x_treino[:, 0] + x_treino[:, 1] > 1).astype(np.uint8)
        x_validacao = rng.random((500, len(modelo_rf.ATRIBUTOS)), dtype=np.float32)
        blocos = []
        for i in range(100):
            caso = {"id_consulta": str(i), "particao": "validacao",
                    "nome_referencia": str(i), "tipo": "fixture", "ids_relevantes": "2"}
            blocos.append((caso, ["0", "1", "2", "3", "4"], i * 5, (i + 1) * 5))
        with patch.object(modelo_rf, "CONFIGURACOES", [{"max_depth": 12, "min_samples_leaf": 2}]):
            with contextlib.redirect_stdout(io.StringIO()):
                modelo, _ = modelo_rf.selecionar(
                    x_treino, y_treino, np.ones(300), x_validacao, blocos
                )
        self.assertEqual(modelo.n_jobs, 1)
        antes = modelo_rf.pontuar(modelo, x_validacao)
        with tempfile.TemporaryDirectory() as pasta:
            arquivo = Path(pasta) / "modelo.joblib"
            joblib.dump(modelo, arquivo, compress=3)
            restaurado = joblib.load(arquivo)
        depois = modelo_rf.pontuar(restaurado, x_validacao)
        np.testing.assert_array_equal(antes, depois)
        self.assertEqual(modelo_rf.ordenar(blocos, antes), modelo_rf.ordenar(blocos, depois))


if __name__ == "__main__":
    unittest.main()
