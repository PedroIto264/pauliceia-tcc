"""Prepara controles espaciais do backup e uma amostra fixa para latência HTTP."""

from collections import Counter, defaultdict
from decimal import Decimal
import hashlib
import json
import math
import re
import struct

from iniciar import BACKUP, HASH_BACKUP, PASTA
from piloto import documentos
from preparar_historico import ler_csv, sha
from testar_modelo import MODELO_ESCOLHIDO


PASTA_DADOS = PASTA / "dados/validacao_portal"
COMPARACAO = PASTA / ".local/comparacoes_metricas/20261121T125929Z-28ccbb72"
SEMENTE = "pauliceia-validacao-portal-v1"


def chave(valor):
    return hashlib.sha256((SEMENTE + str(valor)).encode()).hexdigest()


def ponto_ewkb(hexadecimal):
    """Leitura independente de POINT 2D com SRID 4326, sem PostGIS/Shapely."""
    dados = bytes.fromhex(hexadecimal)
    if len(dados) != 25 or dados[0] not in (0, 1):
        raise ValueError("Geometria inesperada no backup.")
    ordem = "<" if dados[0] == 1 else ">"
    tipo, srid = struct.unpack(ordem + "II", dados[1:9])
    if tipo != 0x20000001 or srid != 4326:
        raise ValueError("Esperado POINT 2D em EPSG:4326.")
    x, y = struct.unpack(ordem + "dd", dados[9:])
    if not (math.isfinite(x) and math.isfinite(y) and -180 <= x <= 180 and -90 <= y <= 90):
        raise ValueError("Coordenadas inválidas no backup.")
    return (x, y)


def ler_pontos(conteudo):
    prefixo = "COPY public.places_pilot_area2 ("
    colunas, pontos, excluidos = None, [], Counter()
    for linha in conteudo.decode("utf8").splitlines():
        if colunas is None:
            if linha.startswith(prefixo):
                colunas = linha.removeprefix(prefixo).removesuffix(") FROM stdin;").split(", ")
            continue
        if linha == r"\.":
            return pontos, dict(excluidos)
        r = dict(zip(colunas, linha.split("\t"), strict=True))
        if r["geom"] == r"\N" or r["first_year"] == r"\N":
            excluidos["sem_geometria_ou_ano_inicial"] += 1
            continue
        # O endpoint compara number::float (float8). A forma decimal mais curta
        # preserva o mesmo float, sem arredondamento ad hoc dos números da fonte.
        numero = format(Decimal(str(float(r["number"]))).normalize(), "f")
        if not re.fullmatch(r"\d{1,9}(\.\d{1,6})?", numero):
            excluidos["numero_fora_do_formato_da_rota"] += 1
            continue
        inicio = int(r["first_year"])
        aberto = r["last_year"] in (r"\N", "0")
        fim = 2000 if aberto else int(r["last_year"])
        if not (0 <= inicio <= fim <= 9998):
            excluidos["intervalo_invalido"] += 1
            continue
        pontos.append({"id": int(r["id"]), "rua": int(r["id_street"]), "numero": numero,
                       "inicio": inicio, "fim": fim, "fim_aberto": aberto,
                       "xy": ponto_ewkb(r["geom"])})
    raise ValueError("Bloco de pontos incompleto.")


def referencia(pontos, rua, numero, ano):
    correspondencias = [p for p in pontos if p["rua"] == rua and Decimal(p["numero"]) == Decimal(numero)
                         and p["inicio"] <= ano <= p["fim"]]
    return sorted({p["xy"] for p in correspondencias}), sorted(p["id"] for p in correspondencias)


