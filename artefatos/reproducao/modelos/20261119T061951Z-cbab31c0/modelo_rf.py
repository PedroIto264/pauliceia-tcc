"""Treina uma reordenação supervisionada dos candidatos já recuperados."""

import csv
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import platform
from tempfile import TemporaryDirectory
import uuid

import joblib
import numpy as np
import rapidfuzz
from rapidfuzz.distance import DamerauLevenshtein, JaroWinkler, Levenshtein
from rapidfuzz.fuzz import token_set_ratio, token_sort_ratio
import sklearn
from sklearn.ensemble import RandomForestClassifier

from avaliar_gabarito import medir, resumir
from extrair_logradouros import normalizar
from iniciar import HASH_BACKUP, PASTA
from piloto import documentos
from preparar_gabarito import conferir


ATRIBUTOS = ["damerau_levenshtein", "jaro_winkler", "token_sort", "token_set",
             "levenshtein", "escore_relativo", "razao_comprimentos"]
# A grade é definida antes de observar os resultados do modelo.
CONFIGURACOES = [
    {"max_depth": 12, "min_samples_leaf": 2},
    {"max_depth": 12, "min_samples_leaf": 5},
    {"max_depth": None, "min_samples_leaf": 2},
    {"max_depth": None, "min_samples_leaf": 5},
]


def atributos(consulta, candidato, escore, maior_escore):
    return [
        DamerauLevenshtein.normalized_similarity(consulta, candidato),
        JaroWinkler.normalized_similarity(consulta, candidato),
        token_sort_ratio(consulta, candidato) / 100,
        token_set_ratio(consulta, candidato) / 100,
        Levenshtein.normalized_similarity(consulta, candidato),
        escore / maior_escore if maior_escore else 0,
        min(len(consulta), len(candidato)) / max(len(consulta), len(candidato), 1),
    ]


def carregar(pasta):
    resumo = json.loads((pasta / "resumo.json").read_text(encoding="utf8"))
    gabarito = pasta / "gabarito_ampliado.csv"
    if hashlib.sha256(gabarito.read_bytes()).hexdigest() != resumo["gabarito_sha256"]:
        raise ValueError("O gabarito diverge da avaliação.")
    if resumo["backup_sha256"] != HASH_BACKUP or resumo["k"] != 100:
        raise ValueError("Backup ou quantidade de candidatos incompatível.")
    with gabarito.open(encoding="utf-8-sig", newline="") as arq:
        todos = list(csv.DictReader(arq, delimiter=";"))
    docs = documentos()
    conferir(todos, docs)
    casos = {c["id_consulta"]: c for c in todos if c["particao"] in {"treino", "validacao"}}
    recuperados = {}
    ids_catalogo = {str(d["id"]) for d in docs}
    with gzip.open(pasta / "candidatos.jsonl.gz", "rt", encoding="utf8") as arq:
        for linha in arq:
            item = json.loads(linha)
            if item["metodo"] != "bm25_trigramas" or item["id_consulta"] not in casos:
                continue
            chave = item["id_consulta"]
            if chave in recuperados:
                raise ValueError("Consulta duplicada no cache.")
            ids, scores = item["ids"], item["scores"]
            if len(ids) != len(scores) or len(ids) > 100 or len(ids) != len(set(ids)):
                raise ValueError("Lista de candidatos inconsistente.")
            if not set(ids) <= ids_catalogo or any(not np.isfinite(s) or s < 0 for s in scores):
                raise ValueError("Candidato ou escore inválido.")
            recuperados[chave] = item
    if recuperados.keys() != casos.keys():
        raise ValueError("A avaliação deve conter todas as consultas de treino e validação.")
    return resumo, casos, recuperados, {str(d["id"]): normalizar(d["nome"]) for d in docs}


