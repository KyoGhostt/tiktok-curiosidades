"""Editor: uma cena = um clipe relevante (Pixabay/Pexels), tudo em 9:16, voz + legenda queimada via FFmpeg."""
import random, subprocess, requests
from pathlib import Path
from config import PEXELS_KEY, PIXABAY_KEY

VF_VIDEO = "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30"
VF_IMAGE = ("scale=1620:2880:force_original_aspect_ratio=increase,crop=1620:2880,"
            "zoompan=z='min(1+on*0.0006,1.25)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s=1080x1920:fps=30")
ENC = ["-an", "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p"]


def run(cmd):
    r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if r.returncode:
        raise RuntimeError("ffmpeg falhou: " + r.stderr[-600:])


AI_TAGS = ("ai generated", "ai-generated", "generative", "midjourney", "artificial intelligence", "ai art", "digital art")


def _norm(w):
    w = w.lower().strip()
    return w[:-1] if w.endswith("s") and len(w) > 3 else w


def _score(tags, query):
    t = {_norm(x) for x in ",".join(tags).replace(" ", ",").split(",") if x}
    return sum(1 for w in query.split() if _norm(w) in t)


def _is_ai(tags):
    j = tags.lower()
    return any(a in j for a in AI_TAGS) or j.split(", ").count("ai") > 0


def _pixabay_videos(q):
    r = requests.get("https://pixabay.com/api/videos/", timeout=30,
                     params={"key": PIXABAY_KEY, "q": q, "per_page": 30, "safesearch": "true"})
    out = []
    for h in (r.json().get("hits", []) if r.ok else []):
        v = h["videos"].get("medium") or h["videos"].get("small")
        tags = h.get("tags", "")
        if v and v.get("url") and h.get("duration", 0) >= 4 and not _is_ai(tags):
            out.append((v["url"], "video", _score([tags], q)))
    return out


def _pixabay_images(q):
    r = requests.get("https://pixabay.com/api/", timeout=30,
                     params={"key": PIXABAY_KEY, "q": q, "per_page": 30, "orientation": "vertical",
                             "image_type": "photo", "safesearch": "true"})
    out = []
    for h in (r.json().get("hits", []) if r.ok else []):
        tags = h.get("tags", "")
        if h.get("largeImageURL") and not _is_ai(tags):
            out.append((h["largeImageURL"], "image", _score([tags], q)))
    return out


def _pexels_videos(q):
    r = requests.get("https://api.pexels.com/videos/search", headers={"Authorization": PEXELS_KEY}, timeout=30,
                     params={"query": q, "orientation": "portrait", "per_page": 15})
    out = []
    for v in (r.json().get("videos", []) if r.ok else []):
        f = min((x for x in v["video_files"] if x.get("width", 0) >= 540), key=lambda x: x["width"], default=None)
        if f: out.append((f["link"], "video", 1))
    return out


def candidates(query, used):
    """Ordem: vídeo relevante > foto relevante > vídeo qualquer. Só aceita o que bate com as tags da busca."""
    words = query.split()
    qs = [query] + ([w for w in words if len(w) > 3][:1] if len(words) > 1 else [])
    found = []
    for q in qs:
        for fn, ok in ((_pixabay_videos, PIXABAY_KEY), (_pixabay_images, PIXABAY_KEY), (_pexels_videos, PEXELS_KEY)):
            if not ok: continue
            try: found += [c for c in fn(q) if c[0] not in used and c[2] > 0]
            except Exception: pass
        if found: break
    found.sort(key=lambda c: (-c[2], c[1] != "video", random.random()))
    top = found[:12]
    random.shuffle(top)
    top.sort(key=lambda c: (-c[2], c[1] != "video"))
    return top[:4]


SATISFYING = ["slime", "kinetic sand", "soap cutting", "satisfying", "paint mixing", "hydraulic press",
              "marble run", "sand art", "slime asmr", "glitter", "foam", "clay"]


def satisfying_candidates(used):
    """Fundo 'que prende' (estilo slime/satisfatório): clipes livres do Pixabay, sem relação com o tema."""
    qs = random.sample(SATISFYING, 4)
    found = []
    for q in qs:
        try:
            found += [c for c in _pixabay_videos(q) if c[0] not in used]
        except Exception:
            pass
    random.shuffle(found)
    return found[:6]


def _luma(path):
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-vf", "select=eq(n\\,20),signalstats,metadata=print:key=lavfi.signalstats.YAVG:file=-",
                        "-frames:v", "1", "-f", "null", "-"], capture_output=True, text=True)
    import re
    m = re.search(r"YAVG=([\d.]+)", r.stderr + r.stdout)
    return float(m.group(1)) if m else 128.0


def _render_media(url, kind, dur, workdir, i, out):
    src = workdir / f"src{i}.{'mp4' if kind == 'video' else 'jpg'}"
    src.write_bytes(requests.get(url, timeout=120).content)
    if kind == "video":
        run(["ffmpeg", "-y", "-stream_loop", "-1", "-i", str(src), "-t", f"{dur:.3f}", "-vf", VF_VIDEO, *ENC, str(out)])
    else:
        run(["ffmpeg", "-y", "-loop", "1", "-framerate", "30", "-i", str(src), "-t", f"{dur:.3f}", "-vf", VF_IMAGE, *ENC, str(out)])


def render_scene(query, dur, workdir, i, used):
    out = workdir / f"cena{i}.mp4"
    cands = satisfying_candidates(used) if query == "@satisfying" else candidates(query, used)
    for url, kind, _ in cands:
        used.add(url)
        try:
            _render_media(url, kind, dur, workdir, i, out)
            if _luma(out) >= 35:
                return out
        except Exception:
            continue
    run(["ffmpeg", "-y", "-f", "lavfi", "-i", f"gradients=s=1080x1920:d={dur:.3f}:speed=0.02:c0=0x1a1a2e:c1=0x16213e:c2=0x0f3460:n=3",
         "-vf", "fps=30", *ENC, str(out)])
    return out


def build(scenes, mp3, ass, total, workdir, out):
    """scenes: [(busca, duracao_segundos)]"""
    used, parts = set(), []
    for i, (q, d) in enumerate(scenes):
        parts.append(render_scene(q, d, workdir, i, used))
    lst = workdir / "lista.txt"
    lst.write_text("".join(f"file '{p.resolve()}'\n" for p in parts))
    bg = workdir / "fundo.mp4"
    run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst), "-c", "copy", str(bg)])
    ass_path = str(Path(ass).resolve()).replace(":", r"\:")
    run(["ffmpeg", "-y", "-i", str(bg), "-i", str(mp3), "-vf", f"eq=brightness=-0.06:saturation=1.1,subtitles='{ass_path}'",
         "-map", "0:v", "-map", "1:a", "-t", f"{total:.2f}", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "160k", "-movflags", "+faststart", str(out)])
