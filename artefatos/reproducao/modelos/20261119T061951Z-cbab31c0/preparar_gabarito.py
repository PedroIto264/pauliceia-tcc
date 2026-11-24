"""Gera consultas reproduzíveis e partições por grupo de nomes de logradouro."""

from collections import Counter, defaultdict
import csv
import hashlib
import io
import json
import re

from extrair_logradouros import normalizar
from iniciar import HASH_BACKUP, PASTA
from piloto import documentos, GABARITO


DESTINO = PASTA / "dados"
SEMENTE = "pauliceia-tcc-v1"
ABREVIACOES = {
    "rua": "r.", "avenida": "av.", "travessa": "tv.", "praca": "pc.",
    "alameda": "al.", "largo": "lg.", "ladeira": "ld.", "estrada": "est.",
}
IGNORAR = set(ABREVIACOES) | {"de", "da", "do", "dos", "das", "e", "par", "impar",
                            "becco", "villa", "viaduto", "viadcuto", "r", "av"}
CAMPOS = ["id_consulta", "grupo", "particao", "nome_referencia", "ids_relevantes",
          "tipo", "origem", "consulta"]


def hash_texto(texto):
    return hashlib.sha256(texto.encode("utf-8")).hexdigest()


def grupo_nome(nome):
    """Agrupa diferenças de acento, caixa, ordem e os lados par/ímpar."""
    palavras = re.findall(r"\w+", normalizar(nome))
    if palavras and palavras[-1] in {"par", "impar"}:
        palavras.pop()
    return " ".join(sorted(palavras))


def posicao_opcao(nome, tipo, opcoes):
    return opcoes[int(hash_texto(SEMENTE + nome + tipo), 16) % len(opcoes)]


def variantes(nome):
    yield "original", "cadastro", nome
    base = normalizar(nome)
    if base != nome.casefold():
        yield "normalizacao", "sintetica", base
    primeira, _, resto = base.partition(" ")
    if primeira in ABREVIACOES and resto:
        yield "abreviacao", "sintetica", ABREVIACOES[primeira] + " " + resto
    palavras = list(re.finditer(r"[a-z]+", base))
    elegiveis = [m for m in palavras if len(m[0]) >= 4 and m[0] not in IGNORAR]
    indices = [i for m in elegiveis for i in range(m.start(), m.end())]
    trocas = [i for m in elegiveis for i in range(m.start(), m.end() - 1) if base[i] != base[i + 1]]
    if indices:
        i = posicao_opcao(base, "omissao", indices)
        yield "omissao", "sintetica", base[:i] + base[i + 1:]
        i = posicao_opcao(base, "substituicao", indices)
        letra = chr((ord(base[i]) - ord("a") + 1) % 26 + ord("a"))
        yield "substituicao", "sintetica", base[:i] + letra + base[i + 1:]
        i = posicao_opcao(base, "insercao", indices)
        yield "insercao", "sintetica", base[:i] + base[i] + base[i:]
    if trocas:
        i = posicao_opcao(base, "transposicao", trocas)
        yield "transposicao", "sintetica", base[:i] + base[i + 1] + base[i] + base[i + 2:]
    if len(elegiveis) >= 2:
        # Duas omissões em palavras diferentes.
        removidos = {m.start() + 1 for m in elegiveis[:2]}
        yield "duas_omissoes", "sintetica", "".join(c for i, c in enumerate(base) if i not in removidos)
    tokens = base.split()
    if len(tokens) > 2:
        yield "ordem", "sintetica", " ".join([tokens[0]] + list(reversed(tokens[1:])))


