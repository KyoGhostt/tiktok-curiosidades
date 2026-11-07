"""Versão completa para o YouTube: junta as partes (mesma voz, mesmo fundo), SEM selo 'Parte X de N' nem 'continua', em 16:9 com boa qualidade."""
import subprocess
from pathlib import Path
import tts, video, lang


def _dur(f):
    return float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(f)],
                                capture_output=True, text=True).stdout.strip() or 0)


def completo(d, allw, clip, pos0):
    d = Path(d); n = len(allw)
    lst = d / "juntar.txt"
    lst.write_text("".join(f"file '{(d / f'voz{i}.mp3').resolve()}'\n" for i in range(1, n + 1)))
    mp3 = d / "voz_completo.mp3"
    video.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-c:a", "libmp3lame", "-b:a", "128k", str(mp3)])
    words, off = [], 0.0
    for i, (w, _t) in enumerate(allw, 1):
        words += [(a + off, b + off, t) for a, b, t in w]
        off += _dur(d / f"voz{i}.mp3")
    ass = d / "legenda_completo.ass"
    tts.make_ass(words, ass, script=" ".join(t for _w, t in allw), overlays=[])
    total = off + 0.6
    vert = d / "completo_vertical.mp4"
    calmo = any(j in clip[0].name for j in ("subway", "roblox", "gta"))
    video.build_mc(clip[0], pos0 % max(1, clip[1] - total), total, mp3, ass, vert, None, calmo, cap_over=250e6)
    out = d / "completo.mp4"
    video.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(vert), "-filter_complex",
               "[0:v]split[a][b];[a]scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,boxblur=24:6[bg];"
               "[b]scale=-2:720[fg];[bg][fg]overlay=(W-w)/2:0[v]", "-map", "[v]", "-map", "0:a", "-c:v", "libx264", "-preset", "veryfast",
               "-crf", "22", "-maxrate", "3500k", "-bufsize", "7000k", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart", str(out)])
    vert.unlink(missing_ok=True)
    print(f"completo.mp4: {_dur(out):.0f}s", flush=True)
