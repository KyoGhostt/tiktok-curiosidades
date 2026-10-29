"""Gera uma história completa (3 a 6 partes): roteiro PT-BR, voz, fundo (Minecraft ou stock), cartão de abertura e legenda."""
import json, sys, traceback
from datetime import datetime
from config import OUT
import story, schedule, tts, video, reviewer, writer, capa, mc, otimo

# Hashtags reais e muito usadas em PT-BR por tema (tags compostas inventadas não têm busca nenhuma)
TEMAS = {"trabalho": ["chefe", "trabalho"], "relacionamento": ["relacionamento", "casal"], "familia": ["familia", "drama"],
         "vinganca": ["vinganca", "justica"], "vizinhos": ["vizinhos", "confusao"], "amizade": ["amizade", "drama"],
         "escola": ["escola", "adolescencia"], "drama": ["drama", "historiasreais"]}
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
    sub = f"r/{post['sub']}" if post else "história original"
    origem = f"Baseado em relato do Reddit ({sub})" if post else "História fictícia"
    now = datetime.now(schedule.TZ)
    d = OUT / ("hist-" + now.strftime("%Y%m%d-%H%M%S")); d.mkdir(parents=True)
    voz = VOZES.get(data.get("genero_narrador", "m"), VOZES["m"])
    n = len(data["partes"])
    tema = data.get("tema", "") if data.get("tema", "") in otimo.POOL else "drama"
    clip = mc.pick_clip()  # um gameplay por história; cada parte continua de onde a anterior parou
    pos = 0.0
    if clip:
        import random
        pos = random.uniform(0, max(1, clip[1] * 0.5))
    partes = []
    for i, p in enumerate(data["partes"], 1):
        mp3, ass, mp4 = d / f"voz{i}.mp3", d / f"legenda{i}.ass", d / f"parte{i}.mp4"
        words = tts.synth(p["texto"], mp3, voz)
        ov = [(0, None, f"PARTE {i} DE {n}", "Badge")]
        if i < n:
            fim = (words[-1][1] if words else 0)
            ov.append((fim - 2.2, None, (p.get("gancho_final") or "A história continua").upper() +
                       f"\\NCONTINUA NA PARTE {i+1}", "End"))
        dur = tts.make_ass(words, ass, script=p["texto"], overlays=ov)
        total = dur + 0.6
        titulo = f"{data['titulo']} (Parte {i} de {n})"
        card = capa.card(d / f"capa{i}.png", data["titulo"], sub, p["texto"], i, n)
        if clip:
            video.build_mc(clip[0], pos % max(1, clip[1] - total), total, mp3, ass, mp4, card, calmo="subway" in clip[0].name)
            pos += total
        else:
            fundos = data["fundos"]
            scenes = [(fundos[k % len(fundos)], total / 6) for k in range(6)]
            video.build(scenes, mp3, ass, total, d, mp4, card)
        probs, secs = reviewer.check(mp4, {"hashtags": ["x"] * 5, "roteiro": p["texto"]}, lo=40, hi=125)
        cap = otimo.legenda(data["titulo"] + f" (Parte {i} de {n})", i, n, tema)   # hashtags otimizadas (5 no total)
        partes.append({"parte": i, "arquivo": f"parte{i}.mp4", "titulo": titulo, "legenda": cap,
                       "duracao_s": round(secs), "avisos": probs, "fundo": ("subway" if "subway" in clip[0].name else "minecraft") if clip else "stock"})
        print(f"parte {i}/{n}: {secs:.0f}s fundo={('subway' if 'subway' in clip[0].name else 'minecraft') if clip else 'stock'} avisos={probs}", flush=True)
    info = {"id": d.name, "titulo": data["titulo"], "origem": origem, "fonte": post and post["id"], "n": n,
            "tema": tema, "partes": partes, "debug": story.DEBUG}
    (d / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))
    return d


if __name__ == "__main__":
    try:
        build_package()
    except Exception:
        traceback.print_exc(); sys.exit(1)
