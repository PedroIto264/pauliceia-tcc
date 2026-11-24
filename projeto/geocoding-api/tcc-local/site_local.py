"""Inicia o portal local e confere o caminho entre o site, o índice e o PostGIS."""

import json
import hashlib
import subprocess
import sys
from urllib.parse import urlencode
from urllib.request import urlopen

from iniciar import COMPOSE, configurar, conferir_banco, psql
from piloto import documentos, indexar
from testar_modelo import MODELO_ESCOLHIDO


PORTAL = "http://127.0.0.1:3180"


def obter(caminho, modelo_esperado=None, **parametros):
    url = PORTAL + "/api/geocoding/" + caminho + "?" + urlencode(parametros)
    with urlopen(url, timeout=15) as resposta:
        if modelo_esperado is not None and resposta.headers.get("X-Pauliceia-Modelo") != modelo_esperado:
            raise RuntimeError("O portal respondeu com outro modelo de busca.")
        return json.load(resposta)


def main():
    resumo = json.loads((MODELO_ESCOLHIDO / "resumo.json").read_text(encoding="utf8"))
    modelo_hash = hashlib.sha256((MODELO_ESCOLHIDO / "modelo.joblib").read_bytes()).hexdigest()
    if modelo_hash != resumo["modelo_sha256"]:
        raise RuntimeError("O modelo difere do arquivo avaliado.")
    configurar()
    subprocess.run(COMPOSE + ["up", "-d", "--wait", "db", "elasticsearch"], check=True)
    conferir_banco()
    if indexar(documentos()) != resumo["indice"]:
        raise RuntimeError("O catálogo difere do índice usado pelo modelo.")
    try:
        subprocess.run(COMPOSE + ["up", "-d", "--build", "--wait", "modelo", "api", "site"], check=True)
    except subprocess.CalledProcessError:
        subprocess.run(COMPOSE + ["logs", "--tail", "30", "modelo", "api", "site"])
        raise
    candidatos = obter("candidatos", modelo_esperado=modelo_hash, nome="beco dos aflitos")
    if not candidatos or candidatos[0] != {"id": 440, "nome": "becco dos afflictos"}:
        raise RuntimeError("A busca pelo portal nao retornou a rua esperada.")
    for consulta, id_esperado in (("rua ancheita", 44), ("rua cotsa", 386)):
        candidatos = obter("candidatos", modelo_esperado=modelo_hash, nome=consulta)
        if not candidatos or candidatos[0]["id"] != id_esperado:
            raise RuntimeError(f"O modelo nao colocou a rua esperada em primeiro lugar para {consulta}.")
    print("Teste OK: Random Forest ativo no portal; rua ancheita e rua cotsa em primeiro lugar.")
    pontos = obter("candidatos/440/pontos", numero=11, ano=1940)
    controle = json.loads(psql("pauliceia", b"""
        SELECT json_build_array(ST_X(geom), ST_Y(geom))
        FROM public.places_pilot_area2 WHERE id = 4359;
    """))
    if pontos != [controle] or obter("candidatos/440/pontos", numero=11, ano=1800):
        raise RuntimeError("A consulta de pontos pelo portal diverge do PostGIS.")
    print("Teste OK: o portal encontrou a rua, o ponto de 1940 e a ausencia de ponto em 1800.")
    print(f"Mapa do TCC: {PORTAL}/portal/explore")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Portal interrompido: {erro}")
