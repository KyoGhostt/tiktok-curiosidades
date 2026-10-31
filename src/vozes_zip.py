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

# ---- análise: quadros, transcrição do começo, ritmo e tom da voz ----
from PIL import Image
import numpy as np
try:
    from faster_whisper import WhisperModel
    wm = WhisperModel("small", device="cpu", compute_type="int8")
except Exception as e:
    wm = None; print("whisper indisponível:", e)
import librosa
for p in arqs:
    if p.suffix.lower() != ".mp4": continue
    nome = p.stem[:30]
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)], capture_output=True, text=True).stdout)
    ims = []
    for i in range(8):
        t = dur * (i + 0.5) / 8
        q = W / f"f{i}.png"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.1f}", "-i", str(p), "-frames:v", "1", "-vf", "scale=-2:480", str(q)])
        if q.exists(): ims.append(Image.open(q).convert("RGB"))
    if ims:
        w, h = ims[0].size
        s = Image.new("RGB", (w * 4, h * 2))
        for i, im in enumerate(ims): s.paste(im, ((i % 4) * w, (i // 4) * h))
        s.save(OUT / f"quadros-{nome}.jpg", quality=70)
    wav = W / "a.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "20", "-t", "75", "-i", str(p), "-ac", "1", "-ar", "16000", str(wav)])
    y, sr = librosa.load(str(wav), sr=16000)
    f0, vf, _ = librosa.pyin(y, fmin=70, fmax=400, sr=sr)
    f0 = f0[~np.isnan(f0)]
    print(f"\n=== {nome} ({dur:.0f}s) tom mediano {np.median(f0):.0f} Hz (p10 {np.percentile(f0,10):.0f} / p90 {np.percentile(f0,90):.0f})" if len(f0) else f"\n=== {nome} sem tom")
    if wm:
      try:
        segs, info = wm.transcribe(y.astype("float32"), language=None, beam_size=1)
        txt = " ".join(sg.text.strip() for sg in segs)
        pal = len(txt.split())
        print(f"idioma {info.language}; {pal} palavras em ~75 s = {pal/75*60:.0f} palavras/min")
        print("trecho:", txt[:500])
      except Exception as e:
        print("transcrição falhou:", str(e)[:150])
