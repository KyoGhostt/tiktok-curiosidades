"""CÉREBRO por comunidade (BR / ES / US, sempre separados). Avalia por HISTORIA INTEIRA (todas as partes, 7+ dias depois da ultima) e
so MUDA os pesos 1x por semana (domingo) e aos poucos. Nos outros dias apenas coleta/avalia e grava relatorio.
  - DURACAO dos videos (bandit entre as opcoes de lang.py), TEMAS das historias (peso por tema).
Nota de uma parte = ln(1+views) * (0.5 + retencao) * (1 + min(eng,0.15)*2); eng = (curtidas + 2*comentarios + 3*compartilhamentos)/views.
Nota da historia = media das partes. (Favoritos/salvos o Buffer nao informa.) Passo maximo por semana: +-15 pontos de peso.
Saida em ANALISES_DIR (branch `analises`: cerebro.json = pesos, RELATORIO.md, historias.json, historico_semanal.json) - leitura por Claude.
Uso: cerebro.py rodar | aplicar | simular   (rodar = so aplica aos domingos; aplicar = forca; simular = nao grava)"""
import json, math, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import buffer_post as bp
import lang, otimo

ESTADO = Path(os.environ.get("ESTADO_DIR", "/tmp/estado"))
SAIDA = Path(os.environ.get("ANALISES_DIR") or ESTADO)
ARQ = SAIDA / "cerebro.json"
HIST = ESTADO / "historico.json"
SEED = Path(__file__).resolve().parent.parent / "data" / "seed_historico.json"
MADURO_D, MIN_N, PISO, TAU, PASSO = 7, 3, 0.15, 0.6, 0.15
DUR_MIN, DUR_MAX = 1.1, 4.0
YT_CANAL = "6aeeb178e29c69a1718e4a04"
Q = """query($o:OrganizationId!,$s:DateTime!){posts(first:100,input:{organizationId:$o,
  filter:{dueAt:{start:$s}},sort:[{field:dueAt,direction:desc}]}){edges{node{id status dueAt sentAt shareMode text
  channelId metrics{type value}}}}}"""


def dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _j(p, d):
    return json.loads(p.read_text()) if p.exists() else d


def coletar():
    """Posts enviados (30 dias) do TikTok desta comunidade e, se for a BR, tambem do YouTube."""
    org = bp.gql(bp.Q_ORG)["account"]["organizations"][0]["id"]
    ini = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ch = bp.tiktok_channel()
    tk, yt = [], []
    for e in bp.gql(Q, {"o": org, "s": ini})["posts"]["edges"]:
        n = e["node"]
        if n["status"] != "sent": continue
        n["m"] = {m["type"]: m["value"] for m in (n.get("metrics") or [])}
        if n.get("channelId") == ch: tk.append(n)
        elif n.get("channelId") == YT_CANAL and lang.CODE == "pt": yt.append(n)
    return tk, yt


def duracoes():
    """id do post no Buffer -> duracao (s). Fontes: historico.json (gravado por fila.limpar), fila.json atual e o seed inicial."""
    d = {}
    for s in _j(SEED, []):
        if s["lang"] == lang.CODE: d[s["id"]] = s["duracao_s"]
    for h in _j(HIST, []):
        if h.get("buffer_id") and h.get("duracao_s"): d[h["buffer_id"]] = h["duracao_s"]
    for s in _j(ESTADO / "fila.json", {"stories": []})["stories"]:
        for p in s["partes"]:
            if p.get("buffer_id") and p.get("duracao_s"): d[p["buffer_id"]] = p["duracao_s"]
    return d


def tema_de(texto):
    tit = re.split(r" \(Part|\s#|¿|\?", texto)[0]
    try:
        return otimo.classificar(tit, tit)
    except Exception:
        return "drama"


def eng(m, v):
    return (m.get("reactions", 0) + 2 * m.get("comments", 0) + 3 * m.get("shares", 0)) / max(v, 1)


def recompensa(views, ret, e=0.0):
    return math.log1p(views) * (0.5 + ret) * (1 + min(e, 0.15) * 2)


def titulo_de(texto):
    return re.split(r" \((?:Parte|Part) \d+|\s#", texto)[0].strip()


