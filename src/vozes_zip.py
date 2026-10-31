"""Baixa o zip de exemplos de voz do Drive e lista o conteúdo (nome, duração, formato); guarda trechos curtos em /tmp/previews."""
import os, subprocess, zipfile
from pathlib import Path
W = Path("/tmp/vz"); W.mkdir(exist_ok=True)
OUT = Path("/tmp/previews"); OUT.mkdir(exist_ok=True, parents=True)
url = os.environ["DRIVE_URL"]
subprocess.run(["gdown", url, "-O", str(W / "v.zip")], capture_output=True, timeout=1800)
z = W / "v.zip"
print("zip:", z.exists() and z.stat().st_size // 1e6, "MB")
with zipfile.ZipFile(z) as f:
    f.extractall(W / "x")
arqs = sorted(p for p in (W / "x").rglob("*") if p.is_file())
print(len(arqs), "arquivos")
for p in arqs:
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,codec_name,width,height,sample_rate:format=duration", "-of", "compact", str(p)], capture_output=True, text=True)
    print(str(p.relative_to(W / "x")), "|", p.stat().st_size // 1000, "KB |", r.stdout.replace("\n", " ")[:200])