def montar(docs):
    nomes = defaultdict(list)
    for doc in docs:
        nomes[normalizar(doc["nome"])].append(doc)
    # A ausência de número/ano torna registros de mesmo nome igualmente relevantes.
    grupos = {nome: grupo_nome(nome) for nome in nomes}
    por_id = {str(d["id"]): normalizar(d["nome"]) for d in docs}
    with GABARITO.open(encoding="utf-8-sig", newline="") as arq:
        piloto = list(csv.DictReader(arq, delimiter=";"))
    desenvolvimento = {grupos[por_id[c["id_rua"]]] for c in piloto}
    ordem = sorted(set(grupos.values()) - desenvolvimento, key=lambda g: hash_texto(SEMENTE + g))
    fim_treino = len(ordem) * 60 // 100
    fim_validacao = len(ordem) * 80 // 100
    particoes = dict.fromkeys(desenvolvimento, "desenvolvimento")
    particoes.update(dict.fromkeys(ordem[:fim_treino], "treino"))
    particoes.update(dict.fromkeys(ordem[fim_treino:fim_validacao], "validacao"))
    particoes.update(dict.fromkeys(ordem[fim_validacao:], "teste"))

    propostas = []
    duplicadas = 0
    for nome, registros in sorted(nomes.items()):
        referencia = min(registros, key=lambda d: d["id"])["nome"]
        vistos = set()
        for tipo, origem, consulta in variantes(referencia):
            if consulta.casefold() in vistos:
                duplicadas += 1
                continue
            vistos.add(consulta.casefold())
            propostas.append({
                "id_consulta": hash_texto(nome + "\n" + tipo + "\n" + consulta)[:20],
                "grupo": hash_texto(grupos[nome])[:20],
                "particao": particoes[grupos[nome]],
                "nome_referencia": referencia,
                "ids_relevantes": "|".join(str(r["id"]) for r in sorted(registros, key=lambda d: d["id"])),
                "tipo": tipo, "origem": origem, "consulta": consulta,
            })

    destinos = defaultdict(set)
    for caso in propostas:
        destinos[normalizar(caso["consulta"])].add(normalizar(caso["nome_referencia"]))
    casos, exclusoes = [], []
    for caso in propostas:
        consulta = normalizar(caso["consulta"])
        alvo = normalizar(caso["nome_referencia"])
        motivo = ""
        if caso["origem"] == "sintetica":
            if consulta in nomes and consulta != alvo:
                motivo = "consulta_igual_a_outro_nome_cadastrado"
            elif len(destinos[consulta]) > 1:
                motivo = "consulta_gerada_para_mais_de_um_nome"
        if motivo:
            exclusoes.append(dict(caso, motivo=motivo))
        else:
            casos.append(caso)
    conferir(casos, docs)
    resumo = {
        "versao": 1, "semente": SEMENTE, "backup_sha256": HASH_BACKUP,
        "registros_indexados": len(docs), "nomes_normalizados": len(nomes),
        "grupos": len(particoes), "consultas": len(casos),
        "variantes_repetidas_omitidas": duplicadas,
        "variantes_ambiguas_excluidas": len(exclusoes),
        "por_particao": {
            p: {"grupos": sum(v == p for v in particoes.values()),
                "nomes": sum(particoes[g] == p for g in grupos.values()),
                "consultas": sum(c["particao"] == p for c in casos)}
            for p in ("desenvolvimento", "treino", "validacao", "teste")
        },
        "por_tipo": dict(sorted(Counter(c["tipo"] for c in casos).items())),
        "por_origem": dict(Counter(c["origem"] for c in casos)),
    }
    return casos, exclusoes, resumo


def conferir(casos, docs):
    ids_por_nome = defaultdict(set)
    for doc in docs:
        ids_por_nome[normalizar(doc["nome"])].add(str(doc["id"]))
    grupos = defaultdict(set)
    consultas = defaultdict(set)
    identidades = set()
    for caso in casos:
        if caso["id_consulta"] in identidades:
            raise ValueError("ID de consulta repetido.")
        identidades.add(caso["id_consulta"])
        relevantes = caso["ids_relevantes"].split("|")
        esperados = ids_por_nome[normalizar(caso["nome_referencia"])]
        if not esperados or set(relevantes) != esperados or len(relevantes) != len(esperados):
            raise ValueError("IDs relevantes diferentes dos registros do nome de referência.")
        if caso["grupo"] != hash_texto(grupo_nome(caso["nome_referencia"]))[:20]:
            raise ValueError("Grupo inconsistente com o nome de referência.")
        grupos[caso["grupo"]].add(caso["particao"])
        consultas[normalizar(caso["consulta"])].add(caso["grupo"])
    if any(len(v) > 1 for v in grupos.values()):
        raise ValueError("Um grupo aparece em mais de uma partição.")
    if any(len(v) > 1 for v in consultas.values()):
        raise ValueError("Consulta compartilhada por grupos diferentes.")


def bytes_csv(casos, campos):
    texto = io.StringIO(newline="")
    writer = csv.DictWriter(texto, fieldnames=campos, delimiter=";")
    writer.writeheader()
    writer.writerows(casos)
    return texto.getvalue().encode("utf-8-sig")


def main():
    casos, exclusoes, resumo = montar(documentos())
    arquivos = {
        "gabarito_ampliado.csv": bytes_csv(casos, CAMPOS),
        "consultas_ambiguas.csv": bytes_csv(exclusoes, CAMPOS + ["motivo"]),
    }
    resumo["gabarito_sha256"] = hashlib.sha256(arquivos["gabarito_ampliado.csv"]).hexdigest()
    arquivos["gabarito_manifesto.json"] = (json.dumps(resumo, ensure_ascii=False, indent=2) + "\n").encode("utf8")
    DESTINO.mkdir(exist_ok=True)
    for nome, dados in arquivos.items():
        destino = DESTINO / nome
        if destino.exists() and destino.read_bytes() != dados:
            raise ValueError(f"{nome} já existe com outro conteúdo. Use uma versão nova para outro experimento.")
    for nome, dados in arquivos.items():
        (DESTINO / nome).write_bytes(dados)
    print(json.dumps(resumo["por_particao"], ensure_ascii=False, indent=2))
    print(f"Gabarito conferido: {len(casos)} consultas, {len(exclusoes)} variantes ambiguas excluidas.")


if __name__ == "__main__":
    main()
