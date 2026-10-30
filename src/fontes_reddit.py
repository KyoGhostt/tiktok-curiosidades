"""Sondagem (só leitura) de fontes de histórias acessíveis a partir do GitHub Actions."""
import time, requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"}


def tent(nome, f):
    try:
        print(f"[{nome}]", f(), flush=True)
    except Exception as e:
        print(f"[{nome}] ERRO {type(e).__name__} {str(e)[:120]}", flush=True)


def rss(sub, kind):
    r = requests.get(f"https://www.reddit.com/r/{sub}/{kind}/.rss?t=week&limit=25", headers=UA, timeout=25)
    if r.status_code == 429:
        time.sleep(10); r = requests.get(f"https://www.reddit.com/r/{sub}/{kind}/.rss?t=week&limit=25", headers=UA, timeout=25)
    return f"http {r.status_code} entradas {r.text.count('<entry>')}"


for sub in ["AITAH", "TrueOffMyChest", "JustNoMIL", "offmychest", "desabafos", "confessions", "BestofRedditorUpdates", "AmItheAsshole"]:
    for kind in ("top", "controversial"):
        tent(f"reddit r/{sub}/{kind}", lambda: rss(sub, kind)); time.sleep(4)


def lemmy(host):
    r = requests.get(f"https://{host}/api/v3/search", headers=UA, timeout=30, params={"q": "relationship advice", "type_": "Communities", "limit": 5, "sort": "TopAll"})
    if r.status_code != 200: return f"http {r.status_code}"
    cs = r.json().get("communities", [])
    return f"http 200 comunidades {[(c['community']['name'], c['counts']['subscribers']) for c in cs]}"


for h in ["lemmy.world", "lemmy.ml", "sh.itjust.works"]:
    tent(f"lemmy {h}", lambda: lemmy(h))
for nome, url in [("x.com", "https://x.com/search?q=desabafo"), ("nitter", "https://nitter.net/search?q=desabafo"),
                  ("quora", "https://pt.quora.com/"), ("medium-rss", "https://medium.com/feed/tag/relationships"),
                  ("tumblr-rss", "https://www.tumblr.com/tagged/storytime/rss"), ("hn", "https://hacker-news.firebaseio.com/v0/topstories.json")]:
    tent(nome, lambda: f"http {requests.get(url, headers=UA, timeout=25).status_code}")
