"""Gera o catálogo de logradouros usado na avaliação da busca."""

import csv
import hashlib
from pathlib import Path
import unicodedata

from iniciar import BACKUP, HASH_BACKUP


DESTINO = Path(__file__).resolve().parent / "dados" / "logradouros.csv"
TABELA = "COPY public.streets_pilot_area ("
CAMPOS = ("id", "nome_original", "nome_normalizado", "ano_inicial", "ano_final", "tem_geometria")


def normalizar(nome):
    texto = unicodedata.normalize("NFD", nome.casefold())
    sem_acentos = "".join(c for c in texto if not unicodedata.combining(c))
    return " ".join(sem_acentos.split())


def extrair(conteudo):
    colunas = None
    registros = []
    for linha in conteudo.decode("utf-8").split("\n"):
        if colunas is None:
            if linha.startswith(TABELA):
                colunas = linha.removeprefix(TABELA).removesuffix(") FROM stdin;").split(", ")
            continue
        if linha == r"\.":
            return sorted(registros, key=lambda registro: registro["id"])
        dados = dict(zip(colunas, linha.split("\t"), strict=True))
        nome = "" if dados["name"] == r"\N" else dados["name"]
        registros.append({
            "id": int(dados["id"]),
            "nome_original": nome,
            "nome_normalizado": normalizar(nome),
            "ano_inicial": "" if dados["first_year"] == r"\N" else dados["first_year"],
            "ano_final": "" if dados["last_year"] == r"\N" else dados["last_year"],
            "tem_geometria": int(dados["geom"] != r"\N"),
        })
    raise ValueError("Bloco COPY de streets_pilot_area incompleto ou ausente.")


def main():
    conteudo = BACKUP.read_bytes()
    if hashlib.sha256(conteudo).hexdigest() != HASH_BACKUP:
        raise ValueError("O backup difere da versao usada na avaliacao.")
    registros = extrair(conteudo)
    DESTINO.parent.mkdir(exist_ok=True)
    with DESTINO.open("w", encoding="utf-8-sig", newline="") as arquivo:
        tabela = csv.DictWriter(arquivo, fieldnames=CAMPOS, delimiter=";")
        tabela.writeheader()
        tabela.writerows(registros)
    print(f"{len(registros)} registros gravados em {DESTINO}")


if __name__ == "__main__":
    main()
