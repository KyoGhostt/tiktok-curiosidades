"""Gameplay vertical por história: Minecraft parkour (Automate Socials, uso livre) ou Subway Surfers (Internet Archive, gravações
verticais; o item de 2024 é CC0 e sem HUD). Se uma fonte sair do ar, a outra assume. MC_JOGO=minecraft|subway força uma delas."""
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


# só o item CC0, que tem a tela limpa (sem placar/HUD/menus) nos 193 s inteiros (conferido quadro a quadro);
# os outros itens do Archive têm placar, menus e anúncios na tela e foram descartados.
SUBWAY = ["subway-surfers-2024-gameplay-4-k-9x-16-no-copyright-1"]


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


def pick_biblioteca():
    """Fundo da biblioteca (release 'fundos' do GitHub): só arquivos listados em fundos/aprovados.txt, jogo sorteado entre os disponíveis."""
    try:
        ap = Path("fundos/aprovados.txt")
        ok = {l.strip() for l in ap.read_text().splitlines() if l.strip() and not l.startswith("#")} if ap.exists() else set()
        repo = os.environ.get("GITHUB_REPOSITORY", "KyoGhostt/tiktok-curiosidades")
        assets = requests.get(f"https://api.github.com/repos/{repo}/releases/tags/fundos", headers=UA, timeout=30).json().get("assets", [])
        ass = [a for a in assets if a["name"] in ok]
        if not ass:
            return None
        jogos = sorted({a["name"].split("_")[0] for a in ass})
        jogo = random.choice(jogos)
        a = random.choice([x for x in ass if x["name"].startswith(jogo + "_")])
        DIR.mkdir(parents=True, exist_ok=True)
        v = DIR / f"bib_{a['name']}"
        with requests.get(a["browser_download_url"], headers=UA, stream=True, timeout=600) as r:
            r.raise_for_status()
            with open(v, "wb") as f:
                for chunk in r.iter_content(1 << 20):
                    f.write(chunk)
        d = duration(v)
        print(f"biblioteca: {a['name']} ({d/60:.1f} min)", flush=True)
        return (v, d) if d > 60 else None
    except Exception as e:
        print("biblioteca: falhou ->", repr(e)[:200], flush=True)
        return None


def pick_clip():
    """Escolhe o jogo da história (sorteio; se a fonte falhar, tenta a outra)."""
    ordem = [pick_minecraft, pick_subway, pick_biblioteca]
    forca = os.environ.get("MC_JOGO", "")
    if forca == "subway": ordem = [pick_subway]
    elif forca == "biblioteca": ordem = [pick_biblioteca]
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
