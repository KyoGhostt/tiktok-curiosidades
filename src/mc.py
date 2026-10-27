"""Gameplay vertical de Minecraft (Automate Socials: uso livre, inclusive comercial). Baixa um dos 16 pacotes por história."""
import random, re, subprocess, zipfile
from pathlib import Path
import requests
from config import OUT

BASE = "https://automatesocials.com"
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
DIR = OUT / "mc"


def zip_urls():
    html = requests.get(f"{BASE}/gameplays/", headers=UA, timeout=30).text
    pages = sorted(set(re.findall(r"https://automatesocials\.com/\d{4}/\d\d/\d\d/minecraft-gameplay-\d+/", html)))
    urls = []
    for p in pages:
        try:
            h = requests.get(p, headers=UA, timeout=30).text
            m = re.search(r'https://automatesocials\.com/wp-content/uploads/[^"\']*Vertical[^"\']*\.zip', h)
            if m: urls.append(m.group(0))
        except Exception:
            continue
    return urls


def duration(path):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def pick_clip():
    """Devolve (caminho_mp4, duracao_s) de um gameplay vertical, ou None se o download falhar."""
    try:
        urls = zip_urls()
        if not urls:
            return None
        url = random.choice(urls)
        DIR.mkdir(parents=True, exist_ok=True)
        zp = DIR / "g.zip"
        with requests.get(url, headers=UA, stream=True, timeout=120) as r:
            r.raise_for_status()
            with open(zp, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        ex = DIR / "x"
        with zipfile.ZipFile(zp) as z:
            z.extractall(ex)
        zp.unlink()
        vids = sorted(p for p in ex.rglob("*") if p.suffix.lower() == ".mp4")
        if not vids:
            return None
        v = vids[0]
        d = duration(v)
        print(f"minecraft: {url.rsplit('/', 1)[-1]} -> {v.name} ({d/60:.1f} min)", flush=True)
        return (v, d) if d > 60 else None
    except Exception as e:
        print("minecraft: falhou ->", repr(e)[:200], flush=True)
        return None
