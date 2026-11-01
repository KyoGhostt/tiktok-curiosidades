"""Banco de histórias reais (Reddit) guardado em estado/<idioma>/banco.json.
O Reddit devolve 429 se pedirem muito de uma vez; então este script roda a cada poucas horas, pede POUCOS feeds com espera longa
e acumula candidatos. A geração (story.pick_story) lê o banco primeiro e só vai ao Reddit ao vivo se ele estiver vazio.
Uso: LANG_CODE=en python src/banco.py [sonda]"""
import json, os, random, sys, time
from pathlib import Path
import requests
import story, lang

ARQ = Path(os.environ.get("ESTADO_DIR", "/tmp/estado")) / "banco.json"
MAX = 120


def load():
    try:
        return json.loads(ARQ.read_text())
    except Exception:
        return []


def encher(combos=3):
    banco = load()
    ids = {p["id"] for p in banco} | story._used()
    comb = [(s, k) for s in lang.L["subs"] for k in ("top", "controversial")]
    random.shuffle(comb)
    novos = 0
    for sub, kind in comb[:combos]:
        try:
            for p in story.fetch_posts(sub, kind):
                if 2500 <= len(p["text"]) <= 20000 and p["id"] not in ids:
                    banco.append(p); ids.add(p["id"]); novos += 1
        except Exception as e:
            print(f"r/{sub}/{kind}: {type(e).__name__} {str(e)[:70]}", flush=True)
        time.sleep(25)
    banco = banco[-MAX:]
    ARQ.parent.mkdir(parents=True, exist_ok=True)
    ARQ.write_text(json.dumps(banco, ensure_ascii=False))
    print(f"[{lang.CODE}] banco: +{novos} novos, total {len(banco)}; debug: {' | '.join(story.DEBUG[-6:])}", flush=True)


MIRRORS = ["https://redlib.catsarch.com", "https://redlib.perennialte.ch", "https://l.opnxng.com", "https://safereddit.com",
           "https://redlib.nadeko.net", "https://old.reddit.com", "https://www.reddit.com"]


def sonda():
    for m in MIRRORS:
        for path in ("/r/relatos/top.rss?t=year", "/r/relatos/top/.rss?t=year"):
            try:
                r = requests.get(m + path, headers=story.UA, timeout=20)
                print(f"{m}{path}: http {r.status_code} {len(r.content)} bytes {'ATOM' if b'<entry' in r.content else ''}", flush=True)
            except Exception as e:
                print(f"{m}{path}: {type(e).__name__}", flush=True)


if __name__ == "__main__":
    sonda() if len(sys.argv) > 1 and sys.argv[1] == "sonda" else encher()
