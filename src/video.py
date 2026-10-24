"""Editor: fundo vertical 9:16 (Pexels free, ou fundo animado) + voz + legenda queimada via FFmpeg."""
import random, subprocess, requests
from config import PEXELS_KEY, PIXABAY_KEY


def _pixabay(kw):
    r = requests.get("https://pixabay.com/api/videos/", params={"key": PIXABAY_KEY, "q": kw, "per_page": 10,
                     "safesearch": "true"}, timeout=30)
    out = []
    for h in (r.json().get("hits", []) if r.ok else []):
        v = h["videos"].get("medium") or h["videos"].get("small")
        if v and v.get("url"):
            out.append((v["url"], h.get("duration", 8)))
    return out


def _pexels(kw):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": PEXELS_KEY},
                     params={"query": kw, "orientation": "portrait", "per_page": 8}, timeout=30)
    out = []
    for v in (r.json().get("videos", []) if r.ok else []):
        f = min((x for x in v["video_files"] if x.get("width", 0) >= 540), key=lambda x: x["width"], default=None)
        if f:
            out.append((f["link"], v.get("duration", 8)))
    return out


def fetch_backgrounds(keywords, dest, need_seconds):
    search = _pixabay if PIXABAY_KEY else _pexels if PEXELS_KEY else None
    if not search:
        return []
    files, total = [], 0
    for kw in keywords:
        try:
            vids = search(kw)
        except Exception:
            continue
        random.shuffle(vids)
        for url, dur in vids[:2]:
            p = dest / f"bg{len(files)}.mp4"
            p.write_bytes(requests.get(url, timeout=120).content)
            files.append(p); total += dur
            if total >= need_seconds:
                return files
    return files


def run(cmd):
    subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)


def render(bgs, mp3, ass, duration, out):
    dur = duration + 0.6
    if bgs:
        inputs = []
        for b in bgs:
            inputs += ["-stream_loop", "-1", "-i", str(b)]
        n = len(bgs)
        seg = dur / n
        parts = "".join(
            f"[{i}:v]trim=0:{seg:.2f},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,setsar=1,fps=30[v{i}];" for i in range(n))
        chain = "".join(f"[v{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=0[bg];"
    else:  # fallback sem chave: fundo gradiente animado
        inputs = ["-f", "lavfi", "-i", f"gradients=s=1080x1920:d={dur:.2f}:speed=0.02:c0=0x1a1a2e:c1=0x16213e:c2=0x0f3460:n=3"]
        parts, chain = "", "[0:v]fps=30[bg];"
    ass_path = str(ass).replace(":", r"\:")
    fc = f"{parts}{chain}[bg]eq=brightness=-0.12,subtitles='{ass_path}'[v]"
    ai = len(bgs) if bgs else 1
    run(["ffmpeg", "-y", *inputs, "-i", str(mp3), "-filter_complex", fc, "-map", "[v]", "-map", f"{ai}:a",
         "-t", f"{dur:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-pix_fmt", "yuv420p",
         "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)])
