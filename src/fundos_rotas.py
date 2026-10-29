"""Sondagem de rotas para baixar gameplay sem copyright: Internet Archive e intermediários do YouTube (Piped/Invidious/cobalt)."""
import json, re, sys
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/124 Safari/537.36"}
IDS = ["XYC1Qtu1kZo", "hJcv2nZ8x84", "AwQSObT2VCo", "7YNdPOW4U5A", "RqOmh0kONFQ"]


def tenta(nome, fn):
    try:
        print(f"[ok] {nome}: {fn()}")
    except Exception as e:
        print(f"[falhou] {nome}: {str(e)[:160]}")


def archive(q):
    r = requests.get("https://archive.org/advancedsearch.php", params={"q": f"{q} AND mediatype:movies", "fl[]": ["identifier", "title", "downloads"],
                     "rows": 8, "output": "json", "sort[]": "downloads desc"}, headers=UA, timeout=30)
    r.raise_for_status()
    docs = r.json()["response"]["docs"]
    return [(d["identifier"], d.get("title", "")[:50], d.get("downloads")) for d in docs]


def piped(inst, vid):
    r = requests.get(f"{inst}/streams/{vid}", headers=UA, timeout=30)
    r.raise_for_status()
    j = r.json()
    vs = [s for s in j.get("videoStreams", []) if s.get("videoOnly") is False or True]
    return f"{j.get('title','')[:40]} streams={len(vs)} ex={(vs[0]['url'][:60] if vs else '-')}"


def invidious(inst, vid):
    r = requests.get(f"{inst}/api/v1/videos/{vid}", headers=UA, timeout=30)
    r.raise_for_status()
    j = r.json()
    f = j.get("formatStreams", [])
    return f"{j.get('title','')[:40]} formatos={len(f)}"


def cobalt(vid):
    r = requests.post("https://api.cobalt.tools/", json={"url": f"https://www.youtube.com/watch?v={vid}", "videoQuality": "1080"},
                      headers={**UA, "Accept": "application/json", "Content-Type": "application/json"}, timeout=30)
    return f"HTTP {r.status_code} {r.text[:150]}"


for q in ("subway surfers gameplay", "minecraft parkour gameplay", "gta v gameplay no copyright", "roblox gameplay"):
    tenta("archive.org " + q, lambda q=q: archive(q))
for inst in ("https://pipedapi.kavin.rocks", "https://api.piped.private.coffee", "https://pipedapi.adminforge.de"):
    tenta("piped " + inst, lambda inst=inst: piped(inst, IDS[0]))
for inst in ("https://inv.nadeko.net", "https://yewtu.be", "https://invidious.nerdvpn.de"):
    tenta("invidious " + inst, lambda inst=inst: invidious(inst, IDS[0]))
tenta("cobalt", lambda: cobalt(IDS[0]))
