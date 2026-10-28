"""Diagnóstico: procura gameplays no YouTube (licença Creative Commons / verticais) e testa se o download funciona no Actions."""
import json, subprocess, sys

QUERIES = ["subway surfers gameplay no copyright vertical", "gta 5 gameplay no copyright vertical",
           "roblox parkour gameplay no copyright vertical", "minecraft parkour gameplay no copyright vertical"]


def sh(cmd, timeout=300):
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


rows = []
for q in QUERIES:
    r = sh(["yt-dlp", "--skip-download", "--dump-json", "--no-warnings", "--ignore-errors", f"ytsearch8:{q}"], 600)
    n = 0
    for line in r.stdout.splitlines():
        try:
            j = json.loads(line)
        except Exception:
            continue
        n += 1
        rows.append({"q": q.split()[0], "id": j["id"], "titulo": j.get("title", "")[:60], "canal": j.get("channel", ""),
                     "dur_min": round((j.get("duration") or 0) / 60, 1), "lic": (j.get("license") or "")[:40],
                     "w": j.get("width"), "h": j.get("height")})
    print(f"::notice::busca '{q}': {n} resultados; stderr: {r.stderr.strip()[:200]}")
cc = [x for x in rows if "Creative Commons" in x["lic"]]
print(f"::notice::total {len(rows)}; com licença Creative Commons: {len(cc)}")
for x in cc[:25]:
    print("::notice::CC | %(q)s | %(id)s | %(canal)s | %(titulo)s | %(dur_min)smin | %(w)sx%(h)s | %(lic)s" % x)
json.dump(rows, open("yt_result.json", "w"), ensure_ascii=False, indent=1)
# teste de download: 20 s do primeiro CC (ou do primeiro resultado)
alvo = (cc or rows or [None])[0]
if alvo:
    r = sh(["yt-dlp", "-f", "bv*[height<=1080][ext=mp4]/bv*[height<=1080]/b", "--download-sections", "*0-20", "-o", "teste_yt.%(ext)s",
            "--no-warnings", f"https://www.youtube.com/watch?v={alvo['id']}"], 300)
    print(f"::notice::download teste {alvo['id']} rc={r.returncode} {(r.stderr or r.stdout)[-300:]}".replace("\n", " "))
