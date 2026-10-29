"""Otimizador diário. Lê (1) o desempenho real dos posts no Buffer (views, tempo assistido) e (2) a pesquisa na web
(o que o Brasil procura: Google Trends, autocompletar do YouTube/Google), e então:
  - ajusta os horários dos PRÓXIMOS vídeos (testa 1h antes/depois e fica com o que dá mais views); posts já no Buffer não mudam de horário;
  - escolhe as hashtags de cada tema (as que mais deram views + exploração de novas) e reescreve os posts agendados.
Só decide com dados suficientes (MIN_AMOSTRAS) para não reagir a ruído. Uso: otimizar.py rodar | simular"""
import json, math, os, re, sys
from datetime import datetime, timedelta, timezone
import buffer_post as bp
import fila, fontes, otimo, schedule

MIN_AMOSTRAS = 3        # posts maduros por horário antes de comparar
MADURO_H = 36           # só conta posts com mais de 36 h (as métricas atualizam 1x por dia)
GANHO = 1.15            # o horário novo precisa render 15% mais views para trocar
HORAS_OK = range(8, 23)  # nunca de madrugada
Q = """query($o:OrganizationId!,$s:DateTime!){posts(first:100,input:{organizationId:$o,
  filter:{dueAt:{start:$s}},sort:[{field:dueAt,direction:asc}]}){edges{node{id status dueAt sentAt shareMode text
  metrics{type value}}}}}"""
M_EDIT = """mutation($i:EditPostInput!){editPost(input:$i){__typename
  ... on PostActionSuccess{post{id dueAt text}} ... on MutationError{message}}}"""


def dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def coletar_posts():
    org = bp.gql(bp.Q_ORG)["account"]["organizations"][0]["id"]
    ini = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    nodes = [e["node"] for e in bp.gql(Q, {"o": org, "s": ini})["posts"]["edges"]]
    for n in nodes:
        n["m"] = {m["type"]: m["value"] for m in (n.get("metrics") or [])}
    return nodes


def maduros(nodes):
    """Posts já enviados, agendados por nós (shareNow é teste manual), com tempo para acumular views."""
    lim = datetime.now(timezone.utc) - timedelta(hours=MADURO_H)
    return [n for n in nodes if n["status"] == "sent" and n.get("sentAt") and dt(n["sentAt"]) < lim
            and n.get("shareMode") == "customScheduled" and n.get("dueAt")]


def hora_brt(n):
    t = dt(n["dueAt"]).astimezone(schedule.TZ)
    return (t.hour + (1 if t.minute >= 30 else 0)) % 24


def stats_horas(ms):
    h = {}
    for n in ms:
        h.setdefault(hora_brt(n), []).append(n["m"].get("views", 0))
    return {k: {"n": len(v), "media": sum(v) / len(v)} for k, v in h.items()}


def stats_tags(ms):
    acc = {}
    for n in ms:
        for t in set(re.findall(r"#(\w+)", n["text"].lower())):
            acc.setdefault(t, []).append(n["m"].get("views", 0))
    return {t: {"n": len(v), "media": sum(v) / len(v)} for t, v in acc.items()}


# ---------- horários ----------
def vizinho_ok(h, slots, idx):
    outros = [s[0] for i, s in enumerate(slots) if i != idx]
    return h in HORAS_OK and all(abs(h - o) >= 3 for o in outros)


def otimizar_horarios(c, hs, log):
    """Um teste por vez: troca 1 horário pelo vizinho (±1h) até ter amostras; quem render mais fica."""
    slots = [list(s) for s in c["slots"]]
    t = c.get("teste")
    if t:
        i, base, novo = t["idx"], t["base"], t["novo"]
        a, b = hs.get(base, {"n": 0, "media": 0}), hs.get(novo, {"n": 0, "media": 0})
        if b["n"] >= MIN_AMOSTRAS and a["n"] >= MIN_AMOSTRAS:
            vence = novo if b["media"] > a["media"] * GANHO else base
            log.append(f"⏱ Teste {base}h x {novo}h: {a['media']:.0f} x {b['media']:.0f} views -> fica {vence}h")
            slots[i] = [vence, 0]; c["teste"] = None
            c.setdefault("historico", []).append({"quando": datetime.now(timezone.utc).isoformat()[:10], "base": base, "novo": novo,
                                                  "base_views": round(a["media"]), "novo_views": round(b["media"]), "vencedor": vence})
        else:
            log.append(f"⏱ Teste em andamento: {base}h ({a['n']} posts) x {novo}h ({b['n']} posts); preciso de {MIN_AMOSTRAS} de cada")
    else:
        for i, (h, _) in enumerate(slots):          # começa um teste no primeiro horário com dados suficientes
            if hs.get(h, {}).get("n", 0) < MIN_AMOSTRAS:
                continue
            for novo in (h + 1, h - 1):
                if hs.get(novo, {}).get("n", 0) < MIN_AMOSTRAS and vizinho_ok(novo, slots, i):
                    c["teste"] = {"idx": i, "base": h, "novo": novo}
                    slots[i] = [novo, 0]
                    log.append(f"⏱ Novo teste: o horário das {h}h passa a ser {novo}h para comparar")
                    break
            if c["teste"]:
                break
        if not c["teste"]:
            log.append("⏱ Horários mantidos (poucos dados ainda: preciso de %d posts maduros por horário)" % MIN_AMOSTRAS)
    c["slots"] = slots


