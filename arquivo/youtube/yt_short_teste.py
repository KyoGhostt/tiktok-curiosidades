"""Teste rapido do Short do YouTube com um post do banco (sem gerar a historia inteira)."""
import json, os, random
from pathlib import Path
import mc, yt_short, lang

b = json.loads((Path(os.environ["ESTADO_DIR"]) / "banco.json").read_text())
p = random.choice([x for x in b if len(x["text"]) > 3000])
data = {"titulo": "A Sogra e a Obsessao Pela Foto", "partes": [{"texto": p["text"]}]}
clip = mc.pick_clip()
d = Path("output/hist-teste-short"); d.mkdir(parents=True, exist_ok=True)
yt_short.criar(d, data, lang.L["voz"]["f"], clip, 0)