def historias(posts, dur):
    """Agrupa posts em historias. Retorna lista de dicts com partes, maturidade e nota."""
    g = {}
    for n in posts:
        d = dur.get(n["id"])
        if not d or not n.get("sentAt"): continue
        pm = re.search(r"(?:Parte|Part) (\d+) (?:de|of) (\d+)", n["text"])
        g.setdefault(titulo_de(n["text"]), []).append((n, d, int(pm.group(1)) if pm else 1, int(pm.group(2)) if pm else 1))
    agora = datetime.now(timezone.utc)
    out = []
    for tit, ps in g.items():
        ps.sort(key=lambda x: x[2])
        total = max(x[3] for x in ps)
        ultimo = max(dt(x[0]["sentAt"]) for x in ps)
        idade = (agora - ultimo).total_seconds() / 86400
        partes = []
        for n, d, i, _ in ps:
            m = n["m"]; v = m.get("views", 0)
            ret = min(1.0, (m.get("averageTimeWatched") or 0) / d)
            partes.append(dict(parte=i, id=n["id"], enviado=n["sentAt"][:16], dur_s=d, views=v, ret=round(ret, 3), likes=m.get("reactions", 0),
                               com=m.get("comments", 0), shares=m.get("shares", 0), eng=round(eng(m, v), 4), r=round(recompensa(v, ret, eng(m, v)), 3)))
        completa = len(partes) >= total and all(p["views"] > 20 for p in partes)
        maduro = completa and idade >= MADURO_D
        k = len(partes)
        out.append(dict(titulo=tit, n=total, enviadas=k, idade_dias=round(idade, 1), maduro=maduro,
                        status="avaliada" if maduro else ("amadurecendo" if completa else "partes pendentes"),
                        dur=sum(p["dur_s"] for p in partes) / k / 60, tema=tema_de(tit),
                        views=sum(p["views"] for p in partes), views_media=round(sum(p["views"] for p in partes) / k),
                        ret=round(sum(p["ret"] for p in partes) / k, 3), likes=sum(p["likes"] for p in partes),
                        com=sum(p["com"] for p in partes), shares=sum(p["shares"] for p in partes),
                        r=round(sum(p["r"] for p in partes) / k, 3), partes=partes))
    return sorted(out, key=lambda h: -h["idade_dias"])


def arm(d, opts):
    o = min(opts, key=lambda x: abs(x - d))
    return str(o) if abs(o - d) <= 0.3 else f"ref{round(d * 2) / 2}"   # duracao fora das opcoes (ex.: 5:00 antigo) vira referencia, nao braco


def agrupar(rows, chave):
    g = {}
    for r in rows: g.setdefault(chave(r), []).append(r)
    return {k: {"n": len(v), "views": round(sum(x["views_media"] for x in v) / len(v)), "ret": round(sum(x["ret"] for x in v) / len(v), 3),
                "r": round(sum(x["r"] for x in v) / len(v), 3), "likes": round(sum(x["likes"] for x in v) / len(v), 1),
                "com": round(sum(x["com"] for x in v) / len(v), 1), "shares": round(sum(x["shares"] for x in v) / len(v), 1)} for k, v in g.items()}


def pesos(stats, opts):
    ms = [stats[str(o)]["r"] for o in opts if stats.get(str(o), {}).get("n", 0) >= MIN_N]
    prior = max(ms) if ms else 5.0                # braco sem dados = otimista (explora)
    m = {o: (stats[str(o)]["r"] if stats.get(str(o), {}).get("n", 0) >= MIN_N else prior) for o in opts}
    mx = max(m.values())
    w = {o: math.exp((m[o] - mx) / TAU) for o in opts}
    t = sum(w.values()); w = {o: max(PISO, v / t) for o, v in w.items()}
    t = sum(w.values())
    return {str(o): round(v / t, 3) for o, v in w.items()}


def gerir_bracos(opts, stats, log):
    """Adiciona opcao vizinha quando a melhor esta na ponta; tira as claramente piores (com amostra)."""
    ok = {o: stats.get(str(o), {}) for o in opts}
    if all(v.get("n", 0) >= 5 for v in ok.values()):
        best = max(opts, key=lambda o: ok[o]["r"])
        novo = None
        if best == min(opts) and best - 0.5 >= DUR_MIN: novo = best - 0.5
        elif best == max(opts) and best + 0.5 <= DUR_MAX: novo = best + 0.5
        if novo and len(opts) < 5:
            opts.append(novo); log.append(f"➕ a melhor duracao ({best} min) esta na ponta: vou testar tambem {novo} min")
    for o in list(opts):
        v = ok.get(o)
        if v and v.get("n", 0) >= 8 and len(opts) > 2 and v["r"] < max(x.get("r", 0) for x in ok.values()) - 1.5:
            opts.remove(o); log.append(f"➖ {o} min rendeu bem menos: saiu do teste")
    return sorted(opts)


