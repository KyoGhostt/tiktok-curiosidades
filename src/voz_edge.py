"""Teste de vozes extras do edge-tts (grátis, multilíngues) lendo português, mesmo texto/fundo/legenda do robô."""
import random, subprocess
from pathlib import Path
import tts, video, capa, mc
from voz_texto import TEXTO
OUT = Path("/tmp/previews"); OUT.mkdir(exist_ok=True, parents=True)
W = Path("/tmp/ve"); W.mkdir(exist_ok=True)
VOZES = ["pt-BR-ThalitaMultilingualNeural", "en-US-AndrewMultilingualNeural", "en-US-BrianMultilingualNeural",
         "fr-FR-RemyMultilingualNeural", "de-DE-FlorianMultilingualNeural", "en-US-AvaMultilingualNeural", "en-US-EmmaMultilingualNeural"]
clip = mc.pick_minecraft()
for v in VOZES:
    nome = v.replace("Neural", "").replace("Multilingual", "-multi")
    try:
        mp3 = W / f"{nome}.mp3"
        words = tts.synth(tts.limpar_texto(TEXTO), mp3, v)
        ass = W / f"{nome}.ass"
        dur = tts.make_ass(words, ass, script=None, overlays=[(0, None, v.split("-")[2][:12].upper(), "Badge")])
        total = dur + 0.6
        card = capa.card(W / f"{nome}.png", "Teste de voz " + nome, "x", "x", 1, 1)
        full = W / f"{nome}_f.mp4"
        video.build_mc(clip[0], random.uniform(0, max(1, clip[1] - total)), total, mp3, ass, full, card)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(full), "-vf", "scale=540:960", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "30", "-c:a", "aac", "-b:a", "96k", str(OUT / f"edge-{nome}.mp4")], check=True)
        full.unlink(missing_ok=True); print("ok", v, f"{dur:.0f}s", flush=True)
    except Exception as e:
        print("FALHOU", v, repr(e)[:150], flush=True)
