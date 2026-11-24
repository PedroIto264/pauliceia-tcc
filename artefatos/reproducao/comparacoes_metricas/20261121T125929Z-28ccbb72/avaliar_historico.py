"""Avalia grafias documentadas e simulações com o Random Forest congelado."""

import argparse
import ast
from collections import defaultdict
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import uuid

from iniciar import COMPOSE, HASH_BACKUP, PASTA, configurar
from preparar_historico import DESTINO, FONTES, ler_csv, salvar_csv, sha
from testar_modelo import MODELO_ESCOLHIDO


def conferir_funcoes_modelo():
    # O carregador foi ampliado para o teste reservado após o treinamento.
    # Compare especificamente cálculo, matriz, previsão e ordenação, sem confundir
    # essa mudança de seleção de partições com mudança das similaridades.
    nomes = {"atributos", "matriz", "pontuar", "ordenar"}
    def funcoes(caminho):
        arvore = ast.parse(caminho.read_text(encoding="utf8"))
        return {n.name: ast.dump(n, include_attributes=False) for n in arvore.body
                if isinstance(n, ast.FunctionDef) and n.name in nomes}
    salvo = funcoes(MODELO_ESCOLHIDO / "modelo_rf.py")
    atual = funcoes(PASTA / "modelo_rf.py")
    if set(salvo) != nomes or atual != salvo:
        raise ValueError("O cálculo de atributos ou a ordenação mudou desde o treinamento.")


def conferir_gabarito():
    from preparar_historico import construir
    from piloto import documentos

    meta = json.loads((DESTINO / "manifesto.json").read_text(encoding="utf8"))
    for caminho, chave in ((DESTINO / "gabarito.csv", "gabarito_sha256"),
                           (DESTINO / "exclusoes.csv", "exclusoes_sha256"),
                           (FONTES, "fontes_sha256"),
                           (PASTA / "preparar_historico.py", "gerador_sha256"),
                           (PASTA / "dados" / "gabarito_piloto.csv", "gabarito_piloto_sha256"),
                           (PASTA / "dados" / "gabarito_ampliado.csv", "gabarito_original_sha256")):
        if sha(caminho) != meta[chave]:
            raise ValueError(f"Arquivo alterado após preparação: {caminho.name}")
    if meta["backup_sha256"] != HASH_BACKUP:
        raise ValueError("Backup incompatível.")
    docs = documentos()
    esperado, _ = construir(docs, ler_csv(PASTA / "dados" / "gabarito_ampliado.csv"),
                            json.loads(FONTES.read_text(encoding="utf8")),
                            ler_csv(PASTA / "dados" / "gabarito_piloto.csv"))
    casos = ler_csv(DESTINO / "gabarito.csv")
    if casos != esperado:
        raise ValueError("O gabarito não corresponde às regras e fontes registradas.")
    return casos, meta, docs


def reordenar(modelo, casos, cache, docs):
    from extrair_logradouros import normalizar
    from modelo_rf import matriz, ordenar, pontuar

    nomes = {str(d["id"]): normalizar(d["nome"]) for d in docs}
    consultas = {c["id_consulta"]: c for c in casos}
    candidatos = {c["id_consulta"]: c for c in cache if c["metodo"] == "bm25_trigramas"}
    if candidatos.keys() != consultas.keys() or len(candidatos) != len(casos):
        raise ValueError("Coleta incompleta.")
    for c in cache:
        ids, scores = c["ids"], c["scores"]
        import math
        if (len(ids) > 100 or len(ids) != len(scores) or len(ids) != len(set(ids))
                or not set(ids) <= nomes.keys()
                or any(not math.isfinite(s) or s < 0 for s in scores)):
            raise ValueError("Candidatos ou escores inválidos.")
    x, _, _, blocos = matriz(consultas, candidatos, nomes, "complementar")
    return ordenar(blocos, pontuar(modelo, x), "random_forest")


def resumir_recortes(linhas):
    from avaliar_gabarito import resumir

    # Nunca misturar grafias documentadas e simulações em uma única taxa principal.
    grupos = defaultdict(list)
    for l in linhas:
        novidade = "repetida" if l["consulta_preexistente"] else "nova"
        grupos[(l["tipo"], "todas", "todas")].append(l)
        grupos[(l["tipo"], l["particao_original"], novidade)].append(l)
    return [dict(categoria=categoria, particao_original=particao, consulta=novidade,
                 resultados=resumir(valores))
            for (categoria, particao, novidade), valores in sorted(grupos.items())]


