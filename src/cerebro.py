"""CÉREBRO por comunidade (BR / ES / US, sempre separados): le o desempenho real no Buffer e ajusta sozinho
  - a DURACAO dos videos (bandit: testa as opcoes de lang.py, favorece a que mais rende, explora vizinhas),
  - os TEMAS das historias (peso por tema),
  - e relata o que aprendeu. Os pesos ficam em ESTADO_DIR/cerebro.json e a geracao (story.py) le de la.
Recompensa de um post = ln(1+views) * (0.5 + retencao), com retencao = tempo medio assistido / duracao. So conta posts com 48 h+.
Limites de seguranca: duracao entre 1,1 e 4 min (>60 s p/ Creator Rewards), pelo menos 15% de exploracao por opcao, nada de apagar posts.
Uso: cerebro.py rodar | simular"""
import json, math, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import buffer_post as bp
import lang, otimo

ESTADO = Path(os.environ.get("ESTADO_DIR", "/tmp/estado"))
ARQ, HIST = ESTADO / "cerebro.json", ESTADO / "historico.json"
SEED = Path(__file__).resolve().parent.parent / "data" / "seed_historico.json"
MADURO_H, MIN_N, PISO, TAU = 48, 3, 0.15, 0.6
DUR_MIN, DUR_MAX = 1.1, 4.0
Q = """query($o:OrganizationId!,$s:DateTime!){posts(first:100,input:{organizationId:$o,
  filter:{dueAt:{start:$s}},sort:[{field:dueAt,direction:desc}]}){edges{node{id status dueAt sentAt shareMode text
  channelId metrics{type value}}}}}"""


def dt(s):
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def _j(p, d):
    return json.loads(p.read_text()) if p.exists() else d


def coletar():
    org = bp.gql(bp.Q_ORG)["account"]["organizations"][0]["id"]
    ini = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    ch = bp.tiktok_channel()
    out = []
    for e in bp.gql(Q, {"o": org, "s": ini})["posts"]["edges"]:
        n = e["node"]
        if n.get("channelId") == ch and n["status"] == "sent":
            n["m"] = {m["type"]: m["value"] for m in (n.get("metrics") or [])}
            out.append(n)
    return out


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


def recompensa(views, ret):
    return math.log1p(views) * (0.5 + ret)


def linhas(posts, dur):
    lim = datetime.now(timezone.utc) - timedelta(hours=MADURO_H)
    out = []
    for n in posts:
        if not n.get("sentAt") or dt(n["sentAt"]) > lim or n["id"] not in dur: continue
        m, d = n["m"], dur[n["id"]]
        v = m.get("views", 0)
        if v <= 20: continue                      # metrica ainda nao chegou
        ret = min(1.0, (m.get("averageTimeWatched") or 0) / d)
        pm = re.search(r"(?:Parte|Part) (\d+) (?:de|of) (\d+)", n["text"])
        out.append(dict(dur=d / 60, views=v, ret=ret, r=recompensa(v, ret), likes=m.get("reactions", 0), com=m.get("comments", 0),
                        tema=tema_de(n["text"]), parte=int(pm.group(1)) if pm else 1, n=int(pm.group(2)) if pm else 1))
    return out


def arm(d, opts):
    o = min(opts, key=lambda x: abs(x - d))
    return str(o) if abs(o - d) <= 0.3 else f"ref{round(d * 2) / 2}"   # duracao fora das opcoes (ex.: 5:00 antigo) vira referencia, nao braco


def agrupar(rows, chave):
    g = {}
    for r in rows: g.setdefault(chave(r), []).append(r)
    return {k: {"n": len(v), "views": round(sum(x["views"] for x in v) / len(v)), "ret": round(sum(x["ret"] for x in v) / len(v), 3),
                "r": round(sum(x["r"] for x in v) / len(v), 3)} for k, v in g.items()}


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


def rodar(simular=False):
    c = _j(ARQ, {})
    opts = [float(x) for x in c.get("opcoes", lang.L.get("alvo_opcoes") or [2.0])]
    posts = coletar()
    rows = linhas(posts, duracoes())
    log = []
    ds = agrupar(rows, lambda r: arm(r["dur"], opts)) if rows else {}
    opts = gerir_bracos(opts, ds, log)
    ts = agrupar(rows, lambda r: r["tema"])
    media = sum(r["views"] for r in rows) / len(rows) if rows else 0
    pt = {k: round(max(0.5, min(2.0, v["views"] / media)), 2) if v["n"] >= MIN_N and media else 1.0 for k, v in ts.items()}
    c.update(opcoes=opts, pesos_duracao=pesos(ds, opts), duracao=ds, tema=ts, pesos_tema=pt,
             parte=agrupar(rows, lambda r: "1" if r["parte"] == 1 else "2+"), amostra=len(rows),
             atualizado=datetime.now(timezone.utc).isoformat())
    best = max(ds.items(), key=lambda kv: kv[1]["r"]) if ds else None
    tema_top = max(ts.items(), key=lambda kv: kv[1]["views"]) if ts else None
    rel = [f"🧠 Cérebro {lang.L['nome']} ({lang.CODE.upper()}): {len(rows)} posts maduros analisados"]
    for o in opts:
        v = ds.get(str(o))
        rel.append(f"• {o} min: " + (f"{v['n']} posts, {v['views']} views, vê {v['ret']*100:.0f}% do vídeo" if v else "sem dados ainda") + f" → peso {c['pesos_duracao'][str(o)]*100:.0f}%")
    for k, v in sorted(ds.items()):
        if k.startswith("ref") and v["n"] >= MIN_N:
            rel.append(f"• referência {k[3:]} min (antigo): {v['n']} posts, {v['views']} views, vê {v['ret']*100:.0f}% do vídeo")
    if tema_top: rel.append(f"• tema que mais rende: {tema_top[0]} ({tema_top[1]['views']} views em média, {tema_top[1]['n']} posts)")
    rel += log
    c.setdefault("historico", []).append({"quando": c["atualizado"][:10], "pesos": c["pesos_duracao"], "n": len(rows)})
    c["historico"] = c["historico"][-60:]
    print("\n".join(rel), flush=True)
    if simular:
        print("(simulacao: nada gravado)"); return
    ESTADO.mkdir(parents=True, exist_ok=True)
    ARQ.write_text(json.dumps(c, ensure_ascii=False, indent=1))
    try:
        import telegram
        if telegram.configured() and (datetime.now().weekday() == 0 or log): telegram.send_message("\n".join(rel))   # relatorio semanal (2a) ou quando algo mudou
    except Exception as e:
        print("telegram:", str(e)[:100])


if __name__ == "__main__":
    rodar(simular=(sys.argv[1:] == ["simular"]))
