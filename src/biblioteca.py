"""Biblioteca de fundos: baixa UMA vez os vídeos de fundo do YouTube (com cookies), padroniza em 1080x1920 sem áudio, gera quadros de
conferência e guarda no release "fundos" do GitHub. Depois disso o YouTube nunca mais é necessário (mc.py baixa do release)."""
import os, re, subprocess, sys
from pathlib import Path
import requests
from PIL import Image, ImageDraw

REPO = os.environ.get("GITHUB_REPOSITORY", "KyoGhostt/tiktok-curiosidades")
OUT = Path("/tmp/previews"); OUT.mkdir(exist_ok=True, parents=True)
W = Path("/tmp/bib"); W.mkdir(exist_ok=True, parents=True)
MAX_S = 1200   # no máximo 20 min por vídeo (mantém o arquivo abaixo de ~700 MB)


def sh(cmd, t=3600):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=t)


def existentes():
    r = sh(["gh", "release", "view", "fundos", "--repo", REPO, "--json", "assets", "--jq", ".assets[].name"])
    return set(r.stdout.split()) if r.returncode == 0 else None


def sondar(p):
    r = sh(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height:format=duration", "-of", "csv=p=0:s=x", str(p)])
    a = r.stdout.split()
    w, h = (int(x) for x in a[0].split("x")[:2])
    return w, h, float(a[1]) if len(a) > 1 else 0.0


def folha(src, dest, dur):
    ts = list(range(5, int(dur) - 3, max(30, int(dur) // 16)))[:16]
    imgs = []
    for t in ts:
        p = W / f"q{t}.png"
        sh(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(t), "-i", str(src), "-frames:v", "1", "-vf", "scale=-2:360", str(p)])
        if p.exists(): imgs.append((p, t))
    if not imgs: return
    w, h, cols = 150, 266, 8
    rows = (len(imgs) + cols - 1) // cols
    s = Image.new("RGB", (w * cols, (h + 14) * rows)); d = ImageDraw.Draw(s)
    for i, (p, t) in enumerate(imgs):
        x, y = (i % cols) * w, (i // cols) * (h + 14)
        s.paste(Image.open(p).convert("RGB").resize((w, h)), (x, y)); d.text((x + 2, y + h + 1), f"{t}s", fill="white")
    s.save(dest, quality=80)


def processar(raw, nome):
    """Padroniza (1080x1920, sem áudio, máx. 20 min), gera quadros de conferência e guarda no release."""
    w, h, dur = sondar(raw)
    print(f"{nome}: origem {w}x{h} {dur:.0f}s {raw.stat().st_size/1e6:.0f}MB")
    if h <= w:
        print(f"  PULADO: horizontal ({w}x{h}); só entram vídeos verticais"); return
    fim = W / nome
    c = sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-t", str(MAX_S), "-an",
            "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-maxrate", "4M", "-bufsize", "8M", "-movflags", "+faststart", str(fim)])
    if c.returncode: print("  ffmpeg falhou:", c.stderr[-200:]); return
    d2 = sondar(fim)[2]
    folha(fim, OUT / f"conferir-{nome[:-4]}.jpg", d2)
    u = sh(["gh", "release", "upload", "fundos", str(fim), "--repo", REPO, "--clobber"])
    print(f"  guardado: {nome} {fim.stat().st_size/1e6:.0f}MB {d2:.0f}s" if u.returncode == 0 else f"  upload falhou: {u.stderr[-200:]}")
    fim.unlink()


def direto(url, nome):
    sh(["gh", "release", "create", "fundos", "--repo", REPO, "--title", "Biblioteca de fundos", "--notes", "Vídeos de fundo (gameplay vertical) usados pelo robô."])
    raw = W / "direto.mp4"
    with requests.get(url, stream=True, timeout=600) as r:
        r.raise_for_status()
        with open(raw, "wb") as f:
            for ch in r.iter_content(1 << 20):
                f.write(ch)
    processar(raw, nome)


def drive(url, jogo):
    """Baixa um ZIP (ou vídeo) compartilhado do Google Drive, padroniza cada vídeo vertical e guarda no release."""
    import zipfile, hashlib
    sh(["gh", "release", "create", "fundos", "--repo", REPO, "--title", "Biblioteca de fundos", "--notes", "Vídeos de fundo (gameplay vertical) usados pelo robô."])
    dest = W / "drive"; dest.mkdir(exist_ok=True)
    r = sh(["gdown", url, "-O", str(dest / "baixado.bin")], t=3000)
    print("gdown:", (r.stdout + r.stderr).strip()[-300:])
    bin_ = dest / "baixado.bin"
    if not bin_.exists() or bin_.stat().st_size < 1e6:
        print("FALHOU: download do Drive (link não público?)"); return
    print(f"baixado {bin_.stat().st_size/1e6:.0f} MB")
    arqs = []
    if zipfile.is_zipfile(bin_):
        orig = W / f"original_{jogo}.zip"   # cópia fiel do que o dono mandou (≤2 GB), para ele poder apagar do Drive
        bin_.rename(orig); bin_ = orig
        u = sh(["gh", "release", "upload", "fundos", str(orig), "--repo", REPO, "--clobber"], t=3000)
        print("original guardado:" if u.returncode == 0 else "upload do original falhou:", orig.name, (u.stderr or "")[-150:])
        with zipfile.ZipFile(bin_) as z:
            z.extractall(dest / "x")
        bin_.unlink()
        arqs = sorted(p for p in (dest / "x").rglob("*") if p.suffix.lower() in (".mp4", ".mov", ".mkv", ".webm", ".m4v"))
    else:
        arqs = [bin_]
    print(f"{len(arqs)} vídeo(s) no arquivo:", [a.name for a in arqs])
    have = existentes() or set()
    for a in arqs:
        base = re.sub(r"[^a-z0-9]+", "-", a.stem.lower()).strip("-")[:40] or "video"
        nome = f"{jogo}_{base}_{hashlib.md5(a.name.encode()).hexdigest()[:4]}.mp4"
        if nome in have: print("já existe:", nome); continue
        processar(a, nome)
        a.unlink(missing_ok=True)


def normalizar():
    """Arquivos que o dono subiu à mão no release com o prefixo raw_ (ex.: raw_gta_abc.mp4): padroniza, guarda como gta_abc.mp4 e apaga o raw."""
    r = sh(["gh", "release", "view", "fundos", "--repo", REPO, "--json", "assets", "--jq", ".assets[].name"])
    for a in [x for x in r.stdout.split() if x.startswith("raw_")]:
        d = sh(["gh", "release", "download", "fundos", "--repo", REPO, "-p", a, "-D", str(W), "--clobber"])
        if d.returncode: print("download falhou", a, d.stderr[-150:]); continue
        raw = W / a
        processar(raw, a[4:] if a.endswith(".mp4") else a[4:].rsplit(".", 1)[0] + ".mp4")
        sh(["gh", "release", "delete-asset", "fundos", a, "--repo", REPO, "-y"])
        raw.unlink(missing_ok=True)


def main():
    if os.environ.get("DRIVE_URL"):
        drive(os.environ["DRIVE_URL"].strip(), (os.environ.get("DIRETO_NOME") or "gta").strip()); return
    if os.environ.get("NORMALIZAR"):
        normalizar(); return
    if os.environ.get("DIRETO_URL"):
        direto(os.environ["DIRETO_URL"].strip(), os.environ["DIRETO_NOME"].strip()); return
    ck = os.environ.get("YT_COOKIES", "").strip()
    cookies = []
    if ck:
        (W / "cookies.txt").write_text(ck + "\n"); cookies = ["--cookies", str(W / "cookies.txt")]
    else:
        print("AVISO: secret YT_COOKIES vazio; o YouTube deve bloquear o download")
    have = existentes()
    if have is None:
        sh(["gh", "release", "create", "fundos", "--repo", REPO, "--title", "Biblioteca de fundos", "--notes", "Vídeos de fundo (gameplay vertical) usados pelo robô."])
        have = set()
    for linha in Path("fundos/links.txt").read_text().splitlines():
        if not linha.strip() or linha.startswith("#") or "|" not in linha: continue
        jogo, url = (x.strip() for x in linha.split("|", 1))
        m = re.search(r"(?:v=|youtu\.be/)([\w-]{11})", url)
        if not m: print("link inválido:", linha); continue
        nome = f"{jogo}_{m.group(1)}.mp4"
        if nome in have: print("já existe:", nome); continue
        raw = list(W.glob("raw.*"))
        for f in raw: f.unlink()
        r = sh(["yt-dlp", "--no-warnings", "--no-playlist", *cookies, "-f", "bv*[height<=1920]+ba/bv*[height<=1920]/b", "-o", str(W / "raw.%(ext)s"), url])
        raw = list(W.glob("raw.*"))
        if r.returncode or not raw:
            print(f"FALHOU {nome}: {(r.stderr or r.stdout).strip()[-200:]}"); continue
        w, h, dur = sondar(raw[0])
        print(f"{nome}: baixado {w}x{h} {dur:.0f}s")
        if h <= w:
            print(f"  PULADO: horizontal ({w}x{h}); só entram vídeos verticais"); continue
        fim = W / nome
        c = sh(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw[0]), "-t", str(MAX_S), "-an",
                "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-maxrate", "4M", "-bufsize", "8M", "-movflags", "+faststart", str(fim)])
        if c.returncode: print("  ffmpeg falhou:", c.stderr[-200:]); continue
        d2 = sondar(fim)[2]
        folha(fim, OUT / f"conferir-{nome[:-4]}.jpg", d2)
        u = sh(["gh", "release", "upload", "fundos", str(fim), "--repo", REPO, "--clobber"])
        print(f"  guardado: {nome} {fim.stat().st_size/1e6:.0f}MB {d2:.0f}s" if u.returncode == 0 else f"  upload falhou: {u.stderr[-200:]}")
        fim.unlink()
        for f in raw: f.unlink()


main()
