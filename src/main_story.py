"""Gera uma história completa (3 a 6 partes): roteiro PT-BR, voz, fundo (Minecraft ou stock), cartão de abertura e legenda."""
import json, sys, traceback
from datetime import datetime
from config import OUT
import story, schedule, tts, video, reviewer, writer, capa, mc, otimo, lang

# Hashtags reais e muito usadas em PT-BR por tema (tags compostas inventadas não têm busca nenhuma)
TEMAS = {"trabalho": ["chefe", "trabalho"], "relacionamento": ["relacionamento", "casal"], "familia": ["familia", "drama"],
         "vinganca": ["vinganca", "justica"], "vizinhos": ["vizinhos", "confusao"], "amizade": ["amizade", "drama"],
         "escola": ["escola", "adolescencia"], "drama": ["drama", "historiasreais"]}
VOZES = lang.L["voz"]


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
    origem = f"Reddit ({sub})" if post else "original"
    now = datetime.now(schedule.TZ)
    d = OUT / ("hist-" + now.strftime("%Y%m%d-%H%M%S")); d.mkdir(parents=True)
    voz = VOZES.get(data.get("genero_narrador", "m"), VOZES["m"])
    n = len(data["partes"])
    tema = otimo.classificar(" ".join(p["texto"] for p in data["partes"]), data["titulo"])
    if lang.CODE == "pt" and tema == "drama" and data.get("tema", "") in otimo.POOL:
        tema = data["tema"]     # PT: mantém o tema do modelo quando o título não decide (comportamento anterior)
    clip = mc.pick_clip()  # um gameplay por história; cada parte continua de onde a anterior parou
    pos = 0.0
    if clip:
        import random
        pos = random.uniform(0, max(1, clip[1] * 0.5))
    partes = []
    for i, p in enumerate(data["partes"], 1):
        mp3, ass, mp4 = d / f"voz{i}.mp3", d / f"legenda{i}.ass", d / f"parte{i}.mp4"
        p["texto"] = tts.limpar_texto(p["texto"])  # sem "*", "_", "#" etc. (a voz lia "asterisco")
        nw = len(p["texto"].split())
        alvo_s = story.ALVO_MIN * 60 - 0.6
        mult = nw / story.ALVO_MIN / story.PPM * 1.08          # velocidade relativa da voz (1.0 = normal)
        for it in range(3):                                     # ajusta o ritmo medindo o áudio real até chegar perto de 5:00
            r = max(-40, min(60, round((mult - 1) * 100)))
            words = tts.synth(p["texto"], mp3, voz, rate=f"{r:+d}%")
            d_real = words[-1][1] if words else alvo_s
            print(f"  parte {i}: {nw} palavras, voz {r:+d}% -> {d_real:.0f}s (alvo {alvo_s:.0f}s)", flush=True)
            if abs(d_real - alvo_s) / alvo_s < 0.04 or r in (-40, 60):
                break
            mult *= d_real / alvo_s
        words = tts.ajustar(mp3, words, alvo_s)
        ov = [(0, None, lang.UI["parte"].format(i=i, n=n), "Badge")] if n > 1 else []
        if i < n:
            fim = (words[-1][1] if words else 0)
            ov.append((fim - 2.2, None, (p.get("gancho_final") or lang.UI["gancho"]).upper() +
                       "\\N" + lang.UI["continua"].format(j=i+1), "End"))
        dur = tts.make_ass(words, ass, script=p["texto"], overlays=ov)
        total = story.ALVO_MIN * 60.0 if 0.85 * story.ALVO_MIN * 60 <= dur + 0.6 <= 1.15 * story.ALVO_MIN * 60 else dur + 0.6
        sufixo = lang.UI["sufixo"].format(i=i, n=n) if n > 1 else ""
        titulo = f"{data['titulo']}{sufixo}"
        card = capa.card(d / f"capa{i}.png", data["titulo"], sub, p["texto"], i, n)
        if clip:
            video.build_mc(clip[0], pos % max(1, clip[1] - total), total, mp3, ass, mp4, card, calmo=any(j in clip[0].name for j in ("subway", "roblox", "gta")))
            pos += total
        else:
            fundos = data["fundos"]
            scenes = [(fundos[k % len(fundos)], total / 6) for k in range(6)]
            video.build(scenes, mp3, ass, total, d, mp4, card)
        probs, secs = reviewer.check(mp4, {"hashtags": ["x"] * 5, "roteiro": p["texto"]}, lo=240, hi=story.ALVO_MIN * 60 * 1.2)
        cap = otimo.legenda(titulo, i, n, tema)   # hashtags otimizadas (5 no total)
        partes.append({"parte": i, "arquivo": f"parte{i}.mp4", "titulo": titulo, "legenda": cap,
                       "duracao_s": round(secs), "avisos": probs, "fundo": (next((j for j in ("subway", "gta", "roblox") if j in clip[0].name), "minecraft")) if clip else "stock"})
        print(f"parte {i}/{n}: {secs:.0f}s fundo={next((j for j in ('subway', 'gta', 'roblox') if j in clip[0].name), 'minecraft') if clip else 'stock'} avisos={probs}", flush=True)
    info = {"id": d.name, "titulo": data["titulo"], "origem": origem, "fonte": post and post["id"], "n": n,
            "tema": tema, "partes": partes, "debug": story.DEBUG}
    (d / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))
    return d


if __name__ == "__main__":
    try:
        build_package()
    except Exception:
        traceback.print_exc(); sys.exit(1)