def matriz(casos, recuperados, nomes, particao):
    pares, rotulos, pesos, blocos = [], [], [], []
    for caso in casos.values():
        if caso["particao"] != particao:
            continue
        candidatos = recuperados[caso["id_consulta"]]
        ids, scores = candidatos["ids"], candidatos["scores"]
        inicio = len(pares)
        consulta = normalizar(caso["consulta"])
        relevantes = set(caso["ids_relevantes"].split("|"))
        maior = max(scores, default=0)
        for candidato, score in zip(ids, scores, strict=True):
            pares.append(atributos(consulta, nomes[candidato], score, maior))
            rotulos.append(int(candidato in relevantes))
            pesos.append(1 / len(ids))
        # Consultas sem candidatos também entram nas métricas.
        blocos.append((caso, ids, inicio, len(pares)))
    return (np.asarray(pares, dtype=np.float32).reshape(-1, len(ATRIBUTOS)),
            np.asarray(rotulos, dtype=np.uint8), np.asarray(pesos), blocos)


def ordenar(blocos, probabilidades=None, metodo="bm25_trigramas"):
    linhas = []
    for caso, ids, inicio, fim in blocos:
        ordenados = ids
        if probabilidades is not None:
            # Empates preservam a posição anterior do Elasticsearch.
            ordem = np.argsort(-probabilidades[inicio:fim], kind="stable")
            ordenados = [ids[i] for i in ordem]
        linhas.append(dict(caso, metodo=metodo,
                           **medir(ordenados, caso["ids_relevantes"].split("|")),
                           ranking="|".join(ordenados)))
    return linhas


def pontuar(modelo, matriz_x):
    if not len(matriz_x):
        return np.empty(0)
    positiva = list(modelo.classes_).index(1)
    return modelo.predict_proba(matriz_x)[:, positiva]


def selecionar(x_treino, y_treino, pesos, x_validacao, blocos):
    if set(y_treino) != {0, 1} or not blocos:
        raise ValueError("Treino exige pares positivos e negativos, e validação exige consultas.")
    melhor, chave_melhor, tentativas = None, None, []
    for config in CONFIGURACOES:
        modelo = RandomForestClassifier(n_estimators=200, random_state=42, n_jobs=4,
                                        class_weight="balanced_subsample", **config)
        modelo.fit(x_treino, y_treino, sample_weight=pesos)
        # A soma sequencial das árvores mantém os escores e empates reproduzíveis.
        modelo.set_params(n_jobs=1)
        linhas = ordenar(blocos, pontuar(modelo, x_validacao), "random_forest")
        metricas = resumir(linhas)[0]
        macro = metricas["media_por_nome"]
        chave = (macro["rr_100"], macro["acerto_1"])
        tentativas.append({"configuracao": config, "validacao": metricas})
        print(f"RF {config}: Top-1 {metricas['media_por_consulta']['acerto_1']:.2%}, "
              f"MRR por nome {macro['rr_100']:.4f}", flush=True)
        if chave_melhor is None or chave > chave_melhor:
            melhor, chave_melhor = modelo, chave
    return melhor, tentativas