def passo(antigo, alvo, lo=PISO):
    """Muda no maximo PASSO por semana em direcao ao alvo; renormaliza (soma 1) mantendo o piso."""
    novo = {k: antigo.get(k, 1 / len(alvo)) + max(-PASSO, min(PASSO, alvo[k] - antigo.get(k, 1 / len(alvo)))) for k in alvo}
    novo = {k: max(lo, v) for k, v in novo.items()}
    t = sum(novo.values())
    return {k: round(v / t, 3) for k, v in novo.items()}


def yt_resumo(yt):
    if not yt: return None
    v = [n["m"].get("views", 0) for n in yt]
    return dict(n=len(yt), views_total=sum(v), views_media=round(sum(v) / len(v)), curtidas=sum(n["m"].get("reactions", 0) for n in yt),
                comentarios=sum(n["m"].get("comments", 0) for n in yt), compartilhamentos=sum(n["m"].get("shares", 0) for n in yt),
                posts=[dict(texto=n["text"][:70], enviado=(n.get("sentAt") or "")[:10], **{k: n["m"].get(k, 0) for k in ("views", "reactions", "comments", "shares", "averageTimeWatched")}) for n in yt])


def relatorio(c, hs, ds, ts, opts, antigos, log, aplicou, yt):
    L = [f"# Cérebro — {lang.L['nome']} ({lang.CODE.upper()})", "",
         f"Gerado em {c['atualizado']}. {'**PESOS ATUALIZADOS nesta execução** (domingo/aplicar).' if aplicou else 'Só coleta: os pesos NÃO mudaram hoje (mudam 1x por semana, no domingo).'}",
         f"Regra: avalia a história inteira (todas as partes, {MADURO_D}+ dias após a última). Passo máximo ±{int(PASSO*100)} pts/semana. Favoritos/salvos: o Buffer não informa.", "",
         "## Pesos de duração (vigentes)", "| duração | histórias avaliadas | views/parte | retenção | curtidas | coment. | compart. | nota | peso antes → agora |", "|---|---|---|---|---|---|---|---|---|"]
    for o in opts:
        v = ds.get(str(o), {})
        L.append(f"| {o} min | {v.get('n', 0)} | {v.get('views', '-')} | {v.get('ret', '-')} | {v.get('likes', '-')} | {v.get('com', '-')} | {v.get('shares', '-')} | {v.get('r', '-')} | "
                 f"{antigos.get(str(o), '-')} → {c['pesos_duracao'].get(str(o))} |")
    for k, v in sorted(ds.items()):
        if k.startswith("ref"): L.append(f"| {k[3:]} min (ref. antiga) | {v['n']} | {v['views']} | {v['ret']} | {v['likes']} | {v['com']} | {v['shares']} | {v['r']} | — |")
    L += ["", "## Temas (peso na escolha das histórias)", "| tema | histórias | views/parte | peso |", "|---|---|---|---|"]
    for k, v in sorted(ts.items(), key=lambda kv: -kv[1]["views"]): L.append(f"| {k} | {v['n']} | {v['views']} | {c['pesos_tema'].get(k, 1.0)} |")
    L += ["", "## Histórias", "| título | partes | idade | status | duração | tema | views | retenção | curtidas | coment. | compart. | nota |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for h in hs: L.append(f"| {h['titulo'][:50]} | {h['enviadas']}/{h['n']} | {h['idade_dias']}d | {h['status']} | {h['dur']:.1f} | {h['tema']} | {h['views']} | {h['ret']} | {h['likes']} | {h['com']} | {h['shares']} | {h['r']} |")
    if log: L += ["", "## Mudanças desta semana"] + [f"- {x}" for x in log]
    if yt: L += ["", "## YouTube Shorts (BR, canal separado)", f"{yt['n']} Shorts enviados, {yt['views_total']} views no total ({yt['views_media']} em média), {yt['curtidas']} curtidas, {yt['comentarios']} comentários, {yt['compartilhamentos']} compart."]
    return "\n".join(L) + "\n"


def rodar(modo="rodar"):
    simular = modo == "simular"
    aplicar = modo == "aplicar" or (modo == "rodar" and datetime.now(timezone.utc).weekday() == 6)
    c = _j(ARQ, {})
    if not c and (ESTADO / "cerebro.json").exists(): c = _j(ESTADO / "cerebro.json", {})   # migra pesos antigos
    opts = [float(x) for x in c.get("opcoes", lang.L.get("alvo_opcoes") or [2.0])]
    tk, yt = coletar()
    hs = historias(tk, duracoes())
    ok = [h for h in hs if h["maduro"]]
    log = []
    ds = agrupar(ok, lambda h: arm(h["dur"], opts)) if ok else {}
    ts = agrupar(ok, lambda h: h["tema"])
    antigos = dict(c.get("pesos_duracao") or {})
    ptema_ant = dict(c.get("pesos_tema") or {})
    if aplicar:
        opts = gerir_bracos(opts, ds, log)
        alvo = pesos(ds, opts)
        base = antigos or {str(o): round(1 / len(opts), 3) for o in opts}
        c["pesos_duracao"] = passo(base, alvo)
        media = sum(v["views"] * v["n"] for v in ts.values()) / max(1, sum(v["n"] for v in ts.values()))
        alvo_t = {k: max(0.5, min(2.0, v["views"] / media)) if v["n"] >= MIN_N and media else 1.0 for k, v in ts.items()}
        c["pesos_tema"] = {k: round(max(0.5, min(2.0, ptema_ant.get(k, 1.0) + max(-PASSO, min(PASSO, a - ptema_ant.get(k, 1.0))))), 2) for k, a in alvo_t.items()}
        for o in opts:
            if str(o) not in antigos: log.append(f"nova opção de duração {o} min entra com peso {c['pesos_duracao'][str(o)]}")
        for k, v in c["pesos_duracao"].items():
            if antigos.get(k) is not None and abs(v - antigos[k]) >= 0.01: log.append(f"duração {k} min: peso {antigos[k]} → {v}")
        c["ultima_atualizacao"] = datetime.now(timezone.utc).isoformat()
        c.setdefault("historico_pesos", []).append({"quando": c["ultima_atualizacao"][:10], "pesos": c["pesos_duracao"], "n_historias": len(ok)})
        c["historico_pesos"] = c["historico_pesos"][-60:]
    else:
        c.setdefault("pesos_duracao", {str(o): round(1 / len(opts), 3) for o in opts} if not antigos else antigos)
        c.setdefault("pesos_tema", {})
    c.update(opcoes=opts, duracao=ds, tema=ts, amostra_historias=len(ok), atualizado=datetime.now(timezone.utc).isoformat())
    for k in ("parte", "amostra", "historico"): c.pop(k, None)
    rel = relatorio(c, hs, ds, ts, opts, antigos, log, aplicar, yt_resumo(yt))
    print(rel[:1500], flush=True)
    if simular:
        print("(simulacao: nada gravado)"); return
    SAIDA.mkdir(parents=True, exist_ok=True)
    ARQ.write_text(json.dumps(c, ensure_ascii=False, indent=1))
    (SAIDA / "RELATORIO.md").write_text(rel)
    (SAIDA / "historias.json").write_text(json.dumps(hs, ensure_ascii=False, indent=1))
    if yt: (SAIDA / "youtube.json").write_text(json.dumps(yt_resumo(yt), ensure_ascii=False, indent=1))
    if aplicar:
        h = _j(SAIDA / "historico_semanal.json", [])
        h.append({"quando": c["atualizado"][:10], "pesos_duracao": c["pesos_duracao"], "pesos_tema": c["pesos_tema"], "n_historias": len(ok), "mudancas": log})
        (SAIDA / "historico_semanal.json").write_text(json.dumps(h[-104:], ensure_ascii=False, indent=1))
        try:
            import telegram
            if telegram.configured():
                resumo = [f"🧠 Cérebro semanal {lang.L['nome']} ({lang.CODE.upper()}): {len(ok)} histórias avaliadas"]
                resumo += [f"• {o} min: peso {c['pesos_duracao'][str(o)]*100:.0f}%" + (f" ({ds[str(o)]['n']} hist., {ds[str(o)]['views']} views/parte)" if str(o) in ds else " (sem dados)") for o in opts]
                telegram.send_message("\n".join(resumo + log))
        except Exception as e:
            print("telegram:", str(e)[:100])


if __name__ == "__main__":
    rodar(sys.argv[1] if len(sys.argv) > 1 else "rodar")
