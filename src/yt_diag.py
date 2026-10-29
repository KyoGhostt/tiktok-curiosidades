"""Diagnóstico: tenta baixar um vídeo específico do YouTube no Actions com vários 'clients' do yt-dlp."""
import subprocess, sys
from pathlib import Path

VID = sys.argv[1] if len(sys.argv) > 1 else "AwQSObT2VCo"
URL = f"https://www.youtube.com/watch?v={VID}"
for cli in ("default", "tv", "tv_embedded", "web_embedded", "ios", "android_vr", "mweb", "web_safari"):
    cmd = ["yt-dlp", "--no-warnings", "--no-playlist", "-f", "bv*[height<=1920]+ba/b", "--download-sections", "*0-10",
           "-o", f"t_{cli}.%(ext)s", URL]
    if cli != "default":
        cmd[1:1] = ["--extractor-args", f"youtube:player_client={cli}"]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        ok = any(Path(".").glob(f"t_{cli}.*"))
        print(f"::notice::{cli}: rc={r.returncode} baixou={ok} {(r.stderr or r.stdout).strip()[-160:]}".replace("\n", " "))
    except Exception as e:
        print(f"::notice::{cli}: erro {str(e)[:100]}")
