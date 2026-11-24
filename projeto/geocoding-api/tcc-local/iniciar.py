"""Restaura o backup do TCC e verifica o geocodificador no Docker local."""

import hashlib
import json
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.error import URLError
from urllib.request import urlopen


PASTA = Path(__file__).resolve().parent
BACKUP = PASTA.parents[2] / "dados" / "backup_dev.sql"
HASH_BACKUP = "8004407db214a605561e6c3d8f57643f6f66ad0ada40971ea288757964880fac"
ARQUIVO_ENV = PASTA / ".local" / "docker.env"
COMPOSE = ["docker", "compose", "--env-file", str(ARQUIVO_ENV), "-f", str(PASTA / "compose.yaml")]
URL = "http://127.0.0.1:3130/api/geocoding"


def configurar():
    ARQUIVO_ENV.parent.mkdir(exist_ok=True)
    try:
        with ARQUIVO_ENV.open("x", encoding="ascii") as arquivo:
            for nome in ("TCC_DB_PASSWORD", "TCC_API_PASSWORD"):
                arquivo.write(f"{nome}={secrets.token_hex(32)}\n")
    except FileExistsError:
        pass


def psql(banco, sql, transacao=False):
    comando = COMPOSE + [
        "exec", "-T", "db", "psql", "-X", "-qAt", "-U", "postgres", "-d", banco,
        "-v", "ON_ERROR_STOP=1", "-v", "VERBOSITY=terse", "-v", "SHOW_CONTEXT=never",
    ]
    if transacao:
        comando.append("--single-transaction")
    resultado = subprocess.run(comando + ["-f", "-"], input=sql, stdout=subprocess.PIPE, check=True)
    return resultado.stdout.decode("utf-8").strip()


def restaurar(conteudo):
    psql("postgres", rb"""
SELECT pg_advisory_lock(8764501);
SELECT 'CREATE ROLE pauliceia NOLOGIN' WHERE NOT EXISTS
    (SELECT FROM pg_roles WHERE rolname = 'pauliceia') \gexec
\getenv senha TCC_API_PASSWORD
SELECT format('CREATE ROLE tcc_consulta LOGIN PASSWORD %L', :'senha') WHERE NOT EXISTS
    (SELECT FROM pg_roles WHERE rolname = 'tcc_consulta') \gexec
SELECT 'CREATE DATABASE pauliceia TEMPLATE template0 ENCODING ''UTF8''' WHERE NOT EXISTS
    (SELECT FROM pg_database WHERE datname = 'pauliceia') \gexec
""")
    marcador = psql("pauliceia", b"SELECT to_regclass('tcc_local.restauracao') IS NOT NULL;")
    if marcador == "t":
        if psql("pauliceia", b"SELECT sha256 FROM tcc_local.restauracao;") != HASH_BACKUP:
            raise RuntimeError("O volume ja contem outra restauracao. Confira o banco antes de continuar.")
        return

    # O PostgreSQL 16 removeu esta opcao do PostgreSQL 9.6.
    antigo = b"SET default_with_oids = false;"
    if conteudo.splitlines().count(antigo) != 1:
        raise RuntimeError("Configuracao de OIDs inesperada no dump.")
    prefixo = b"""
SELECT pg_advisory_xact_lock(8764502);
DO $$ BEGIN
    IF EXISTS (SELECT FROM pg_tables WHERE schemaname NOT IN ('pg_catalog', 'information_schema')) THEN
        RAISE EXCEPTION 'O banco pauliceia ja contem tabelas. Restauracao cancelada.';
    END IF;
END $$;
"""
    sufixo = b"""
GRANT USAGE ON SCHEMA public TO tcc_consulta;
GRANT SELECT ON public.streets_pilot_area, public.places_pilot_area2, public.places_pilot_area TO tcc_consulta;
CREATE SCHEMA tcc_local;
CREATE TABLE tcc_local.restauracao (sha256 text PRIMARY KEY);
INSERT INTO tcc_local.restauracao VALUES ('""" + HASH_BACKUP.encode("ascii") + b"""');
"""
    psql("pauliceia", prefixo + conteudo.replace(antigo, b"", 1) + sufixo, transacao=True)


def conferir_banco():
    contagens = psql("pauliceia", b"""
SELECT count(*), count(NULLIF(trim(name), '')), count(geom) FROM public.streets_pilot_area;
""")
    if contagens != "873|868|871":
        raise RuntimeError(f"Contagens inesperadas (total|com nome|com geometria): {contagens}")
    ponto = psql("pauliceia", b"""
SELECT ST_AsText(p.geom) FROM public.places_pilot_area2 p
JOIN public.streets_pilot_area s ON s.id = p.id_street::integer
WHERE s.name = 'rua tres de dezembro' AND p.number::float = 7
  AND 1933 BETWEEN p.first_year::integer AND p.last_year::integer;
""")
    if not ponto or len(ponto.splitlines()) != 1:
        raise RuntimeError("O banco nao retornou uma geometria unica para o endereco de controle.")
    print("Banco conferido: 873 registros de logradouro, 868 com nome e 871 com geometria.", flush=True)
    return ponto


def conferir_api(ponto):
    for tentativa in range(30):
        try:
            with urlopen(URL + "/streets", timeout=10) as resposta:
                ruas = json.load(resposta)
            break
        except (URLError, TimeoutError, ConnectionError):
            if tentativa == 29:
                raise
            time.sleep(1)
    if not isinstance(ruas, list) or len(ruas) != 873:
        raise RuntimeError("A API retornou uma lista de logradouros inesperada.")

    with urlopen(URL + "/geolocation/rua%20tres%20de%20dezembro,7,1933/json", timeout=20) as resposta:
        resultado = json.load(resposta)
    if not isinstance(resultado, list) or len(resultado) != 2:
        raise RuntimeError("Formato de resposta do geocodificador inesperado.")
    candidatos = resultado[1]
    if not isinstance(candidatos, list) or len(candidatos) != 1 or not isinstance(candidatos[0], dict):
        raise RuntimeError("O geocodificador nao retornou um unico endereco.")
    endereco = candidatos[0]
    if endereco.get("status") != 1 or endereco.get("confidence") != 1 or endereco.get("geom") != ponto:
        raise RuntimeError("A resposta da API diverge do ponto historico armazenado no PostGIS.")
    print("Teste OK: Rua Tres de Dezembro, 7 (1933). A geometria da API coincide com a do banco.")


def main():
    conteudo = BACKUP.read_bytes()
    if hashlib.sha256(conteudo).hexdigest() != HASH_BACKUP:
        raise RuntimeError(f"O arquivo {BACKUP.name} difere do backup analisado.")
    subprocess.run(["docker", "info", "--format", "Docker Engine {{.ServerVersion}} | {{.OSType}}"], check=True)
    configurar()
    subprocess.run(COMPOSE + ["up", "-d", "--wait", "db"], check=True)
    print("Conferindo a restauracao do backup...", flush=True)
    restaurar(conteudo)
    ponto = conferir_banco()
    subprocess.run(COMPOSE + ["up", "-d", "--build", "api"], check=True)
    conferir_api(ponto)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Verificacao interrompida: {erro}")
