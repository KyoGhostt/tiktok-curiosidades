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


def jogos_aprovados():
    """Jogos com pelo menos um arquivo aprovado em fundos/aprovados.txt (prefixo do nome: gta, subway, slime...)."""
    ap = Path("fundos/aprovados.txt")
    ok = [l.strip() for l in ap.read_text().splitlines() if l.strip() and not l.startswith("#")] if ap.exists() else []
    return sorted({n.split("_")[0] for n in ok})


def pick_biblioteca(jogo=None):
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
        jogo = jogo if jogo in jogos else random.choice(jogos)
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


PESO_MINECRAFT = 0.5   # Minecraft já tem muitos vídeos no ar: cada jogo da biblioteca pesa 1, Minecraft pesa 0,5 (31/10)


def pick_clip():
    """Escolhe o jogo da história: sorteio ponderado entre Minecraft (peso menor) e os jogos da biblioteca (GTA, Subway...).
    Se a fonte do jogo sorteado falhar, tenta os outros."""
    forca = os.environ.get("MC_JOGO", "")
    if forca == "subway": return pick_subway()
    if forca == "biblioteca": return pick_biblioteca()
    if forca == "minecraft": return pick_minecraft()
    jogos = ["minecraft"] + [j for j in jogos_aprovados() if j != "minecraft"]
    if "subway" not in jogos: jogos.append("subway")          # o clipe CC0 do Internet Archive conta como Subway
    peso = [PESO_MINECRAFT if j == "minecraft" else 1.0 for j in jogos]
    escolhido = random.choices(jogos, weights=peso, k=1)[0]
    ordem = [escolhido] + [j for j in jogos if j != escolhido]
    for j in ordem:
        if j == "minecraft": c = pick_minecraft()
        elif j == "subway": c = (pick_subway() if random.random() < 0.3 or "subway" not in jogos_aprovados() else None) or pick_biblioteca("subway") or pick_subway()
        else: c = pick_biblioteca(j)
        if c:
            print(f"jogo sorteado: {j}", flush=True)
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
