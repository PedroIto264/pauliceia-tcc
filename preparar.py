"""Verifica os artefatos publicados e restaura suas cópias de execução local."""

import hashlib
import json
from pathlib import Path
import shutil
import sys

RAIZ = Path(__file__).resolve().parent
ORIGEM = RAIZ / "artefatos" / "reproducao"
DESTINO = RAIZ / "projeto" / "geocoding-api" / "tcc-local" / ".local"


def sha256(arquivo):
    return hashlib.sha256(arquivo.read_bytes()).hexdigest()


def main():
    manifesto = json.loads((RAIZ / "artefatos" / "sha256.json").read_text(encoding="utf-8"))
    encontrados = {f.relative_to(ORIGEM).as_posix() for f in ORIGEM.rglob("*") if f.is_file()}
    if encontrados != set(manifesto):
        raise ValueError("A lista de artefatos difere do manifesto SHA-256.")
    # Conferir tudo antes de copiar; não substituir resultados locais divergentes.
    for relativo, esperado in manifesto.items():
        fonte = ORIGEM / relativo
        alvo = DESTINO / relativo
        if not fonte.resolve().is_relative_to(ORIGEM.resolve()) or not alvo.resolve().is_relative_to(DESTINO.resolve()):
            raise ValueError("Caminho fora da pasta de artefatos.")
        if sha256(fonte) != esperado:
            raise ValueError(f"Artefato alterado: {relativo}")
        if alvo.exists() and sha256(alvo) != esperado:
            raise ValueError(f"Resultado local divergente; preserve-o antes de continuar: {relativo}")
    for relativo in manifesto:
        alvo = DESTINO / relativo
        if not alvo.exists():
            alvo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ORIGEM / relativo, alvo)
    print(f"{len(manifesto)} artefatos conferidos e disponíveis em tcc-local/.local.")
    backup = RAIZ / "dados" / "backup_dev.sql"
    if not backup.exists():
        print("Backup privado ausente. Consulte dados/README.md antes de iniciar o portal.")
    elif sha256(backup) != "8004407db214a605561e6c3d8f57643f6f66ad0ada40971ea288757964880fac":
        raise ValueError("O backup local difere do usado no experimento.")
    else:
        print("Backup local conferido; ele permanece excluído do Git.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError) as erro:
        sys.exit(f"Preparação interrompida: {erro}")