def casos_espaciais(pontos, catalogo):
    grupos = defaultdict(list)
    for p in pontos:
        if p["rua"] in catalogo:
            grupos[(p["rua"], p["numero"])].append(p)
    # Um ano de três dígitos no backup é mantido no oráculo, mas o endereço não
    # serve como âncora temporal de quatro dígitos. Não inferir a data correta.
    grupos = {g: rows for g, rows in grupos.items() if all(p["inicio"] >= 1001 for p in rows)}
    selecionados, ruas = [], set()
    for grupo in sorted(grupos, key=chave):
        if grupo[0] not in ruas:
            selecionados.append(grupo)
            ruas.add(grupo[0])
        if len(selecionados) == 30:
            break
    # Controles adicionais para múltiplos pontos e o limite convencional de 2000.
    for modo in ("multiplos", "fim_aberto", "numero_decimal"):
        adicionados = 0
        for grupo in sorted(grupos, key=chave):
            registros = grupos[grupo]
            if modo == "fim_aberto":
                atende = any(p["fim_aberto"] for p in registros)
            elif modo == "numero_decimal":
                atende = "." in grupo[1]
            else:
                atende = any(len(referencia(pontos, *grupo, p["inicio"])[0]) > 1 for p in registros)
            if atende:
                if grupo not in selecionados:
                    selecionados.append(grupo)
                adicionados += 1
                if adicionados == 5:
                    break
    casos, vistos = [], set()

    def adicionar(rua, numero, ano, tipo):
        if (rua, numero, ano) in vistos:
            return
        vistos.add((rua, numero, ano))
        xy, ids = referencia(pontos, rua, numero, ano)
        casos.append({"id_caso": chave((rua, numero, ano))[:20], "tipo": tipo,
                      "id_rua": rua, "nome": catalogo.get(rua, "ID inexistente"),
                      "numero": numero, "ano": ano, "coordenadas": xy, "ids_pontos": ids})

    for rua, numero in selecionados:
        registros = grupos[(rua, numero)]
        p = sorted(registros, key=lambda p: chave(p["id"]))[0]
        adicionar(rua, numero, p["inicio"], "inicio_intervalo")
        adicionar(rua, numero, (p["inicio"] + p["fim"]) // 2, "interior_intervalo")
        adicionar(rua, numero, p["fim"], "limite_2000" if p["fim_aberto"] else "fim_intervalo")
        adicionar(rua, numero, min(r["inicio"] for r in registros) - 1, "antes_de_todos_intervalos")
        adicionar(rua, numero, max(r["fim"] for r in registros) + 1, "apos_todos_intervalos")
        if any(r["fim_aberto"] for r in registros):
            adicionar(rua, numero, 2000, "limite_2000")
            adicionar(rua, numero, 2001, "apos_limite_2000")
        for r in registros:
            if len(referencia(pontos, rua, numero, r["inicio"])[0]) > 1:
                adicionar(rua, numero, r["inicio"], "multiplas_coordenadas")
                break
    for rua in sorted({g[0] for g in selecionados}):
        numero = str(int(max(Decimal(p["numero"]) for p in pontos if p["rua"] == rua)) + 1)
        adicionar(rua, numero, 1936, "numero_inexistente")
    adicionar(max(set(catalogo) | {p["rua"] for p in pontos}) + 1, "1", 1936, "rua_inexistente")
    return casos


def preparar():
    if sha(BACKUP) != HASH_BACKUP:
        raise ValueError("Backup alterado.")
    resumo = json.loads((COMPARACAO / "resumo.json").read_text(encoding="utf8"))
    if sha(COMPARACAO / "resultados.csv") != resumo["arquivos_sha256"]["resultados.csv"]:
        raise ValueError("Rankings de referência alterados.")
    if sha(MODELO_ESCOLHIDO / "modelo.joblib") != resumo["modelo_sha256"]:
        raise ValueError("Modelo diferente da comparação.")
    docs = {d["id"]: d["nome"] for d in documentos()}
    pontos, excluidos = ler_pontos(BACKUP.read_bytes())
    por_tipo = defaultdict(list)
    for r in ler_csv(COMPARACAO / "resultados.csv"):
        if r["metodo"] == "random_forest":
            por_tipo[(r["particao"], r["tipo"])].append(r)
    consultas = []
    for (particao, tipo), rows in sorted(por_tipo.items()):
        # Seleção por hash, independente de tempo de resposta ou acerto observado.
        for r in sorted(rows, key=lambda r: chave(r["id_consulta"]))[:10]:
            ids = [int(i) for i in r["ranking"].split("|")[:5]] if r["ranking"] else []
            consultas.append({"id_consulta": r["id_consulta"], "particao": particao, "tipo": tipo,
                              "consulta": r["consulta"], "ids_relevantes": r["ids_relevantes"],
                              "esperados": [{"id": i, "nome": docs[i]} for i in ids]})
    espaciais = casos_espaciais(pontos, docs)
    fluxos, ruas = [], set()
    for c in sorted(consultas, key=lambda c: chave(c["id_consulta"])):
        relevantes = set(map(int, c["ids_relevantes"].split("|")))
        alvos = [p for p in pontos if p["rua"] in relevantes and p["rua"] not in ruas and p["inicio"] >= 1001
                 and p["rua"] in {r["id"] for r in c["esperados"]}]
        if not alvos:
            continue
        p = min(alvos, key=lambda p: chave(p["id"]))
        xy, ids = referencia(pontos, p["rua"], p["numero"], p["inicio"])
        fluxos.append(dict(c, id_rua=p["rua"], numero=p["numero"], ano=p["inicio"],
                           coordenadas=xy, ids_pontos=ids))
        ruas.add(p["rua"])
        if len(fluxos) == 20:
            break
    protocolo = {
        "versao": 1, "semente": SEMENTE, "modelo_sha256": resumo["modelo_sha256"],
        "backup_sha256": HASH_BACKUP, "comparacao": str(COMPARACAO),
        "comparacao_resumo_sha256": sha(COMPARACAO / "resumo.json"),
        "comparacao_resultados_sha256": sha(COMPARACAO / "resultados.csv"),
        "gerador_sha256": sha(PASTA / "preparar_validacao_portal.py"),
        "repeticoes_medidas": 3, "aquecimentos_por_consulta": 1,
        "tolerancia_coordenadas_graus": 1e-9, "timeout_segundos": 15,
        "pontos_elegiveis": len(pontos), "pontos_excluidos": excluidos,
        "anos_iniciais_atipicos": [{"id_ponto": p["id"], "ano_inicial": p["inicio"]}
                                   for p in pontos if p["inicio"] < 1001],
        "consultas": consultas, "espaciais": espaciais, "fluxos": fluxos,
        "limites": ["Latência HTTP pelo proxy do portal; inclui Elasticsearch e RF, exclui desenho no navegador.",
                    "Requisições sequenciais com nova conexão, serviço aquecido; não é teste de carga.",
                    "Geometrias conferidas com o backup, não com levantamento de campo ou fonte histórica independente.",
                    "O fim ausente/zero é tratado como 2000 conforme contrato da API, não como evidência histórica.",
                    "Fluxo completo usa seleção explícita de um ID relevante presente nas sugestões, não necessariamente o primeiro.",
                    "O novo fluxo consulta pontos cadastrados; não avalia interpolação da API legada."]}
    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    arquivo = PASTA_DADOS / "protocolo.json"
    arquivo.write_text(json.dumps(protocolo, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    (PASTA_DADOS / "manifesto.json").write_text(json.dumps({"protocolo_sha256": sha(arquivo)}, indent=2) + "\n", encoding="utf8")
    print(f"Preparacao OK: {len(consultas)} consultas de latencia, {len(espaciais)} controles espaciais, {len(fluxos)} fluxos completos.")
    print(f"Espaciais: {sum(bool(c['coordenadas']) for c in espaciais)} com pontos; "
          f"{sum(not c['coordenadas'] for c in espaciais)} sem pontos; "
          f"{sum(len(c['coordenadas']) > 1 for c in espaciais)} com multiplas coordenadas.")
    return protocolo


if __name__ == "__main__":
    preparar()
