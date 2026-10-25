import json, sys, traceback
from datetime import datetime
from config import OUT, VIDEOS_PER_RUN
import scout, writer, tts, video, reviewer, publisher, publisher_yt


def one():
    meta, trend = None, None
    trends = scout.get_trends()
    for _ in range(4):
        if not trends:
            break
        plan = writer.plan_from_trends(trends)
        if not plan:
            break
        trends = [t for t in trends if t["term"] != plan["term"]]
        scout.mark_used(plan["term"])
        base = scout.wiki_lookup(plan["pesquisa"])
        if len(base) < 200:
            print("sem texto-base para", plan["pesquisa"]); continue
        try:
            meta = writer.write_script(plan["pesquisa"], base, plan); trend = plan; topic = plan["term"]
            print(f"assunto em alta: {plan['term']} -> {plan['pesquisa']}"); break
        except writer.TopicRejected:
            print("rejeitado:", plan["term"])
    if meta is None:  # reserva: tema aleatório da Wikipedia
        print("sem tendência utilizável; usando tema da Wikipedia")
        for _ in range(8):
            topic, base = scout.pick_topic()
            try: meta = writer.write_script(topic, base); break
            except writer.TopicRejected: print(f"tema rejeitado: {topic}")
        else:
            raise RuntimeError("nenhum tema aprovado")
    d = OUT / datetime.now().strftime("%Y%m%d-%H%M%S"); d.mkdir(parents=True)
    mp3, ass, mp4 = d / "voz.mp3", d / "legenda.ass", d / "video.mp4"
    words = tts.synth(meta["roteiro"], mp3)
    dur = tts.make_ass(words, ass, script=meta["roteiro"])
    total_len = dur + 0.6
    # tempo de cada cena = proporcional às palavras faladas
    counts = [len(c["texto"].split()) for c in meta["cenas"]]
    tot = sum(counts); cum = 0; starts = []
    for c in counts:
        starts.append(0.0 if cum == 0 else words[min(len(words) - 1, round(cum / tot * len(words)))][0])
        cum += c
    scenes = [(meta["cenas"][i]["busca"], (starts[i + 1] if i + 1 < len(starts) else total_len) - starts[i])
              for i in range(len(starts))]
    scenes = [(q, max(d, 1.0)) for q, d in scenes]
    video.build(scenes, mp3, ass, total_len, d, mp4)
    problems, total = reviewer.check(mp4, meta)
    import unicodedata
    def key(t): return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if c.isalnum())
    tags = [h.lstrip("#").replace(" ", "") for h in meta["hashtags"]]
    if trend:  # hashtag do assunto em alta, só se for curta o bastante para ser usável
        slug = "".join(ch for ch in trend["term"].title() if ch.isalnum())
        if 3 <= len(slug) <= 20: tags.insert(0, slug)
    tags += ["curiosidades", "voceSabia", "fy"]
    seen, uniq = set(), []
    for t in tags:
        if t and len(t) <= 30 and key(t) not in seen: seen.add(key(t)); uniq.append(t)
    tags = uniq[:8]
    cap = f"{meta['titulo']} " + " ".join("#" + t for t in tags) + " #ia"
    if problems:
        status = "REPROVADO: " + "; ".join(problems)
    else:
        outs = []
        for name, fn in (("tiktok", lambda: publisher.publish(mp4, cap)),
                         ("youtube", lambda: publisher_yt.publish(mp4, meta["titulo"], cap, tags))):
            try: outs.append(fn())
            except Exception as e: outs.append(f"{name} FALHOU: {str(e)[:200]}")
        status = " | ".join(outs)
    (d / "info.json").write_text(json.dumps({"debug": scout.DEBUG, "topic": topic, "trend": trend and {k: trend[k] for k in ("term", "traffic", "angulo")}, **meta, "caption": cap, "status": status},
                                            ensure_ascii=False, indent=2))
    print(f"[{topic}] {total:.0f}s -> {status}")
    if problems: raise RuntimeError(status)


if __name__ == "__main__":
    ok = True
    for _ in range(VIDEOS_PER_RUN):
        try: one()
        except Exception: traceback.print_exc(); ok = False
    sys.exit(0 if ok else 1)
