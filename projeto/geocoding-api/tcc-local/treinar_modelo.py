"""Prepara as dependências em ambiente local e executa o treinamento."""

import argparse
import hashlib
from pathlib import Path
import subprocess
import sys
import venv


PASTA = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("avaliacao", type=Path, help="Diretório da avaliação com candidatos.jsonl.gz")
    parser.add_argument("--ambiente-pronto", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args()
    pasta = args.avaliacao.resolve()
    for nome in ("resumo.json", "gabarito_ampliado.csv", "candidatos.jsonl.gz"):
        if not (pasta / nome).is_file():
            raise ValueError(f"Arquivo ausente: {pasta / nome}")
    if args.ambiente_pronto:
        from modelo_rf import executar
        executar(pasta)
        return
    ambiente = PASTA / ".local" / "venv-modelo"
    python = ambiente / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.exists():
        print("Criando ambiente Python para o treinamento...", flush=True)
        venv.EnvBuilder(with_pip=True).create(ambiente)
    requisitos = PASTA / "requirements-modelo.txt"
    assinatura = hashlib.sha256(requisitos.read_bytes()).hexdigest()
    marcador = ambiente / "requirements.sha256"
    if not marcador.exists() or marcador.read_text() != assinatura:
        print("Instalando as dependencias do modelo...", flush=True)
        subprocess.run([str(python), "-m", "pip", "install", "--disable-pip-version-check",
                        "--only-binary=:all:", "-r", str(requisitos)], check=True)
        marcador.write_text(assinatura)
    subprocess.run([str(python), str(Path(__file__).resolve()), str(pasta), "--ambiente-pronto"], check=True)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Treinamento interrompido: {erro}")
