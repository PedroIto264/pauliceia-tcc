"""Mede a resposta HTTP do portal e confere seus pontos com o backup original."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import platform
import statistics
import sys
from tempfile import TemporaryDirectory
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
import uuid

from iniciar import BACKUP, HASH_BACKUP, PASTA
from preparar_historico import sha
from preparar_validacao_portal import PASTA_DADOS, chave
from site_local import PORTAL
from testar_modelo import MODELO_ESCOLHIDO


def conferir_protocolo():
    caminho = PASTA_DADOS / "protocolo.json"
    manifesto = json.loads((PASTA_DADOS / "manifesto.json").read_text(encoding="utf8"))
    if sha(caminho) != manifesto["protocolo_sha256"]:
        raise ValueError("Protocolo alterado após a preparação.")
    p = json.loads(caminho.read_text(encoding="utf8"))
    comparacao = Path(p["comparacao"])
    for caminho, esperado in ((BACKUP, HASH_BACKUP),
                              (MODELO_ESCOLHIDO / "modelo.joblib", p["modelo_sha256"]),
                              (PASTA / "preparar_validacao_portal.py", p["gerador_sha256"]),
                              (comparacao / "resumo.json", p["comparacao_resumo_sha256"]),
                              (comparacao / "resultados.csv", p["comparacao_resultados_sha256"])):
        if sha(caminho) != esperado:
            raise ValueError(f"Arquivo de referência alterado: {caminho.name}")
    if p["backup_sha256"] != HASH_BACKUP:
        raise ValueError("Protocolo usa outro backup.")
    return p


def requisitar(caminho, parametros, timeout):
    url = PORTAL + "/api/geocoding/" + caminho + "?" + urlencode(parametros)
    inicio = time.perf_counter_ns()
    status, dados, modelo, erro = None, None, None, ""
    try:
        with urlopen(url, timeout=timeout) as resposta:
            status = resposta.status
            modelo = resposta.headers.get("X-Pauliceia-Modelo")
            dados = json.load(resposta)
    except HTTPError as e:
        status, erro = e.code, f"HTTP {e.code}"
    except (OSError, URLError, ValueError) as e:
        erro = f"{type(e).__name__}: {e}"
    decorrido = (time.perf_counter_ns() - inicio) / 1e6
    return {"http_status": status, "ms": decorrido, "dados": dados,
            "modelo": modelo, "erro_transporte": erro}


def conferir_candidatos(resposta, esperados, modelo):
    if resposta["http_status"] != 200 or resposta["erro_transporte"]:
        return "erro_http"
    if resposta["modelo"] != modelo:
        return "modelo_divergente"
    if resposta["dados"] != esperados:
        return "sugestoes_divergentes_do_ranking_offline"
    return "ok"


def coordenadas_iguais(obtidas, esperadas, tolerancia):
    if not isinstance(obtidas, list) or len(obtidas) != len(esperadas):
        return False
    for p in obtidas:
        if (not isinstance(p, list) or len(p) != 2 or
                any(type(x) not in (float, int) or not math.isfinite(x) for x in p)):
            return False
    if len({tuple(p) for p in obtidas}) != len(obtidas):
        return False
    # Um pareamento um-a-um evita que um ponto repetido cubra dois esperados.
    restantes = [tuple(p) for p in esperadas]
    for ponto in obtidas:
        i = next((i for i, p in enumerate(restantes)
                  if all(abs(x - y) <= tolerancia for x, y in zip(ponto, p))), None)
        if i is None:
            return False
        restantes.pop(i)
    return not restantes


def medir_busca(caso, protocolo, fase, repeticao):
    r = requisitar("candidatos", {"nome": caso["consulta"]}, protocolo["timeout_segundos"])
    motivo = conferir_candidatos(r, caso["esperados"], protocolo["modelo_sha256"])
    return {"fase": fase, "repeticao": repeticao, "id_consulta": caso["id_consulta"],
            "particao": caso["particao"], "tipo": caso["tipo"], "consulta": caso["consulta"],
            "ok": motivo == "ok", "motivo": motivo, **r}


def medir_ponto(caso, protocolo):
    r = requisitar(f"candidatos/{caso['id_rua']}/pontos", {"numero": caso["numero"], "ano": caso["ano"]},
                   protocolo["timeout_segundos"])
    motivo = "ok"
    if r["http_status"] != 200 or r["erro_transporte"]:
        motivo = "erro_http"
    elif not coordenadas_iguais(r["dados"], caso["coordenadas"], protocolo["tolerancia_coordenadas_graus"]):
        motivo = "coordenadas_divergentes_do_backup"
    return {**caso, "ok": motivo == "ok", "motivo": motivo, **r}


def medir_fluxo(caso, protocolo, repeticao):
    inicio = time.perf_counter_ns()
    busca = medir_busca(caso, protocolo, "fluxo", repeticao)
    ponto = None
    motivo = busca["motivo"]
    if busca["ok"]:
        if caso["id_rua"] not in {r["id"] for r in busca["dados"]}:
            motivo = "rua_esperada_ausente_das_sugestoes"
        else:
            ponto = medir_ponto(caso, protocolo)
            motivo = ponto["motivo"]
    return {"id_consulta": caso["id_consulta"], "consulta": caso["consulta"],
            "id_rua": caso["id_rua"], "numero": caso["numero"], "ano": caso["ano"],
            "repeticao": repeticao, "ok": motivo == "ok", "motivo": motivo,
            "ms": (time.perf_counter_ns() - inicio) / 1e6,
            "busca_ms": busca["ms"], "ponto_ms": ponto["ms"] if ponto else None,
            "busca": busca, "ponto": ponto}


def estatisticas(valores):
    if not valores:
        return {"n": 0}
    ordenados = sorted(valores)
    posicao = (len(ordenados) - 1) * .95
    baixo, alto = math.floor(posicao), math.ceil(posicao)
    p95 = ordenados[baixo] + (ordenados[alto] - ordenados[baixo]) * (posicao - baixo)
    return {"n": len(valores), "media_ms": statistics.mean(valores),
            "mediana_ms": statistics.median(valores), "p95_ms": p95,
            "min_ms": min(valores), "max_ms": max(valores)}


def resumir(linhas):
    return {"tentativas": len(linhas), "corretas": sum(r["ok"] for r in linhas),
            "falhas": dict(Counter(r["motivo"] for r in linhas if not r["ok"])),
            "tempo_todas_tentativas": estatisticas([r["ms"] for r in linhas]),
            "tempo_respostas_corretas": estatisticas([r["ms"] for r in linhas if r["ok"]])}


def relatorio(resumo):
    linhas = ["# Validação HTTP e espacial do portal", "",
              f"Execução completa: **{resumo['completa']}**. Motivo de interrupção: {resumo['interrupcao'] or 'nenhum'}.", "",
              "| Etapa | Tentativas | Corretas | Mediana (ms) | P95 (ms) |",
              "| --- | ---: | ---: | ---: | ---: |"]
    for chave in ("aquecimento", "busca", "pontos", "fluxos"):
        r = resumo[chave]
        t = r["tempo_respostas_corretas"]
        linhas.append(f"| {chave} | {r['tentativas']} | {r['corretas']} | "
                      f"{t.get('mediana_ms', '—')} | {t.get('p95_ms', '—')} |")
    linhas += ["", "A tabela de tempo considera respostas conferidas e corretas. Falhas e tempos de todas",
               "as tentativas estão no JSON. Aquecimento é separado das três rodadas medidas.", "",
               "## Escopo", "",
               "O tempo de busca inclui cliente HTTP local, proxy do portal, API Node, Elasticsearch,",
               "similaridades e Random Forest até a leitura do JSON. Não mede desenho do mapa,",
               "interação humana ou atraso de digitação. São requisições sequenciais com nova conexão.",
               "O fluxo soma busca e consulta dos pontos, com escolha explícita do ID de referência.",
               "Não é teste de carga, concorrência ou tempo de inicialização dos serviços.", "",
               "A referência espacial foi lida do backup original, independentemente do endpoint.",
               "A concordância confirma a entrega dos dados cadastrados, não sua exatidão histórica",
               "no terreno. A convenção de fim em 2000 não comprova validade histórica até esse ano.",
               "Não foi avaliada a interpolação da rota legada.", "",
               f"Modelo SHA-256: `{resumo['modelo_sha256']}`.", ""]
    return "\n".join(linhas)


def executar(protocolo):
    # Uma conferência inicial evita centenas de timeouts quando o portal está parado.
    preflight = medir_busca(protocolo["consultas"][0], protocolo, "preflight", 0)
    if not preflight["ok"]:
        raise RuntimeError(f"Portal indisponível ou incompatível ({preflight['motivo']}). "
                           "Inicie Docker Desktop e execute python site_local.py antes desta validação.")
    inicio = datetime.now(timezone.utc).isoformat()
    buscas, pontos, fluxos = [], [], []
    interrupcao, consecutivas = "", 0

    def registrar(destino, linha):
        nonlocal consecutivas
        destino.append(linha)
        consecutivas = 0 if linha["ok"] else consecutivas + 1
        if consecutivas >= 5:
            raise RuntimeError("Cinco verificações consecutivas falharam; coleta parcial preservada.")

    try:
        for repeticao in range(protocolo["repeticoes_medidas"] + 1):
            fase = "aquecimento" if repeticao == 0 else "medicao"
            casos = sorted(protocolo["consultas"], key=lambda c: chave((repeticao, c["particao"], c["id_consulta"])))
            for i, caso in enumerate(casos, 1):
                registrar(buscas, medir_busca(caso, protocolo, fase, repeticao))
                if i % 25 == 0 or i == len(casos):
                    print(f"{fase} {repeticao}: {i}/{len(casos)} consultas.", flush=True)
        for i, caso in enumerate(protocolo["espaciais"], 1):
            registrar(pontos, medir_ponto(caso, protocolo))
            if i % 25 == 0 or i == len(protocolo["espaciais"]):
                print(f"Controles espaciais: {i}/{len(protocolo['espaciais'])}.", flush=True)
        for repeticao in range(1, protocolo["repeticoes_medidas"] + 1):
            for caso in sorted(protocolo["fluxos"], key=lambda c: chave((repeticao, c["id_consulta"]))):
                registrar(fluxos, medir_fluxo(caso, protocolo, repeticao))
            print(f"Fluxos completos: rodada {repeticao}/{protocolo['repeticoes_medidas']}.", flush=True)
    except (RuntimeError, KeyboardInterrupt) as e:
        interrupcao = str(e) or "Interrompido pelo usuário."
    medidas = [r for r in buscas if r["fase"] == "medicao"]
    estratos = defaultdict(list)
    for r in medidas:
        estratos[(r["particao"], r["tipo"])].append(r)
    resumo = {"inicio_utc": inicio, "fim_utc": datetime.now(timezone.utc).isoformat(),
              "completa": not bool(interrupcao), "interrupcao": interrupcao,
              "modelo_sha256": protocolo["modelo_sha256"], "backup_sha256": HASH_BACKUP,
              "protocolo_sha256": sha(PASTA_DADOS / "protocolo.json"),
              "ambiente_cliente": {"sistema": platform.platform(), "python": platform.python_version(),
                                   "cpus_logicas": os.cpu_count(), "portal": PORTAL},
              "aquecimento": resumir([r for r in buscas if r["fase"] == "aquecimento"]),
              "busca": resumir(medidas), "pontos": resumir(pontos), "fluxos": resumir(fluxos),
              "busca_por_grupo": [dict(particao=p, tipo=t, **resumir(rows)) for (p, t), rows in sorted(estratos.items())],
              "pontos_por_tipo": {t: resumir([r for r in pontos if r["tipo"] == t]) for t in sorted({r['tipo'] for r in pontos})},
              "previsto": {"consultas": len(protocolo["consultas"]), "repeticoes": protocolo["repeticoes_medidas"],
                           "pontos": len(protocolo["espaciais"]), "fluxos": len(protocolo["fluxos"])},
              "limites": protocolo["limites"]}
    raiz = PASTA / ".local/validacoes_portal"
    raiz.mkdir(parents=True, exist_ok=True)
    destino = raiz / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    with TemporaryDirectory(prefix="em-andamento-", dir=raiz) as temporario:
        trabalho = Path(temporario)
        for nome, dados in (("buscas.json", buscas), ("pontos.json", pontos), ("fluxos.json", fluxos),
                            ("preflight.json", preflight), ("protocolo.json", protocolo)):
            (trabalho / nome).write_text(json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        for nome in ("validar_portal.py", "preparar_validacao_portal.py"):
            (trabalho / nome).write_bytes((PASTA / nome).read_bytes())
        (trabalho / "relatorio.md").write_text(relatorio(resumo), encoding="utf8")
        resumo["arquivos_sha256"] = {p.name: sha(p) for p in sorted(trabalho.iterdir())}
        (trabalho / "resumo.json").write_text(json.dumps(resumo, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
        conferir_protocolo()
        trabalho.rename(destino)
    for nome in ("busca", "pontos", "fluxos"):
        r = resumo[nome]
        t = r["tempo_respostas_corretas"]
        print(f"{nome}: {r['corretas']}/{r['tentativas']} verificacoes corretas.")
        if t["n"]:
            print(f"  Mediana {t['mediana_ms']:.2f} ms; P95 {t['p95_ms']:.2f} ms; media {t['media_ms']:.2f} ms.")
    print(f"Validacao salva em: {destino}")
    if interrupcao or any(not r["ok"] for r in buscas + pontos + fluxos):
        raise RuntimeError("Há falhas ou coleta incompleta. Consulte o relatório salvo antes de interpretar os tempos.")
    return destino


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verificar", action="store_true", help="Confere os arquivos sem acessar o portal.")
    args = parser.parse_args()
    try:
        protocolo = conferir_protocolo()
        if args.verificar:
            print(f"Protocolo OK: {len(protocolo['consultas'])} consultas, {len(protocolo['espaciais'])} controles espaciais, {len(protocolo['fluxos'])} fluxos.")
            print("Nenhuma medicao HTTP foi executada.")
        else:
            executar(protocolo)
    except (OSError, ValueError, RuntimeError) as e:
        sys.exit(f"Validacao interrompida: {e}")
