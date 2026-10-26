"""Diagnóstico: o que o Pixabay realmente tem para fundo relaxante. Gera uma folha de contato numerada + lista."""
import json, os, subprocess, sys
from pathlib import Path
import requests

KEY = os.environ["PIXABAY_API_KEY"]
QUERIES = ["slime", "slime asmr", "satisfying slime", "soap", "cutting soap", "kinetic sand", "sand", "putty",
           "clay", "foam", "bubbles", "marble run", "liquid", "paint pouring", "play doh", "stress ball"]
out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
rows, n = [], 0
for q in QUERIES:
    r = requests.get("https://pixabay.com/api/videos/", params={"key": KEY, "q": q, "per_page": 20, "safesearch": "true"}, timeout=30)
    hits = r.json().get("hits", []) if r.ok else []
    print(f"{q}: {len(hits)} resultados", flush=True)
    for h in hits[:3]:
        v = h["videos"].get("tiny") or h["videos"].get("small")
        if not v or not v.get("url"):
            continue
        n += 1
        f = out / f"{n:02d}.mp4"
        f.write_bytes(requests.get(v["url"], timeout=60).content)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "1", "-i", str(f), "-frames:v", "1",
                        "-vf", f"scale=320:-2,drawtext=text='{n}':x=6:y=6:fontsize=36:fontcolor=white:box=1:boxcolor=black@0.7", str(out / f"{n:02d}.jpg")])
        rows.append({"n": n, "busca": q, "tags": h.get("tags"), "dur": h.get("duration"), "w": h["videos"].get("medium", {}).get("width"),
                     "h": h["videos"].get("medium", {}).get("height"), "id": h["id"]})
(out / "lista.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1))
subprocess.run(f"ffmpeg -y -loglevel error -pattern_type glob -i '{out}/*.jpg' -vf tile=8x6:padding=4 -frames:v 1 -q:v 3 {out}/folha.jpg", shell=True)
