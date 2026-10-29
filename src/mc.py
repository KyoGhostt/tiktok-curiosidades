"""Gameplay vertical por história: Minecraft parkour (Automate Socials, uso livre) ou Subway Surfers (Internet Archive, gravações
verticais; o item de 2024 é CC0). Se uma fonte sair do ar, a outra assume. MC_JOGO=minecraft|subway força uma delas."""
import os, random, re, subprocess, zipfile
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


SUBWAY = ["subway-surfers-2024-gameplay-4-k-9x-16-no-copyright-1", "vcompress_452", "vcompress_144", "recorder-18052024-072057"]


def archive_url(ident):
    """Maior vídeo (mp4/mov) do item do Internet Archive."""
    j = requests.get(f"https://archive.org/metadata/{ident}", headers=UA, timeout=30).json()
    vids = [f for f in j["files"] if f["name"].lower().endswith((".mp4", ".mov"))]
    f = max(vids, key=lambda x: int(x.get("size") or 0))
    return f"https://archive.org/download/{ident}/{requests.utils.quote(f['name'])}"


def pick_subway():
    try:
        ident = random.choice(SUBWAY)
        url = archive_url(ident)
        DIR.mkdir(parents=True, exist_ok=True)
        v = DIR / "subway.mp4"
        with requests.get(url, headers=UA, stream=True, timeout=180) as r:
            r.raise_for_status()
            with open(v, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        d = duration(v)
        print(f"subway surfers: {ident} ({d/60:.1f} min)", flush=True)
        return (v, d) if d > 60 else None
    except Exception as e:
        print("subway: falhou ->", repr(e)[:200], flush=True)
        return None


def pick_clip():
    """Escolhe o jogo da história (sorteio; se a fonte falhar, tenta a outra)."""
    ordem = [pick_minecraft, pick_subway]
    forca = os.environ.get("MC_JOGO", "")
    if forca == "subway": ordem = [pick_subway]
    elif forca == "minecraft": ordem = [pick_minecraft]
    else: random.shuffle(ordem)
    for fn in ordem:
        c = fn()
        if c:
            return c
    return None


def pick_minecraft():
    """Devolve (caminho_mp4, duracao_s) de um gameplay vertical de Minecraft, ou None se o download falhar."""
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
