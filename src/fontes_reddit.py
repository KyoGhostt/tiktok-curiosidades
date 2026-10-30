"""Sondagem (só leitura) de fontes de histórias do Reddit acessíveis a partir do GitHub Actions."""
import time, requests
from datetime import datetime, timedelta, timezone

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}
SUBS = ["AmItheAsshole", "relationship_advice", "pettyrevenge", "MaliciousCompliance", "entitledparents", "TIFU", "ProRevenge"]
sem = datetime.now(timezone.utc) - timedelta(days=7)


def tent(nome, f):
    t = time.time()
    try:
        print(f"[{nome}]", f(), f"({time.time()-t:.1f}s)", flush=True)
    except Exception as e:
        print(f"[{nome}] ERRO {type(e).__name__} {str(e)[:150]}", flush=True)


def rss(sub, host="www.reddit.com"):
    r = requests.get(f"https://{host}/r/{sub}/top/.rss?t=week&limit=25", headers=UA, timeout=25)
    return f"http {r.status_code} bytes {len(r.content)}"


def reddit_json(sub):
    r = requests.get(f"https://www.reddit.com/r/{sub}/top.json?t=week&limit=25", headers=UA, timeout=25)
    return f"http {r.status_code}"


def arctic(sub):
    r = requests.get("https://arctic-shift.photon-lab.ch/api/posts/search", headers=UA, timeout=60,
                     params={"subreddit": sub, "after": sem.strftime("%Y-%m-%d"), "sort": "desc", "limit": 100})
    if r.status_code != 200: return f"http {r.status_code} {r.text[:100]}"
    d = r.json().get("data", [])
    d = sorted(d, key=lambda p: -(p.get("score") or 0))
    ok = [p for p in d if 1500 <= len(p.get("selftext") or "") <= 9000]
    t = d[0] if d else {}
    return f"http 200 posts {len(d)} utilizaveis {len(ok)} | topo: score {t.get('score')} comentarios {t.get('num_comments')} len {len(t.get('selftext') or '')} '{(t.get('title') or '')[:70]}'"


def pullpush(sub):
    r = requests.get("https://api.pullpush.io/reddit/search/submission/", headers=UA, timeout=60,
                     params={"subreddit": sub, "after": int(sem.timestamp()), "sort_type": "score", "sort": "desc", "size": 25})
    if r.status_code != 200: return f"http {r.status_code}"
    d = r.json().get("data", [])
    ok = [p for p in d if 1500 <= len(p.get("selftext") or "") <= 9000]
    t = d[0] if d else {}
    return f"http 200 posts {len(d)} utilizaveis {len(ok)} | topo: score {t.get('score')} '{(t.get('title') or '')[:70]}'"


for sub in SUBS[:4]:
    tent(f"reddit-rss {sub}", lambda: rss(sub))
    tent(f"old.reddit-rss {sub}", lambda: rss(sub, "old.reddit.com"))
    tent(f"reddit-json {sub}", lambda: reddit_json(sub))
    tent(f"arctic-shift {sub}", lambda: arctic(sub))
    tent(f"pullpush {sub}", lambda: pullpush(sub))
for sub in SUBS[4:]:
    tent(f"arctic-shift {sub}", lambda: arctic(sub))
