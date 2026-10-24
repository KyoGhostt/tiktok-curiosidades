"""Revisor: checagens automáticas antes de publicar."""
import subprocess, json


def check(video, meta):
    p = json.loads(subprocess.run(["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", str(video)],
                                  capture_output=True, text=True).stdout)
    dur = float(p["format"]["duration"])
    problems = []
    if not 25 <= dur <= 75: problems.append(f"duração {dur:.0f}s fora de 25-75s")
    if len(meta["hashtags"]) < 3: problems.append("poucas hashtags")
    if any(w in meta["roteiro"].lower() for w in ("clique no link", "compre", "cupom")): problems.append("tom de spam")
    return problems, dur
