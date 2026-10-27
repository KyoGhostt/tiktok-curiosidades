"""Estoque de vídeos. O manifesto (fila.json) fica no branch `estado`; os vídeos ficam no branch `media`
(links públicos e diretos, que o Buffer exige). O Buffer grátis guarda no máximo 10 posts agendados, então
o estoque espera aqui e vai sendo agendado conforme abre vaga, sempre na ordem das partes.
Comandos: add <pasta> | estoque | encher | limpar | pausar | retomar"""
import json, os, shutil, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
import buffer_post as bp
import schedule

ESTADO = Path(os.environ.get("ESTADO_DIR", "/tmp/estado"))
MEDIA = Path(os.environ.get("MEDIA_DIR", "/tmp/media"))
REPO = os.environ.get("GITHUB_REPOSITORY", "KyoGhostt/tiktok-curiosidades")
RAW = f"https://raw.githubusercontent.com/{REPO}/media"
LIMITE = int(os.environ.get("LIMITE_BUFFER", "9"))   # o plano grátis aceita 10; 1 fica de folga
FILA = ESTADO / "fila.json"

Q_POSTS = """query($o:OrganizationId!,$s:DateTime!){posts(first:100,input:{organizationId:$o,
  filter:{dueAt:{start:$s}},sort:[{field:dueAt,direction:asc}]}){edges{node{id status dueAt}}}}"""


def load():
    return json.loads(FILA.read_text()) if FILA.exists() else {"stories": []}


def save(f):
    ESTADO.mkdir(parents=True, exist_ok=True)
    FILA.write_text(json.dumps(f, ensure_ascii=False, indent=1))


def partes(f):
    return [(s, p) for s in f["stories"] for p in s["partes"]]


def estoque(f):
    """Partes ainda não postadas (esperando ou já agendadas)."""
    return sum(1 for _, p in partes(f) if p["status"] in ("pendente", "agendado"))


def tg(msg):
    try:
        import telegram
        if telegram.configured():
            telegram.send_message(msg)
    except Exception as e:
        print("aviso telegram:", e)


def add(d):
    d = Path(d)
    info = json.loads((d / "info.json").read_text())
    dest = MEDIA / info["id"]
    dest.mkdir(parents=True, exist_ok=True)
    for p in info["partes"]:
        shutil.copy(d / p["arquivo"], dest / p["arquivo"])
    f = load()
    f["stories"].append({"id": info["id"], "titulo": info["titulo"], "n": info["n"], "origem": info["origem"],
                         "partes": [{"parte": p["parte"], "arquivo": p["arquivo"], "titulo": p["titulo"],
                                     "legenda": p["legenda"], "duracao_s": p["duracao_s"], "status": "pendente",
                                     "buffer_id": None, "due": None} for p in info["partes"]]})
    save(f)
    print(f"fila: +{info['titulo']} ({info['n']} partes); estoque={estoque(f)}")
    tg(f"📚 Nova história no estoque: {info['titulo']} ({info['n']} partes)")


def buffer_posts():
    org = bp.gql(bp.Q_ORG)["account"]["organizations"][0]["id"]
    ini = (datetime.now(timezone.utc) - timedelta(days=10)).strftime("%Y-%m-%dT%H:%M:%SZ")
    edges = bp.gql(Q_POSTS, {"o": org, "s": ini})["posts"]["edges"]
    return org, {e["node"]["id"]: e["node"] for e in edges}


def sync(f, posts):
    """Atualiza o status das partes agendadas conforme o Buffer (postado, erro, apagado)."""
    for _, p in partes(f):
        if p["status"] != "agendado" or not p["buffer_id"]:
            continue
        b = posts.get(p["buffer_id"])
        if b is None:
            p["status"] = "removido"      # apagado no Buffer: não reagenda sozinho
        elif b["status"] == "sent":
            p["status"] = "postado"
        elif b["status"] == "error":
            p["status"] = "erro"


def encher():
    if not bp.key():
        print("sem BUFFER_API_KEY"); return
    f = load()
    if f.get("pausado"):
        print("fila pausada: não agenda (use 'retomar')"); return
    org, posts = buffer_posts()
    sync(f, posts)
    ativos = [b for b in posts.values() if b["status"] in ("scheduled", "sending")]
    agora = datetime.now(timezone.utc)
    ultimo = max([datetime.fromisoformat(b["dueAt"].replace("Z", "+00:00")) for b in ativos if b.get("dueAt")] + [agora])
    ch = bp.tiktok_channel()
    novos = []
    pend = [(s, p) for s, p in partes(f) if p["status"] == "pendente"]
    if pend and len(ativos) < LIMITE:
        slots = schedule.slots_after(max(ultimo, agora + timedelta(hours=1)), min(LIMITE - len(ativos), len(pend)))
        for (s, p), dt in zip(pend, slots):
            url = f"{RAW}/{s['id']}/{p['arquivo']}"
            r = bp.gql(bp.M_POST, {"i": {
                "channelId": ch, "schedulingType": "automatic", "mode": "customScheduled",
                "dueAt": dt.isoformat(), "text": p["legenda"], "aiAssisted": True,
                "assets": [{"video": {"url": url, "metadata": {"thumbnailOffset": 1500}}}],
                "metadata": {"tiktok": {"isAiGenerated": True, "title": p["titulo"][:90]}}}})["createPost"]
            if r["__typename"] != "PostActionSuccess":
                msg = f"Buffer recusou '{p['titulo']}': {r.get('message')}"
                print(msg); tg("⚠️ " + msg); break
            p.update(status="agendado", buffer_id=r["post"]["id"], due=dt.isoformat())
            novos.append((p, dt))
            print(f"agendado: {p['titulo']} em {schedule.label(dt)}", flush=True)
    save(f)
    if novos:
        tg("✅ Agendado no TikTok:\n" + "\n".join(f"• {p['titulo']}: {schedule.label(dt)}" for p, dt in novos))
    print(f"buffer ativos={len(ativos)} novos={len(novos)} estoque={estoque(f)}")


def limpar():
    """Apaga do branch media as histórias totalmente postadas (ou removidas) há mais de 1 dia."""
    f = load()
    manter = []
    for s in f["stories"]:
        fim = all(p["status"] in ("postado", "erro", "removido") for p in s["partes"])
        if fim:
            shutil.rmtree(MEDIA / s["id"], ignore_errors=True)
        else:
            manter.append(s)
    f["stories"] = manter
    save(f)
    ids = {s["id"] for s in manter}
    if MEDIA.exists():
        for d in MEDIA.iterdir():
            if d.is_dir() and d.name != ".git" and d.name not in ids:
                shutil.rmtree(d, ignore_errors=True)


def pausa(valor):
    f = load(); f["pausado"] = valor; save(f)
    print("pausado =", valor)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "add": add(sys.argv[2])
    elif cmd == "estoque": print(estoque(load()))
    elif cmd == "encher": encher()
    elif cmd == "limpar": limpar()
    elif cmd == "pausar": pausa(True)
    elif cmd == "retomar": pausa(False)
    else: sys.exit("uso: fila.py add <pasta> | estoque | encher | limpar")
