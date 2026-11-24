"""Prepara um estudo complementar exploratório, sem alterar o teste reservado."""

from collections import Counter, defaultdict
import csv
import hashlib
import json

from extrair_logradouros import normalizar
from iniciar import HASH_BACKUP, PASTA
from piloto import documentos


FONTES = PASTA / "dados" / "fontes_historicas.json"
DESTINO = PASTA / "dados" / "historico"

# Substituições de tokens explicitamente selecionadas ANTES da coleta de rankings.
# São simulações, não equivalências históricas comprovadas ou regras universais.
HISTORICAS = dict(par.split(":") for par in """
theresa:teresa theodoro:teodoro thomaz:tomas mathilde:matilde catharina:catarina
arthur:artur bartholomeu:bartolomeu balthazar:baltazar thome:tome
adolpho:adolfo rodolpho:rodolfo triumpho:triunfo amphitheatro:anfiteatro
ephigenia:ifigenia hygienopolis:higienopolis affonso:afonso afflictos:aflitos
becco:beco commercio:comercio officinas:oficinas bella:bela bello:belo
villa:vila florisbella:florisbela gabriella:gabriela domitilla:domitila
anna:ana anitta:anita motta:mota mello:melo penna:pena camillo:camilo
marcellina:marcelina bocayuva:bocaiuva ytu:itu piauhy:piaui itacolomy:itacolomi
parnahyba:parnaiba parahyba:paraiba pyrineus:pirineus guarany:guarani
guayanazes:guaianazes aymores:aimores tamanduatehy:tamanduatei
itaquy:itaqui itariry:itariri tatuhy:tatui tymbiras:timbiras ypiranga:ipiranga
humayta:humaita glycerio:glicerio nitcheroy:niteroi araguaya:araguaia
uruguayana:uruguaiana catumby:catumbi eloy:eloi javary:javari
itajahy:itajai jacarehy:jacarei jundiahy:jundiai pirahy:pirai
assumpcao:assuncao baptista:batista egydio:egidio jeronymo:jeronimo
""".split())

# Aproximações grafêmicas motivadas por som em tokens delimitados. Não são
# gravações de fala, erros observados, transcrição fonética nem dados de OCR real.
FONETICAS = dict(par.split(":") for par in """
souza:sousa sousa:souza chaves:xaves machado:maxado xavier:chavier
costa:kosta castro:kastro campos:kampos carmo:karmo carlos:karlos
rosa:roza jose:joze joao:joaum queiroz:queiros cezario:cesario
cecilia:sessilia oliveira:olivera teixeira:texeira ferreira:ferrera
""".split())


def sha(caminho):
    return hashlib.sha256(caminho.read_bytes()).hexdigest()


def ler_csv(caminho):
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        return list(csv.DictReader(arquivo, delimiter=";"))


def salvar_csv(caminho, linhas, campos):
    with caminho.open("w", encoding="utf-8-sig", newline="") as arquivo:
        tabela = csv.DictWriter(arquivo, fieldnames=campos, delimiter=";")
        tabela.writeheader()
        tabela.writerows(linhas)


def variantes(nome, regras, combinar=False):
    tokens = nome.split()
    aplicadas = [(i, regras[t]) for i, t in enumerate(tokens) if t in regras]
    for i, novo in aplicadas:
        copia = list(tokens)
        copia[i] = novo
        yield " ".join(copia), f"{tokens[i]} -> {novo}"
    if combinar and len(aplicadas) > 1:
        yield " ".join(regras.get(t, t) for t in tokens), "; ".join(
            f"{tokens[i]} -> {novo}" for i, novo in aplicadas)