# ---------- hashtags ----------
def pontuar(tag, ts, gm):
    s = ts.get(tag, {"n": 0, "media": gm})
    k = 3
    return (s["media"] * s["n"] + gm * k) / (s["n"] + k) + 0.5 * gm / math.sqrt(s["n"] + 1)


def otimizar_tags(c, ts, ms, log):
    c["tags"] = {t: v for t, v in ts.items()}
    if not c["escolhidas"]:     # primeira vez: mantém as hashtags padrão; só decide com dados novos depois
        c["escolhidas"] = {t: otimo.pool(t, c)[:3] for t in otimo.POOL}
        c["base_n"] = len(ms)
        log.append("🏷 Hashtags iniciais definidas por tema (as decisões com dados começam com 3 posts novos)")
        return False
    if len(ms) - c.get("base_n", 0) < 3 and c["escolhidas"]:
        log.append("🏷 Hashtags mantidas (menos de 3 posts novos desde a última decisão)")
        return False
    gm = sum(n["m"].get("views", 0) for n in ms) / len(ms) if ms else 0
    mudou = False
    for tema in otimo.POOL:
        pool = [t for t in otimo.pool(tema, c) if t not in otimo.FIXAS]
        rank = sorted(pool, key=lambda t: -pontuar(t, ts, gm))[:3]
        if rank != c["escolhidas"].get(tema):
            mudou = True
        c["escolhidas"][tema] = rank
    c["base_n"] = len(ms)
    log.append("🏷 Hashtags por tema: " + "; ".join(f"{t}: " + " ".join("#" + x for x in v) for t, v in c["escolhidas"].items()
                                                  if t in ("trabalho", "relacionamento")))
    return mudou


# ---------- pesquisa na web ----------
# só entram termos formados por palavras destas listas (evita nomes próprios, filmes, jogos e lixo do autocompletar)
PERMITIDAS = {"relacionamento", "abusivo", "toxico", "amoroso", "invejoso", "corporativa", "vizinho", "familia", "amiga",
              "amigo", "escola", "chefe", "trabalho", "casamento", "traicao", "sogra", "marido", "esposa", "vinganca", "aberto"}


def candidatas_da_pesquisa(p, c, log):
    """Hashtags que o público realmente digita: só entram termos que aparecem no YouTube E no Google."""
    achou = 0
    for tema, d in (p.get("buscas_por_tema") or {}).items():
        yt = {re.sub(r"^(a |o )?hist[óo]rias? (d[eoa]s? )?", "", x.lower()).strip() for x in d["youtube"]}
        gg = {re.sub(r"^(a |o )?hist[óo]rias? (d[eoa]s? )?", "", x.lower()).strip() for x in d["google"]}
        for termo in (yt & gg):
            tag = re.sub(r"[^a-z0-9]", "", __import__("unicodedata").normalize("NFKD", termo).encode("ascii", "ignore").decode())
            palavras = __import__("unicodedata").normalize("NFKD", termo).encode("ascii", "ignore").decode().split()
            if 6 <= len(tag) <= 24 and palavras and all(w in PERMITIDAS for w in palavras):
                lst = c["candidatas"].setdefault(tema, [])
                if tag not in lst and tag not in otimo.POOL.get(tema, []):
                    lst.append(tag); achou += 1
    if achou:
        log.append(f"🔎 {achou} hashtag(s) nova(s) que o público procura entraram no teste: " + ", ".join(f"{t}:{"/".join(v)}" for t, v in c["candidatas"].items() if v))


NARRATIVAS = {"novelas", "fofoca", "drama", "storytime", "historia", "historias", "tretas", "reddit", "casal", "famosos"}


def tendencias_tiktok(p, c, log):
    """Top do TikTok Brasil: só vira candidata a hashtag o que combina com histórias; o resto só entra no relatório."""
    tags = p.get("endless_tiktok_br") or []
    if not tags:
        return
    log.append("📈 TikTok Brasil na semana (Endless): " + ", ".join("#" + t for t in tags))
    for t in tags:
        if t in NARRATIVAS and t not in c["candidatas"].setdefault("drama", []) and t not in otimo.POOL["drama"]:
            c["candidatas"]["drama"].append(t)
            log.append(f"   #{t} combina com histórias: entrou no teste")


