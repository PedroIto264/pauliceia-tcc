"""Verifica o oráculo espacial e a contabilização da validação HTTP."""

import contextlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from preparar_validacao_portal import ponto_ewkb, ler_pontos, referencia
import validar_portal as v


class ValidacaoPortalTest(unittest.TestCase):
    def test_oraculo_decodifica_float_intervalos_e_deduplica(self):
        xy = (-46.634, -23.543)
        geom = (b'\x01' + struct.pack('<II', 0x20000001, 4326) + struct.pack('<dd', *xy)).hex()
        self.assertEqual(ponto_ewkb(geom), xy)
        texto = ('COPY public.places_pilot_area2 (id, id_street, number, first_year, last_year, geom) FROM stdin;\n'
                 f'1\t7\t2.10000000000000009\t1930\t1940\t{geom}\n'
                 f'2\t7\t2.10000000000000009\t1930\t1940\t{geom}\n'
                 f'3\t8\t3\t1940\t\\N\t{geom}\n'
                 f'4\t9\t1\t199\t1909\t{geom}\n'
                 '\\.\n')
        pontos, excluidos = ler_pontos(texto.encode())
        self.assertFalse(excluidos)
        self.assertEqual(pontos[0]['numero'], '2.1')
        for ano in (1930, 1935, 1940):
            self.assertEqual(referencia(pontos, 7, '2.1', ano), ([xy], [1, 2]))
        for ano in (1929, 1941):
            self.assertEqual(referencia(pontos, 7, '2.1', ano), ([], []))
        self.assertEqual(referencia(pontos, 8, '3', 2000)[0], [xy])
        self.assertEqual(referencia(pontos, 8, '3', 2001)[0], [])
        self.assertEqual(pontos[3]['inicio'], 199)  # Não inventar 1899/1909.

    def test_comparacao_rejeita_coordenadas_trocadas_duplicadas_e_nan(self):
        esperado = [[-46.6, -23.5], [-46.7, -23.6]]
        self.assertTrue(v.coordenadas_iguais(list(reversed(esperado)), esperado, 1e-9))
        for obtido in ([[-23.5, -46.6], [-23.6, -46.7]], [esperado[0], esperado[0]],
                       [[float('nan'), -23.5], esperado[1]], [], None):
            self.assertFalse(v.coordenadas_iguais(obtido, esperado, 1e-9))
        self.assertTrue(v.coordenadas_iguais([], [], 1e-9))

    def test_estatisticas_separam_falhas(self):
        linhas = [{'ok': True, 'motivo': 'ok', 'ms': 10.},
                  {'ok': True, 'motivo': 'ok', 'ms': 20.},
                  {'ok': False, 'motivo': 'erro_http', 'ms': 15000.}]
        resumo = v.resumir(linhas)
        self.assertEqual(resumo['tentativas'], 3)
        self.assertEqual(resumo['corretas'], 2)
        self.assertEqual(resumo['falhas'], {'erro_http': 1})
        self.assertEqual(resumo['tempo_todas_tentativas']['n'], 3)
        self.assertEqual(resumo['tempo_respostas_corretas']['mediana_ms'], 15.)
        self.assertEqual(resumo['tempo_respostas_corretas']['p95_ms'], 19.5)

    def test_fluxo_salva_aquecimento_separado_e_pontos(self):
        caso = {'id_consulta': 'a', 'consulta': 'rua alfa', 'particao': 'teste', 'tipo': 'original',
                'esperados': [{'id': 1, 'nome': 'rua alfa'}]}
        ponto = {'id_caso': 'p', 'tipo': 'inicio_intervalo', 'id_rua': 1, 'nome': 'rua alfa',
                 'numero': '2.1', 'ano': 1930, 'coordenadas': [[-46.6, -23.5]], 'ids_pontos': [1]}
        protocolo = {'consultas': [caso], 'espaciais': [ponto], 'fluxos': [dict(caso, **ponto)],
                     'repeticoes_medidas': 3, 'timeout_segundos': 15,
                     'tolerancia_coordenadas_graus': 1e-9, 'modelo_sha256': 'fixture', 'limites': []}
        def resposta(caminho, parametros, timeout):
            dados = ponto['coordenadas'] if caminho.endswith('/pontos') else caso['esperados']
            return {'http_status': 200, 'ms': 1., 'modelo': 'fixture', 'dados': dados, 'erro_transporte': ''}
        with tempfile.TemporaryDirectory() as t:
            pasta = Path(t)
            (pasta/'protocolo.json').write_text('{}')
            for nome in ('validar_portal.py', 'preparar_validacao_portal.py'):
                (pasta/nome).write_text('# fixture')
            with (patch.object(v, 'PASTA', pasta), patch.object(v, 'PASTA_DADOS', pasta),
                  patch.object(v, 'conferir_protocolo', return_value=protocolo),
                  patch.object(v, 'requisitar', side_effect=resposta), contextlib.redirect_stdout(io.StringIO())):
                destino = v.executar(protocolo)
            resumo = json.loads((destino/'resumo.json').read_text(encoding='utf8'))
            self.assertTrue(resumo['completa'])
            self.assertEqual(resumo['aquecimento']['tentativas'], 1)
            self.assertEqual(resumo['busca']['tentativas'], 3)
            self.assertEqual(resumo['pontos']['corretas'], 1)
            self.assertEqual(resumo['fluxos']['corretas'], 3)


if __name__ == '__main__':
    unittest.main()
