"""Scout: acha assuntos. 100% free, sem chave (Wikipedia PT)."""
import json, random, requests
from datetime import date, timedelta
from config import OUT

UA = {"User-Agent": "curiosidades-bot/1.0"}
HIST = OUT / "used_topics.json"


def _used():
    return set(json.loads(HIST.read_text())) if HIST.exists() else set()


def trending_topics(n=15):
    """Artigos mais lidos de ontem na Wikipedia PT (proxy de interesse do público)."""
    d = date.today() - timedelta(days=2)
    url = f"https://wikimedia.org/api/rest_v1/metrics/pageviews/top/pt.wikipedia/all-access/{d:%Y/%m/%d}"
    try:
        items = requests.get(url, headers=UA, timeout=20).json()["items"][0]["articles"]
    except Exception:
        items = []
    bad = ("Wikipédia", "Especial", "Página_principal", "Ficheiro", "Categoria", "Portal", "Ajuda")
    return [a["article"].replace("_", " ") for a in items if not a["article"].startswith(bad)][:n]


def random_topics(n=10):
    r = requests.get("https://pt.wikipedia.org/w/api.php", headers=UA, timeout=20, params={
        "action": "query", "list": "random", "rnnamespace": 0, "rnlimit": n, "format": "json"})
    return [x["title"] for x in r.json()["query"]["random"]]


def summary(title):
    r = requests.get(f"https://pt.wikipedia.org/api/rest_v1/page/summary/{requests.utils.quote(title)}",
                     headers=UA, timeout=20)
    return r.json().get("extract", "") if r.ok else ""


def pick_topic():
    used = _used()
    pool = [t for t in trending_topics() + random_topics() if t not in used]
    random.shuffle(pool)
    for t in pool:
        s = summary(t)
        if len(s) > 200:
            used.add(t)
            HIST.write_text(json.dumps(sorted(used), ensure_ascii=False))
            return t, s
    raise RuntimeError("Nenhum tópico encontrado")
