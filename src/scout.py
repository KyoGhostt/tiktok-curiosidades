"""Scout: acha assuntos. 100% free, sem chave (Wikipedia PT)."""
import json, random, requests
from datetime import date, timedelta
from config import OUT

UA = {"User-Agent": "curiosidades-bot/1.0"}
DEBUG = []
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
    pool = [t for t in random_topics(20) + trending_topics(5) if t not in used]
    random.shuffle(pool)
    for t in pool:
        s = summary(t)
        if len(s) > 200:
            used.add(t)
            HIST.write_text(json.dumps(sorted(used), ensure_ascii=False))
            return t, s
    raise RuntimeError("Nenhum tópico encontrado")


def _local(tag):
    return tag.split("}")[-1]


def google_trends(geo="BR"):
    """Google Trends (RSS público, sem chave): buscas em alta no Brasil + manchetes ligadas."""
    import xml.etree.ElementTree as ET
    r = requests.get(f"https://trends.google.com/trending/rss?geo={geo}", timeout=20, headers={
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
        "Accept": "application/rss+xml,text/xml,*/*", "Accept-Language": "pt-BR,pt;q=0.9"})
    DEBUG.append(f"google_trends http {r.status_code} {len(r.content)}b {r.text[:80]!r}")
    r.raise_for_status()
    out = []
    for it in ET.fromstring(r.content).iter("item"):
        d = {"term": "", "traffic": "", "news": []}
        for ch in it:
            n = _local(ch.tag)
            if n == "title": d["term"] = (ch.text or "").strip()
            elif n == "approx_traffic": d["traffic"] = (ch.text or "").strip()
            elif n == "news_item":
                for x in ch:
                    if _local(x.tag) == "news_item_title" and x.text: d["news"].append(x.text.strip())
        if d["term"]: out.append(d)
    return out


def get_trends():
    """Lista de assuntos do momento (mais recente primeiro). Tolerante a falhas de cada fonte."""
    trends = []
    try:
        trends += google_trends()
    except Exception as e:
        DEBUG.append("google_trends erro: " + type(e).__name__ + " " + str(e)[:150])
    try:
        for t in trending_topics(10):
            trends.append({"term": t, "traffic": "wikipedia", "news": []})
    except Exception:
        pass
    used = _used()
    return [t for t in trends if t["term"] not in used][:20]


def mark_used(term):
    used = _used(); used.add(term)
    HIST.write_text(json.dumps(sorted(used), ensure_ascii=False))


def wiki_lookup(term, max_items=2):
    """Acha artigos da Wikipedia PT sobre o termo e devolve o texto-base (fatos verificáveis)."""
    r = requests.get("https://pt.wikipedia.org/w/api.php", headers=UA, timeout=20, params={
        "action": "opensearch", "search": term, "limit": max_items, "namespace": 0, "format": "json"})
    titles = r.json()[1] if r.ok else []
    texts = [summary(t) for t in titles]
    return " ".join(t for t in texts if t)[:2500]
