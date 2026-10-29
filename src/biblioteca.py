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


def main():
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
