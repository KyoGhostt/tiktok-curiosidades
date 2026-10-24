import json, sys, traceback
from datetime import datetime
from config import OUT, VIDEOS_PER_RUN
import scout, writer, tts, video, reviewer, publisher


def one():
    for _ in range(8):
        topic, base = scout.pick_topic()
        try:
            meta = writer.write_script(topic, base); break
        except writer.TopicRejected:
            print(f"tema rejeitado: {topic}")
    else:
        raise RuntimeError("8 temas seguidos rejeitados")
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
    cap = f"{meta['titulo']} " + " ".join("#" + h.lstrip("#") for h in meta["hashtags"]) + " #curiosidades #ia"
    status = "REPROVADO: " + "; ".join(problems) if problems else publisher.publish(mp4, cap)
    (d / "info.json").write_text(json.dumps({"topic": topic, **meta, "caption": cap, "status": status},
                                            ensure_ascii=False, indent=2))
    print(f"[{topic}] {total:.0f}s -> {status}")
    if problems: raise RuntimeError(status)


if __name__ == "__main__":
    ok = True
    for _ in range(VIDEOS_PER_RUN):
        try: one()
        except Exception: traceback.print_exc(); ok = False
    sys.exit(0 if ok else 1)
