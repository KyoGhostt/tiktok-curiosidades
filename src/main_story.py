import json, sys, traceback
from datetime import datetime
from config import OUT
import story, schedule, tts, video, reviewer, writer

VOZES = {"m": "pt-BR-AntonioNeural", "f": "pt-BR-FranciscaNeural"}


def build_package():
    data, post = None, None
    for cand in story.pick_story() + [None]:  # None = história original (reserva)
        try:
            data = story.write(cand); post = cand
            break
        except writer.TopicRejected:
            print("história rejeitada pelo filtro:", cand and cand["title"][:60])
            if cand: story._mark(cand["id"])
    if data is None:
        raise RuntimeError("nenhuma história aprovada")
    if post: story._mark(post["id"])
    origem = f"Baseado em relato do Reddit (r/{post['sub']})" if post else "História fictícia"
    now = datetime.now(schedule.TZ)
    slots = schedule.next_slots(3, now)
    d = OUT / ("hist-" + now.strftime("%Y%m%d-%H%M")); d.mkdir(parents=True)
    voz = VOZES.get(data.get("genero_narrador", "m"), VOZES["m"])
    tags_base = ["historiasdoreddit", "storytime"]
    esp = [t.lstrip("#").replace(" ", "") for t in data.get("hashtags", [])][:2]
    partes = []
    for i, p in enumerate(data["partes"], 1):
        mp3, ass, mp4 = d / f"voz{i}.mp3", d / f"legenda{i}.ass", d / f"parte{i}.mp4"
        words = tts.synth(p["texto"], mp3, voz)
        ov = [(0, None, f"PARTE {i}/3", "Badge")]
        if i < 3:
            fim = (words[-1][1] if words else 0)
            ov.append((fim - 2.2, None, (p.get("gancho_final") or "A história continua").upper() +
                       f"\\NPARTE {i+1} {schedule.quando(slots[i], slots[i-1]).upper()}", "End"))
        dur = tts.make_ass(words, ass, script=p["texto"], overlays=ov)
        total = dur + 0.6
        fundos = data["fundos"]
        n = 6  # cortes mais curtos (~10s), cada um com um clipe diferente
        scenes = [("@satisfying", total / n) for _ in range(n)]  # fundo satisfatório (slime etc.)
        video.build(scenes, mp3, ass, total, d, mp4)
        probs, secs = reviewer.check(mp4, {"hashtags": ["x"] * 5, "roteiro": p["texto"]}, lo=40, hi=125)
        titulo = f"{data['titulo']} (Parte {i}/3)"
        cta = f"Parte {i+1} {schedule.quando(slots[i], slots[i-1])}!" if i < 3 else "Final! O que você teria feito? Comenta!"
        tags = ([f"parte{i}"] + tags_base + esp)[:5]  # TikTok limita a 5 hashtags
        cap = f"{titulo} {cta} {origem}. " + " ".join("#" + t for t in tags)
        partes.append({"parte": i, "arquivo": f"parte{i}.mp4", "titulo": titulo, "legenda": cap, "duracao_s": round(secs),
                       "postar_em": slots[i-1].isoformat(), "quando": schedule.label(slots[i-1]), "avisos": probs})
        print(f"parte {i}: {secs:.0f}s, postar {schedule.label(slots[i-1])}, avisos={probs}")
    info = {"titulo": data["titulo"], "origem": origem, "fonte": post and post["id"], "partes": partes, "debug": story.DEBUG}
    (d / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))
    linhas = [f"# {data['titulo']}", f"_{origem}_", "", "| Parte | Postar em | Título |", "|---|---|---|"]
    linhas += [f"| {p['parte']}/3 | **{p['quando']}** | {p['titulo']} |" for p in partes]
    linhas += ["", "## Legendas para copiar", ""] + [f"**Parte {p['parte']}** (`{p['arquivo']}`)\n\n{p['legenda']}\n" for p in partes]
    body = "\n".join(linhas) + "\n<!--DATA:" + json.dumps(info, ensure_ascii=False) + "-->\n"
    (d / "agenda.md").write_text(body)
    return d


if __name__ == "__main__":
    try:
        build_package()
    except Exception:
        traceback.print_exc(); sys.exit(1)