def comparar(linhas, catalogo):
    por_caso = defaultdict(dict)
    for linha in linhas:
        por_caso[linha["id_consulta"]][linha["metodo"]] = linha
    saida = []
    for metodos in por_caso.values():
        rf, tri, bm = (metodos[m] for m in ("random_forest", "bm25_trigramas", "bm25"))
        ids = rf["ranking"].split("|") if rf["ranking"] else []
        status = "acerto"
        if not tri["acerto_100"]:
            status = "alvo_fora_dos_100"
        elif not rf["acerto_1"]:
            status = "falha_de_ordenacao"
        saida.append({
            "id_consulta": rf["id_consulta"], "consulta": rf["consulta"],
            "nome_referencia": rf["nome_referencia"], "categoria": rf["tipo"],
            "fonte_id": rf["fonte_id"], "particao_original": rf["particao_original"],
            "consulta_preexistente": rf["consulta_preexistente"],
            "posicao_bm25": bm["primeira_posicao"],
            "posicao_trigramas": tri["primeira_posicao"], "posicao_rf": rf["primeira_posicao"],
            "primeiro_rf": catalogo[ids[0]] if ids else "", "status": status,
            "ganho_top1": rf["acerto_1"] - tri["acerto_1"],
        })
    return saida


def relatorio(resumo, comparacao):
    texto = ["# Avaliação complementar de grafias", "",
             "Estudo exploratório construído após o teste reservado; modelo congelado.",
             "Grafias documentadas significam ocorrência em fonte municipal digital. O vínculo",
             "com o catálogo é inferência textual sem revisão independente, não prova espacial.",
             "Simulações não são consultas reais, registros de fala ou erros de OCR observados.",
             "As taxas abaixo não devem ser combinadas com as 1.207 consultas do teste anterior.", "",
             "| Categoria | Método | Consultas | Top-1 | Recall@100 | MRR@100 |",
             "| --- | --- | ---: | ---: | ---: | ---: |"]
    for recorte in resumo["recortes"]:
        if recorte["particao_original"] != "todas":
            continue
        for item in recorte["resultados"]:
            m = item["media_por_consulta"]
            texto.append(f"| {recorte['categoria']} | {item['metodo']} | {item['consultas']} | "
                         f"{m['acerto_1']:.2%} | {m['recall_100']:.2%} | {m['rr_100']:.4f} |")
    texto += ["", "## Exposição anterior", "",
              "Os grupos originais de treino, validação, teste e desenvolvimento são preservados.",
              "O resumo JSON separa as métricas por esses grupos e por consulta nova/repetida.",
              "Até o recorte de ruas de teste é exploratório: a seleção ocorreu depois do teste.",
              "Precision@3 e Precision@5 diferem de Acerto@3 e Acerto@5; ambas estão no resumo.", "",
              "## Falhas do Random Forest", "",
              "| Consulta | Referência | Primeiro resultado | Motivo |",
              "| --- | --- | --- | --- |"]
    falhas = [c for c in comparacao if c["status"] != "acerto"]
    for c in falhas:
        texto.append(f"| {c['consulta']} | {c['nome_referencia']} | {c['primeiro_rf']} | {c['status']} |")
    if not falhas:
        texto += ["", "Nenhuma falha Top-1 neste conjunto complementar."]
    texto += ["", "A comparação completa, incluindo acertos ganhos e perdidos, está em comparacao.csv.",
              "As fontes, o gabarito, as exclusões e os scripts usados acompanham esta execução.",
              f"Modelo SHA-256: `{resumo['modelo_sha256']}`.", ""]
    return "\n".join(texto)


