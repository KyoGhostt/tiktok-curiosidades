import json, sys, traceback
from datetime import datetime
from config import OUT, VIDEOS_PER_RUN
import scout, writer, tts, video, reviewer, publisher


def one():
    topic, base = scout.pick_topic()
    meta = writer.write_script(topic, base)
    d = OUT / datetime.now().strftime("%Y%m%d-%H%M%S"); d.mkdir(parents=True)
    mp3, ass, mp4 = d / "voz.mp3", d / "legenda.ass", d / "video.mp4"
    words = tts.synth(meta["roteiro"], mp3)
    dur = tts.make_ass(words, ass)
    bgs = video.fetch_backgrounds(meta["palavras_chave_busca"], d, dur)
    video.render(bgs, mp3, ass, dur, mp4)
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
