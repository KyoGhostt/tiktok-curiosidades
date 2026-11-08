"""Shorts do YouTube (canal PT): resumo de ~90 s de cada historia, mesma voz e fundo, "historia completa no canal".
criar(): chamado em main_story.  publicar/agendar: chamados pelo workflow (release publica -> Buffer YouTube)."""
import json, os, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

ESTADO = Path(os.environ.get("ESTADO_DIR", "output"))
ST = ESTADO / "yt_shorts.json"
LIMITE = 8                     # posts ativos no Buffer (plano gratis: 10 por canal)
SLOTS = [(18, 0), (21, 0)]
TZ = ZoneInfo("America/Sao_Paulo")
SYSTEM = ("Voce escreve o roteiro de um YouTube Short (cerca de 290 palavras) que RESUME uma historia real narrada em primeira pessoa, em portugues do Brasil, "
          "para despertar vontade de ver a historia completa. Regras: a primeira frase tem no maximo 12 palavras e traz o fato mais chocante; "
          "conte o essencial do comeco ao climax em ritmo rapido; NAO revele o desfecho final (termine no auge da tensao); a ultima frase e exatamente: "
          "'A historia completa esta no canal.' Mantenha os primeiros nomes comuns da historia; sem sobrenomes, links ou telefones. "
          "Responda SOMENTE JSON: {\"texto\": \"...\"}")


def _resumo(data):
    import writer
    base = "\n".join(p["texto"] for p in data["partes"])[:9000]
    for name, url, key, model in writer.providers():
        fb = ""
        for t in range(4):
            try:
                d = writer._chat(url, key, model, SYSTEM, f"Titulo: {data['titulo']}\n\nHistoria:\n{base}{fb}", tokens=2200)
                txt = " ".join(str(d.get("texto", "")).split())
                n = len(txt.split())
                if 230 <= n <= 360:
                    return txt
                print(f"::warning::short ({name}): {n} palavras, refazendo", flush=True)
                fb = f"\n\nATENCAO: seu texto anterior teve {n} palavras. Escreva entre 270 e 330 palavras (um texto LONGO, com mais detalhes do enredo)."
            except Exception as e:
                print(f"::warning::short ({name}) falhou: {str(e)[:100]}", flush=True)
                break
    raise RuntimeError("sem resumo")


def criar(d, data, voz, clip, pos):
    import tts, video
    d = Path(d)
    txt = tts.limpar_texto(_resumo(data))
    mp3, ass, mp4 = d / "voz_short.mp3", d / "legenda_short.ass", d / "short.mp4"
    words = tts.synth(txt, mp3, voz, rate="+8%")
    dur = words[-1][1] if words else 90
    total = min(dur + 0.6, 170)
    fim = [(max(dur - 5, 0), None, "HISTÓRIA COMPLETA NO CANAL", "End")]
    tts.make_ass(words, ass, script=txt, overlays=fim)
    calmo = any(j in clip[0].name for j in ("subway", "roblox", "gta"))
    video.build_mc(clip[0], (pos + 17) % max(1, clip[1] - total), total, mp3, ass, mp4, None, calmo, cap_over=20e6)
    titulo = f"{data['titulo']} 😱 #shorts"[:100]
    desc = f"{data['titulo']}: a história completa está no canal! Inscreva-se e ative o sininho 🔔 #shorts #historiasreais #historiasdoreddit #drama"
    (d / "short.json").write_text(json.dumps({"titulo": titulo, "descricao": desc, "dur": round(total)}, ensure_ascii=False))
    print(f"short.mp4: {total:.0f}s", flush=True)


def _load():
    return json.loads(ST.read_text()) if ST.exists() else []


def _save(x):
    ESTADO.mkdir(parents=True, exist_ok=True)
    ST.write_text(json.dumps(x, ensure_ascii=False, indent=1))


def publicar(d):
    d = Path(d)
    if not (d / "short.mp4").exists():
        print("sem short.mp4:", d); return
    meta = json.loads((d / "short.json").read_text())
    tag = "yts-" + d.name
    subprocess.run(["gh", "release", "create", tag, str(d / "short.mp4"), "--title", tag, "--notes", "short YouTube (apagada apos postar)"], check=True)
    repo = os.environ.get("GITHUB_REPOSITORY", "KyoGhostt/tiktok-curiosidades")
    s = _load()
    s.append({"id": d.name, "tag": tag, "titulo": meta["titulo"], "descricao": meta["descricao"],
              "url": f"https://github.com/{repo}/releases/download/{tag}/short.mp4", "status": "pendente"})
    _save(s)
    print("short publicado na release", tag)


def agendar():
    import buffer_post as bp, requests
    s = _load(); agora = datetime.now(timezone.utc)
    for i in s:   # limpa releases de Shorts ja postados (>2 h)
        if i["status"] == "agendado" and datetime.fromisoformat(i["due"]) < agora - timedelta(hours=2) and not i.get("limpo"):
            subprocess.run(["gh", "release", "delete", i["tag"], "--cleanup-tag", "-y"], check=False); i["limpo"] = True
    s = [i for i in s if not i.get("limpo")]
    ativos = [i for i in s if i["status"] == "agendado" and datetime.fromisoformat(i["due"]) > agora]
    pend = [i for i in s if i["status"] == "pendente"]
    if not pend or len(ativos) >= LIMITE:
        _save(s); print(f"yt: ativos={len(ativos)} pendentes={len(pend)}"); return
    ch = None
    for o in bp.gql(bp.Q_ORG)["account"]["organizations"]:
        for c in bp.gql(bp.Q_CHANNELS, {"o": o["id"]})["channels"]:
            if c["service"] == "youtube" and not c["isDisconnected"] and not c["isLocked"]:
                ch = c["id"]
    if not ch:
        raise RuntimeError("canal YouTube nao conectado no Buffer")
    ult = max([datetime.fromisoformat(i["due"]) for i in ativos] + [agora + timedelta(hours=1)])
    t, day = ult.astimezone(TZ), ult.astimezone(TZ).date()
    slots = []
    while len(slots) < min(LIMITE - len(ativos), len(pend)):
        if day.weekday() != 6:
            for h, m in SLOTS:
                dt = datetime(day.year, day.month, day.day, h, m, tzinfo=TZ)
                if dt > t: slots.append(dt)
        day += timedelta(days=1)
    for i, dt in zip(pend, slots):
        r = bp.gql(bp.M_POST, {"i": {"channelId": ch, "schedulingType": "automatic", "mode": "customScheduled", "dueAt": dt.isoformat(),
                                    "text": i["descricao"], "assets": [{"video": {"url": i["url"]}}],
                                    "metadata": {"youtube": {"title": i["titulo"], "categoryId": "24", "privacy": "public",
                                                              "madeForKids": False, "notifySubscribers": False}}}})["createPost"]
        if r["__typename"] != "PostActionSuccess":
            print("::warning::Buffer recusou short:", r.get("message")); break
        i.update(status="agendado", due=dt.isoformat(), buffer_id=r["post"]["id"])
        print("short agendado:", i["titulo"], dt.isoformat(), flush=True)
    _save(s)


if __name__ == "__main__":
    c = sys.argv[1]
    publicar(sys.argv[2]) if c == "publicar" else agendar()