def executar():
    from avaliar_gabarito import LOTE, recuperar
    from piloto import INDICE_CONFIG, elastic, indexar, ndjson
    from testar_modelo import abrir_modelo
    import hashlib

    casos, manifesto, docs = conferir_gabarito()
    modelo, meta_modelo, origem = abrir_modelo(MODELO_ESCOLHIDO)
    treino = json.loads((origem / "resumo.json").read_text(encoding="utf8"))
    if manifesto["gabarito_original_sha256"] != meta_modelo["gabarito_sha256"]:
        raise ValueError("Partições não correspondem ao modelo congelado.")
    conferir_funcoes_modelo()
    esperado = "pauliceia-ruas-" + hashlib.sha256(ndjson([INDICE_CONFIG, *docs])).hexdigest()[:16]
    if esperado != meta_modelo["indice"] or INDICE_CONFIG != treino["indice_config"]:
        raise ValueError("Catálogo ou configuração diverge do treinamento.")
    configurar()
    subprocess.run(COMPOSE + ["up", "-d", "--wait", "elasticsearch"], check=True)
    versao = elastic("GET", "")["version"]["number"]
    if versao != treino["elasticsearch"]:
        raise ValueError("Versão do Elasticsearch diverge do treinamento.")
    indice = indexar(docs)
    raiz = PASTA / ".local" / "historico"
    raiz.mkdir(parents=True, exist_ok=True)
    destino = raiz / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    linhas, cache = [], []
    with TemporaryDirectory(prefix="em-andamento-", dir=raiz) as temporario:
        trabalho = Path(temporario)
        for inicio in range(0, len(casos), LOTE):
            for item in recuperar(indice, casos[inicio:inicio + LOTE]):
                linhas.append(dict(item["linha"], ranking="|".join(item["candidatos"]["ids"])))
                cache.append(item["candidatos"])
            print(f"Consultas coletadas: {min(inicio + LOTE, len(casos))}/{len(casos)}", flush=True)
        linhas += reordenar(modelo, casos, cache, docs)
        # O tempo do Elasticsearch não é tempo de inferência nem latência total.
        for linha in linhas:
            linha.setdefault("elastic_took_ms", "")
        comparacao = comparar(linhas, {str(d["id"]): d["nome"] for d in docs})
        salvar_csv(trabalho / "resultados.csv", linhas, list(linhas[0]))
        salvar_csv(trabalho / "comparacao.csv", comparacao, list(comparacao[0]))
        with gzip.open(trabalho / "candidatos.jsonl.gz", "wt", encoding="utf8") as arquivo:
            for item in cache:
                arquivo.write(json.dumps(item, ensure_ascii=False) + "\n")
        resumo = {
            "execucao": destino.name, "natureza": manifesto["natureza"],
            "manifesto": manifesto, "modelo": MODELO_ESCOLHIDO.name,
            "modelo_sha256": meta_modelo["modelo_sha256"], "versoes": meta_modelo["versoes"],
            "indice": indice, "indice_config": INDICE_CONFIG, "elasticsearch": versao, "k": 100,
            "recortes": resumir_recortes(linhas),
        }
        snapshots = [DESTINO / "gabarito.csv", DESTINO / "manifesto.json", DESTINO / "exclusoes.csv", FONTES,
                     *[PASTA / n for n in ("avaliar_historico.py", "preparar_historico.py", "modelo_rf.py",
                                          "avaliar_gabarito.py", "extrair_logradouros.py", "piloto.py",
                                          "testar_modelo.py", "requirements-modelo.txt")]]
        for caminho in snapshots:
            (trabalho / caminho.name).write_bytes(caminho.read_bytes())
        resumo["arquivos_sha256"] = {f.name: sha(f) for f in sorted(trabalho.iterdir())}
        (trabalho / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        (trabalho / "relatorio.md").write_text(relatorio(resumo, comparacao), encoding="utf8")
        conferir_gabarito()
        if sha(MODELO_ESCOLHIDO / "modelo.joblib") != meta_modelo["modelo_sha256"]:
            raise RuntimeError("O modelo foi alterado durante a avaliação.")
        trabalho.rename(destino)
    for recorte in resumo["recortes"]:
        if recorte["particao_original"] != "todas":
            continue
        for item in recorte["resultados"]:
            m = item["media_por_consulta"]
            print(f"{recorte['categoria']} / {item['metodo']} ({item['consultas']} consultas): "
                  f"Top-1 {m['acerto_1']:.2%}, Recall@100 {m['recall_100']:.2%}, MRR@100 {m['rr_100']:.4f}")
    print(f"Avaliacao complementar salva em: {destino}")
    return destino


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="Confere dados e modelo, sem Docker nem buscas.")
    args = parser.parse_args()
    python = PASTA / ".local" / "venv-modelo" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if Path(sys.prefix).resolve() != python.parent.parent.resolve():
        subprocess.run([str(python), str(Path(__file__).resolve()), *sys.argv[1:]], check=True)
        return
    if args.verificar:
        from testar_modelo import abrir_modelo
        casos, _, _ = conferir_gabarito()
        _, modelo, _ = abrir_modelo(MODELO_ESCOLHIDO)
        conferir_funcoes_modelo()
        print(f"Verificacao OK: {len(casos)} consultas; modelo congelado {modelo['modelo_sha256']}.")
        print("Nenhuma busca foi executada; ainda nao ha metricas complementares.")
    else:
        executar()


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as erro:
        sys.exit(f"Avaliacao historica interrompida: {erro}")