# ---------- aplicar nos posts agendados ----------
def tema_story(s):
    if s.get("tema") in otimo.POOL:
        return s["tema"]
    t = otimo.tema_por_titulo(s["titulo"])
    if t:
        return t
    m = re.findall(r"#(\w+)", s["partes"][0]["legenda"].lower())
    return otimo.tema_de(m)


def aplicar(c, f, nodes, simular, log):
    """Reescreve legendas (hashtags) dos posts agendados e dos pendentes do estoque."""
    ativos = {n["id"]: n for n in nodes if n["status"] == "scheduled"}
    agora = datetime.now(timezone.utc)
    futuros = []
    for s in f["stories"]:
        tema = tema_story(s)
        s["tema"] = tema
        for p in s["partes"]:
            nova = otimo.legenda(p["titulo"], p["parte"], s["n"], tema, c)
            if p["status"] == "pendente":
                p["legenda"] = nova
            elif p["status"] == "agendado" and p.get("buffer_id") in ativos:
                futuros.append((s, p, nova))
    # Posts que já estão no Buffer NÃO mudam de horário: só legenda/hashtags podem ser melhoradas.
    # Os horários otimizados valem apenas para os próximos vídeos (schedule.slots_after lê otimizacao.json).
    ch = ed = 0
    for s, p, nova in futuros:
        b = ativos[p["buffer_id"]]
        if dt(b["dueAt"]) < agora + timedelta(hours=1) or nova == b["text"]:
            continue
        ed += 1
        if simular:
            print(f"[simular] {p['titulo']}: nova legenda -> {nova[-60:]}"); continue
        r = bp.gql(M_EDIT, {"i": {"id": p["buffer_id"], "text": nova, "schedulingType": "automatic", "aiAssisted": True,
                                  "assets": [{"video": {"url": f"{fila.RAW}/{s['id']}/{p['arquivo']}", "metadata": {"thumbnailOffset": 1500}}}],
                                  "metadata": {"tiktok": {"isAiGenerated": True, "title": p["titulo"][:90]}}}})["editPost"]
        if r["__typename"] != "PostActionSuccess":
            log.append(f"⚠️ Buffer recusou editar '{p['titulo']}': {r.get('message')}"); continue
        p["legenda"] = nova; ch += 1
    log.append(f"✏️ Legendas/hashtags dos posts agendados atualizadas: {ch} de {len(futuros)} (horários deles não mudam)" + (" (simulação)" if simular else ""))


def main(simular):
    if not bp.key():
        print("sem BUFFER_API_KEY"); return
    c, f = otimo.load(), fila.load()
    log = []
    nodes = coletar_posts()
    ms = maduros(nodes)
    log.append(f"📊 {len(ms)} post(s) com métricas maduras; views médias: " +
               (f"{sum(n['m'].get('views', 0) for n in ms) / len(ms):.0f}" if ms else "—"))
    hs = stats_horas(ms)
    ts = stats_tags(ms)
    if hs:
        log.append("🕒 Views médias por horário: " + ", ".join(f"{h}h={v['media']:.0f} ({v['n']})" for h, v in sorted(hs.items())))
    p = fontes.coletar()
    ok = [k for k, v in p["_status"].items() if v == "ok"]
    log.append("🌐 Fontes lidas: " + ", ".join(ok) + (" | indisponíveis: " + ", ".join(k for k in p["_status"] if k not in ok) if len(ok) < len(p["_status"]) else ""))
    if p.get("google_trends"):
        log.append("🔥 Em alta no Brasil: " + ", ".join(x["termo"] for x in p["google_trends"][:6]))
    candidatas_da_pesquisa(p, c, log)
    tendencias_tiktok(p, c, log)
    otimizar_horarios(c, hs, log)
    otimizar_tags(c, ts, ms, log)
    c["atualizado"] = datetime.now(timezone.utc).isoformat()
    c["pesquisa"] = {"status": p["_status"], "trends": (p.get("google_trends") or [])[:15]}
    otimo_slots = c["slots"]
    log.append("📅 Horários atuais: " + ", ".join(f"{h:02d}h" for h, _ in sorted(otimo_slots)))
    if not simular:
        otimo.save(c)
    aplicar(c, f, nodes, simular, log)
    if not simular:
        fila.save(f)
    print("\n".join(log))
    if not simular:
        fila.tg("🧠 Otimização diária\n" + "\n".join(log))


if __name__ == "__main__":
    main(len(sys.argv) > 1 and sys.argv[1] == "simular")
