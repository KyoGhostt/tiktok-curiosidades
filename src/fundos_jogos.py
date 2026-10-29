"""Sondagem: o Pixabay tem gameplay de Subway Surfers / GTA / Roblox / Minecraft? Lista metadados e monta uma folha de miniaturas."""
import io, os, sys
import requests
from PIL import Image, ImageDraw
from config import PIXABAY_KEY

QUERIES = ["subway surfers gameplay", "subway surfer", "gta 5 gameplay", "gta gameplay", "roblox gameplay", "roblox",
           "minecraft parkour", "minecraft gameplay", "gameplay vertical", "mobile game gameplay"]
OUT = sys.argv[1] if len(sys.argv) > 1 else "/tmp/previews"


def main():
    os.makedirs(OUT, exist_ok=True)
    thumbs = []
    for q in QUERIES:
        r = requests.get("https://pixabay.com/api/videos/", params={"key": PIXABAY_KEY, "q": q, "per_page": 20}, timeout=30)
        j = r.json()
        hits = j.get("hits", [])
        print(f"## {q}: total={j.get('totalHits')} (mostrando {len(hits)})")
        for h in hits[:6]:
            v = h["videos"]
            best = v.get("large") or v.get("medium")
            vert = best["height"] > best["width"]
            print(f"  id={h['id']} {h['duration']}s {best['width']}x{best['height']}{' VERTICAL' if vert else ''} tags={h['tags'][:70]} user={h['user']}")
            if len(thumbs) < 48 and h["id"] not in [t[0] for t in thumbs]:
                thumbs.append((h["id"], q, v["tiny"]["thumbnail"]))
    W, H, cols = 240, 135, 6
    rows = (len(thumbs) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols, (H + 14) * rows), "black")
    d = ImageDraw.Draw(sheet)
    for i, (vid, q, url) in enumerate(thumbs):
        try:
            im = Image.open(io.BytesIO(requests.get(url, timeout=30).content)).convert("RGB").resize((W, H))
            x, y = (i % cols) * W, (i // cols) * (H + 14)
            sheet.paste(im, (x, y)); d.text((x + 2, y + H + 1), f"{vid} {q[:22]}", fill="white")
        except Exception as e:
            print("thumb falhou", vid, e)
    sheet.save(f"{OUT}/fundos-jogos.jpg", quality=80)


main()