def executar(pasta):
    resumo_base, casos, cache, nomes = carregar(pasta)
    print("Calculando as similaridades dos pares de treino...", flush=True)
    x_t, y_t, pesos, blocos_t = matriz(casos, cache, nomes, "treino")
    print(f"Treino: {len(x_t)} pares, {int(y_t.sum())} relevantes.", flush=True)
    x_v, _, _, blocos_v = matriz(casos, cache, nomes, "validacao")
    modelo, tentativas = selecionar(x_t, y_t, pesos, x_v, blocos_v)
    linhas = ordenar(blocos_t) + ordenar(blocos_v)
    linhas += ordenar(blocos_t, pontuar(modelo, x_t), "random_forest")
    linhas += ordenar(blocos_v, pontuar(modelo, x_v), "random_forest")
    base_v = {c["id_consulta"]: c for c in linhas if c["particao"] == "validacao" and c["metodo"] == "bm25_trigramas"}
    rf_v = [c for c in linhas if c["particao"] == "validacao" and c["metodo"] == "random_forest"]
    mudancas = [
        dict(id_consulta=r["id_consulta"], consulta=r["consulta"], nome_referencia=r["nome_referencia"],
             tipo=r["tipo"], posicao_anterior=base_v[r["id_consulta"]]["primeira_posicao"],
             posicao_rf=r["primeira_posicao"])
        for r in rf_v if r["primeira_posicao"] != base_v[r["id_consulta"]]["primeira_posicao"]
    ]
    id_execucao = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    raiz = PASTA / ".local" / "modelos"
    raiz.mkdir(parents=True, exist_ok=True)
    destino = raiz / id_execucao
    with TemporaryDirectory(prefix="em-andamento-", dir=raiz) as temporario:
        trabalho = Path(temporario)
        modelo_path = trabalho / "modelo.joblib"
        joblib.dump({"modelo": modelo, "atributos": ATRIBUTOS}, modelo_path, compress=3)
        restaurado = joblib.load(modelo_path)["modelo"]
        if not np.array_equal(pontuar(modelo, x_v), pontuar(restaurado, x_v)):
            raise RuntimeError("O modelo salvo diverge do modelo treinado.")
        for nome, registros, campos in (
            ("resultados.csv", linhas, list(linhas[0])),
            ("mudancas_validacao.csv", mudancas,
             ["id_consulta", "consulta", "nome_referencia", "tipo", "posicao_anterior", "posicao_rf"]),
        ):
            with (trabalho / nome).open("w", encoding="utf-8-sig", newline="") as arq:
                writer = csv.DictWriter(arq, fieldnames=campos, delimiter=";")
                writer.writeheader()
                writer.writerows(registros)
        resumo = {
            "execucao": id_execucao, "avaliacao_origem": pasta.name,
            "gabarito_sha256": resumo_base["gabarito_sha256"], "backup_sha256": HASH_BACKUP,
            "indice": resumo_base["indice"], "atributos": ATRIBUTOS,
            "criterio_selecao": "MRR por nome na validacao; desempate Top-1 por nome; depois ordem da grade",
            "parametros": modelo.get_params(), "tentativas": tentativas,
            "tarefas_paralelas_treino": 4,
            "versoes": {"python": platform.python_version(), "sklearn": sklearn.__version__,
                        "rapidfuzz": rapidfuzz.__version__, "numpy": np.__version__},
            "pares_treino": len(x_t), "positivos_treino": int(y_t.sum()),
            "consultas_treino": len(blocos_t), "consultas_validacao": len(blocos_v),
            "resultados": resumir(linhas),
            "validacao_top1_corrigidos": sum(r["acerto_1"] > base_v[r["id_consulta"]]["acerto_1"] for r in rf_v),
            "validacao_top1_perdidos": sum(r["acerto_1"] < base_v[r["id_consulta"]]["acerto_1"] for r in rf_v),
            "importancias": dict(zip(ATRIBUTOS, modelo.feature_importances_.tolist())),
            "modelo_sha256": hashlib.sha256(modelo_path.read_bytes()).hexdigest(),
            "entradas_sha256": {
                nome: hashlib.sha256((pasta / nome).read_bytes()).hexdigest()
                for nome in ("resumo.json", "candidatos.jsonl.gz", "gabarito_ampliado.csv")
            },
        }
        (trabalho / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        for nome in ("modelo_rf.py", "avaliar_gabarito.py", "preparar_gabarito.py",
                     "extrair_logradouros.py", "requirements-modelo.txt"):
            (trabalho / nome).write_bytes((PASTA / nome).read_bytes())
        trabalho.rename(destino)
    for item in resumo["resultados"]:
        m = item["media_por_consulta"]
        print(f"{item['particao']} / {item['metodo']}: Top-1 {m['acerto_1']:.2%}, "
              f"Recall@100 {m['recall_100']:.2%}, MRR@100 {m['rr_100']:.4f}")
    print(f"Validacao: {resumo['validacao_top1_corrigidos']} acertos novos, "
          f"{resumo['validacao_top1_perdidos']} acertos perdidos.")
    print(f"Modelo e resultados: {destino}")
