"""Diagnóstico: busca clipes de fundo no Pixabay e monta uma folha de contato (miniatura + tags + tamanho)."""
import io, json, os, sys
import requests
from PIL import Image, ImageDraw

KEY = os.environ["PIXABAY_API_KEY"]
QUERIES = sys.argv[1:] or ["slime", "slime asmr", "soap", "kinetic sand", "play doh", "putty", "satisfying"]
cells = []
for q in QUERIES:
    r = requests.get("https://pixabay.com/api/videos/", params={"key": KEY, "q": q, "per_page": 12, "safesearch": "true"}, timeout=30)
    hits = r.json().get("hits", []) if r.ok else []
    print(f"{q}: {len(hits)} resultados", flush=True)
    for h in hits[:8]:
        v = h["videos"].get("medium") or h["videos"].get("small") or {}
        thumb = f"https://i.vimeocdn.com/video/{h['picture_id']}_295x166.jpg"
        try:
            im = Image.open(io.BytesIO(requests.get(thumb, timeout=20).content)).convert("RGB").resize((295, 166))
        except Exception:
            continue
        cells.append((q, im, f"{h['duration']}s {v.get('width')}x{v.get('height')}", h.get("tags", "")[:44]))
W, H, cols = 295, 166 + 34, 6
rows = (len(cells) + cols - 1) // cols
sheet = Image.new("RGB", (cols * W, rows * H), "white")
d = ImageDraw.Draw(sheet)
for i, (q, im, info, tags) in enumerate(cells):
    x, y = (i % cols) * W, (i // cols) * H
    sheet.paste(im, (x, y))
    d.text((x + 3, y + 168), f"[{q}] {info}", fill="black")
    d.text((x + 3, y + 180), tags, fill="gray")
sheet.save("fundos.jpg", quality=85)
print("folha:", len(cells), "clipes")
