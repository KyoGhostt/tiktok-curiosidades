"""Amostra: 8 s de cada gameplay vertical do Internet Archive, já em 1080x1920, juntos num vídeo para você avaliar."""
import subprocess
from pathlib import Path
import mc

OUT = Path("/tmp/previews"); OUT.mkdir(exist_ok=True, parents=True)
partes = []
for i, ident in enumerate(mc.SUBWAY):
    try:
        url = mc.archive_url(ident)
        p = OUT / f"s{i}.mp4"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "70", "-i", url, "-t", "8", "-an",
                        "-vf", "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=30",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", str(p)], check=True, timeout=240)
        partes.append(p); print("ok", ident)
    except Exception as e:
        print("falhou", ident, str(e)[:100])
(OUT / "lista.txt").write_text("".join(f"file '{p.resolve()}'\n" for p in partes))
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(OUT / "lista.txt"), "-c", "copy", str(OUT / "amostra-subway.mp4")], check=True)
for p in partes: p.unlink()