def construir(docs, anteriores, fontes, piloto=()):
    por_id = {str(d["id"]): normalizar(d["nome"]) for d in docs}
    por_nome = defaultdict(list)
    for ident, nome in por_id.items():
        por_nome[nome].append(ident)
    originais = {normalizar(c["nome_referencia"]): c for c in anteriores if c["tipo"] == "original"}
    consultas_anteriores = defaultdict(set)
    for c in anteriores:
        consultas_anteriores[normalizar(c["consulta"])].add(c["particao"])
    for c in piloto:
        consultas_anteriores[normalizar(c["consulta"])].add("piloto")
    if set(por_nome) != set(originais):
        raise ValueError("Catálogo e partições originais divergem.")
    propostas = []

    def adicionar(nome, consulta, categoria, regra, fonte=""):
        base = originais[nome]
        propostas.append({
            "id_consulta": hashlib.sha256((nome + "\0" + normalizar(consulta)).encode()).hexdigest()[:20],
            "grupo": base["grupo"], "particao": "complementar",
            "nome_referencia": nome,
            "ids_relevantes": "|".join(sorted(por_nome[nome], key=int)),
            "tipo": categoria, "origem": "fonte_municipal" if fonte else "simulacao_controlada",
            "consulta": consulta, "regra": regra, "fonte_id": fonte,
            "particao_original": base["particao"],
            "consulta_preexistente": "|".join(sorted(consultas_anteriores[normalizar(consulta)])),
            "vinculo_relevancia": "inferencia_textual_sem_revisao_independente" if fonte else "nome_gerador",
        })

    # A forma documental tem prioridade sobre simulação idêntica; não duplicar
    # a mesma consulta/alvo para inflar a contagem ou misturar as categorias.
    for fonte in fontes["fontes"]:
        for caso in fonte["casos"]:
            adicionar(por_id[str(caso["id_rua"])], caso["consulta"],
                      "grafia_documentada", caso["regra"], fonte["id"])
    for nome in sorted(por_nome):
        for consulta, regra in variantes(nome, HISTORICAS, combinar=True):
            adicionar(nome, consulta, "historica_simulada", regra)
        for consulta, regra in variantes(nome, FONETICAS):
            adicionar(nome, consulta, "fonetica_simulada", regra)

    alvos_consulta = defaultdict(set)
    for c in propostas:
        alvos_consulta[normalizar(c["consulta"])].add(c["nome_referencia"])
    aceitas, excluidas, vistas = [], [], set()
    for c in propostas:
        consulta, nome = normalizar(c["consulta"]), c["nome_referencia"]
        motivo = ""
        if consulta == nome:
            motivo = "sem_alteracao_apos_normalizar"
        elif consulta in por_nome:
            motivo = "consulta_coincide_com_outro_nome_do_catalogo"
        elif len(alvos_consulta[consulta]) > 1:
            motivo = "consulta_gerada_para_alvos_diferentes"
        elif (consulta, nome) in vistas:
            motivo = "consulta_alvo_duplicados_prioridade_documentada"
        if motivo:
            excluidas.append(dict(c, motivo=motivo))
        else:
            vistas.add((consulta, nome))
            aceitas.append(c)
    if not aceitas or len({c["id_consulta"] for c in aceitas}) != len(aceitas):
        raise ValueError("Gabarito vazio ou IDs duplicados.")
    return aceitas, excluidas


def preparar():
    anterior = PASTA / "dados" / "gabarito_ampliado.csv"
    meta = json.loads((anterior.parent / "gabarito_manifesto.json").read_text(encoding="utf8"))
    if sha(anterior) != meta["gabarito_sha256"]:
        raise ValueError("O gabarito original foi alterado.")
    fontes = json.loads(FONTES.read_text(encoding="utf8"))
    piloto = PASTA / "dados" / "gabarito_piloto.csv"
    casos, excluidas = construir(documentos(), ler_csv(anterior), fontes, ler_csv(piloto))
    DESTINO.mkdir(parents=True, exist_ok=True)
    salvar_csv(DESTINO / "gabarito.csv", casos, list(casos[0]))
    salvar_csv(DESTINO / "exclusoes.csv", excluidas, [*casos[0], "motivo"])
    manifesto = {
        "versao": 1, "natureza": "estudo_complementar_exploratorio_pos_teste",
        "backup_sha256": HASH_BACKUP, "gabarito_original_sha256": sha(anterior),
        "gabarito_piloto_sha256": sha(piloto),
        "gabarito_sha256": sha(DESTINO / "gabarito.csv"),
        "exclusoes_sha256": sha(DESTINO / "exclusoes.csv"), "fontes_sha256": sha(FONTES),
        "gerador_sha256": sha(PASTA / "preparar_historico.py"),
        "consultas": len(casos), "nomes": len({c["nome_referencia"] for c in casos}),
        "por_categoria": dict(Counter(c["tipo"] for c in casos)),
        "por_particao_original": dict(Counter(c["particao_original"] for c in casos)),
        "consultas_preexistentes": sum(bool(c["consulta_preexistente"]) for c in casos),
        "exclusoes": dict(Counter(c["motivo"] for c in excluidas)),
        "regras_historicas_simuladas": HISTORICAS, "regras_foneticas_simuladas": FONETICAS,
        "limites": [fontes["escopo"],
                    "Seleção intencional feita após conhecer o teste anterior; não é novo teste cego.",
                    "Não reajustar o modelo ou escolher regras pelos acertos desta avaliação.",
                    "Resultados separados por categoria, exposição da rua e repetição da consulta.",
                    "Correspondência textual não comprova número, ano ou coordenadas."]
    }
    (DESTINO / "manifesto.json").write_text(json.dumps(manifesto, ensure_ascii=False, indent=2) + "\n", encoding="utf8")
    print(f"Gabarito complementar: {len(casos)} consultas, {manifesto['nomes']} nomes.")
    for categoria, total in manifesto["por_categoria"].items():
        print(f"  {categoria}: {total}")
    print(f"Consultas ja presentes no gabarito anterior: {manifesto['consultas_preexistentes']}.")
    print(f"Gabarito: {DESTINO / 'gabarito.csv'}")
    return manifesto


if __name__ == "__main__":
    preparar()
