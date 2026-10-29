"""Sondagem 3: (A) quadros ao longo do Subway Surfers CC0 e do mesmo clipe com corte que remove HUD; (B) GTA V parkour de carro no Archive."""
import subprocess, requests
from pathlib import Path
from PIL import Image, ImageDraw
import mc

OUT = Path("/tmp/previews"); OUT.mkdir(exist_ok=True, parents=True)
TMP = Path("/tmp/arq"); TMP.mkdir(exist_ok=True)
UA = mc.UA


def baixar(url, dest):
    with requests.get(url, headers=UA, stream=True, timeout=300) as r:
        r.raise_for_status()
        with open(dest, "wb") as f:
            for c in r.iter_content(1 << 20):
                f.write(c)


def quadro(src, t, vf, out):
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", str(src), "-frames:v", "1", "-vf", vf, str(out)], check=True, timeout=120)


def folha(imgs, rotulos, dest, cols, w, h):
    rows = (len(imgs) + cols - 1) // cols
    s = Image.new("RGB", (w * cols, (h + 14) * rows), "black"); d = ImageDraw.Draw(s)
    for i, (p, r) in enumerate(zip(imgs, rotulos)):
        x, y = (i % cols) * w, (i // cols) * (h + 14)
        s.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y)); d.text((x + 2, y + h + 1), r, fill="white")
    s.save(dest, quality=80)


# ---- A) Subway Surfers: o CC0 inteiro (a cada 15 s) e o vcompress_452 com corte anti-HUD ----
imgs, rot = [], []
cc0 = TMP / "cc0.src"; baixar(mc.archive_url(mc.SUBWAY[0]), cc0)
dur = mc.duration(cc0); print("cc0 dur", dur)
for t in range(3, int(dur) - 2, 15):
    p = TMP / f"cc0_{t}.png"; quadro(cc0, t, "scale=-2:480", p); imgs.append(p); rot.append(f"CC0 {t}s")
folha(imgs, rot, OUT / "sheet-cc0.jpg", 7, 130, 230 if False else 230)
vc = TMP / "vc.src"; baixar(mc.archive_url("vcompress_452"), vc)
CORTE = "crop=iw*0.68:ih*0.85:iw*0.12:ih*0.15,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,scale=-2:480"
imgs, rot = [], []
for t in (20, 80, 140, 200, 260, 320):
    p = TMP / f"vc_{t}.png"; quadro(vc, t, CORTE, p); imgs.append(p); rot.append(f"corte {t}s")
folha(imgs, rot, OUT / "sheet-corte.jpg", 6, 180, 320)

# ---- B) GTA V parkour de carro ----
vistos, linhas = [], []
for q in ("gta 5 car parkour", "gta v car parkour map", "gta online parkour map cars", "gta 5 stunt map no copyright", "gta v mega ramp parkour"):
    try:
        r = requests.get("https://archive.org/advancedsearch.php", params={"q": f"({q}) AND mediatype:movies", "fl[]": ["identifier"], "rows": 6,
                         "output": "json", "sort[]": "downloads desc"}, headers=UA, timeout=30).json()
        for d in r["response"]["docs"]:
            if d["identifier"] not in vistos: vistos.append(d["identifier"])
    except Exception as e:
        print("busca falhou", q, e)
imgs, rot = [], []
for ident in vistos[:14]:
    try:
        j = requests.get(f"https://archive.org/metadata/{ident}", headers=UA, timeout=30).json()
        vids = [f for f in j["files"] if f["name"].lower().endswith((".mp4", ".mov", ".mkv", ".webm"))]
        if not vids: continue
        f = max(vids, key=lambda x: int(x.get("size") or 0))
        print(f"{ident} | {j['metadata'].get('title','')[:50]} | {int(f.get('size') or 0)/1e6:.0f}MB {f.get('width')}x{f.get('height')} {f.get('length')}s | lic={j['metadata'].get('licenseurl','-')}")
        p = TMP / f"g_{len(imgs)}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "30", "-i", f"https://archive.org/download/{ident}/{requests.utils.quote(f['name'])}",
                        "-frames:v", "1", "-vf", "scale=-2:270", str(p)], check=True, timeout=90)
        imgs.append(p); rot.append(ident[:30])
    except Exception as e:
        print(ident, "falhou", str(e)[:80])
if imgs: folha(imgs, rot, OUT / "sheet-gta.jpg", 4, 300, 170)
