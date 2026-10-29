"""Sondagem do Internet Archive: metadados (resolução, duração, licença) e um quadro de cada vídeo candidato."""
import subprocess, sys, requests
from pathlib import Path

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"}
OUT = Path("/tmp/previews/quadros"); OUT.mkdir(parents=True, exist_ok=True)
FIXOS = ["rpreplay-final-1680875953", "recorder-18052024-072057", "vcompress_452", "vcompress_144",
         "minecraft-parkour-gameplay-no-copyright-480p"]
CONSULTAS = ["subway surfers gameplay no copyright", "roblox obby gameplay", "roblox gameplay no copyright", "gta 5 gameplay no copyright",
             "gta v gameplay vertical", "minecraft parkour no copyright vertical", "gameplay no copyright vertical 9:16"]


def achar(q):
    r = requests.get("https://archive.org/advancedsearch.php", params={"q": f"({q}) AND mediatype:movies", "fl[]": ["identifier"],
                     "rows": 6, "output": "json", "sort[]": "downloads desc"}, headers=UA, timeout=30)
    return [d["identifier"] for d in r.json()["response"]["docs"]]


def inspecionar(ident):
    j = requests.get(f"https://archive.org/metadata/{ident}", headers=UA, timeout=30).json()
    m = j.get("metadata", {})
    vids = [f for f in j.get("files", []) if f["name"].lower().endswith((".mp4", ".mov", ".mkv"))]
    if not vids:
        return None
    f = sorted(vids, key=lambda x: -int(x.get("size") or 0))[0]
    mb = int(f.get("size") or 0) / 1e6
    w, h = f.get("width"), f.get("height")
    print(f"{ident} | {m.get('title','')[:45]} | {f['name'][:30]} {mb:.0f}MB {w}x{h} {f.get('length','?')}s | lic={m.get('licenseurl','-')} | {m.get('creator','')}")
    url = f"https://archive.org/download/{ident}/{f['name']}"
    png = OUT / f"{ident[:40]}.jpg"
    try:
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "20", "-i", url, "-frames:v", "1", "-vf", "scale=-2:360", str(png)],
                       timeout=90, check=True)
    except Exception as e:
        print("   quadro falhou:", str(e)[:80])
    return ident


vistos = []
for q in CONSULTAS:
    try:
        print("##", q)
        for i in achar(q):
            if i not in vistos and i not in FIXOS and len(vistos) < 18:
                vistos.append(i)
    except Exception as e:
        print("busca falhou", e)
for i in FIXOS + vistos:
    try:
        inspecionar(i)
    except Exception as e:
        print(i, "falhou:", str(e)[:80])
