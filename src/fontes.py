"""Pesquisa de público na web: o que o Brasil está procurando e vendo. Cada fonte é tentada separadamente
(uma que falhar não derruba as outras) e o resultado de cada uma fica registrado."""
import json, re, sys
import requests

UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleTraffic/1.0 Chrome/124 Safari/537.36", "Accept-Language": "pt-BR,pt;q=0.9"}


def google_trends_br():
    """Assuntos em alta no Brasil agora (Google Trends, RSS público) com volume aproximado de buscas."""
    r = requests.get("https://trends.google.com/trending/rss?geo=BR", headers=UA, timeout=30)
    r.raise_for_status()
    out = []
    for it in re.findall(r"<item>(.*?)</item>", r.text, re.S):
        t = re.search(r"<title>(.*?)</title>", it, re.S)
        v = re.search(r"<ht:approx_traffic>(.*?)</ht:approx_traffic>", it)
        if t:
            out.append({"termo": re.sub(r"<!\[CDATA\[|\]\]>", "", t.group(1)).strip(), "buscas": v.group(1) if v else ""})
    return out


def tiktok_hashtags_br():
    """Hashtags em alta no TikTok Brasil (Creative Center, painel público do próprio TikTok)."""
    url = "https://ads.tiktok.com/creative_radar_api/v1/popular_trend/hashtag/list"
    r = requests.get(url, params={"page": 1, "limit": 50, "period": 7, "country_code": "BR", "sort_by": "popular"},
                     headers={**UA, "Referer": "https://ads.tiktok.com/business/creativecenter/inspiration/popular/hashtag/pc/pt"}, timeout=30)
    r.raise_for_status()
    j = r.json()
    lst = (j.get("data") or {}).get("list") or []
    if not lst:
        raise RuntimeError("resposta sem lista: " + str(j)[:200])
    return [{"tag": x.get("hashtag_name"), "posts": x.get("publish_cnt"), "views": x.get("video_views"),
             "tendencia": x.get("trend")} for x in lst]


def sugestoes(consulta, ds="yt"):
    """Autocompletar (o que as pessoas digitam de verdade): ds=yt é YouTube, vazio é Google."""
    p = {"client": "firefox", "hl": "pt-BR", "gl": "BR", "q": consulta}
    if ds: p["ds"] = ds
    r = requests.get("https://suggestqueries.google.com/complete/search", params=p, headers=UA, timeout=30)
    r.raise_for_status()
    return r.json()[1]


def buscas_por_tema():
    base = {"trabalho": "história chefe", "relacionamento": "história relacionamento", "familia": "história família",
            "vinganca": "história vingança", "vizinhos": "história vizinho", "amizade": "história amiga",
            "escola": "história escola", "drama": "histórias reddit"}
    out = {}
    for tema, q in base.items():
        out[tema] = {"youtube": sugestoes(q, "yt"), "google": sugestoes(q, "")}
    return out


def reddit_semana():
    """Quais histórias o mundo inteiro mais curte (alta semanal): serve de termômetro de tema."""
    out = {}
    for sub in ("AmItheAsshole", "pettyrevenge", "MaliciousCompliance", "TIFU", "entitledparents", "ProRevenge", "relationship_advice", "BestofRedditorUpdates"):
        r = requests.get(f"https://www.reddit.com/r/{sub}/top/.rss?t=week&limit=10", headers=UA, timeout=30)
        r.raise_for_status()
        out[sub] = len(re.findall(r"<entry>", r.text))
    return out


def endless_br():
    """Hashtags mais vistas no TikTok Brasil na semana (Endless Radar, atualiza a cada 6 h; só o top 10, bem geral)."""
    r = requests.get("https://endless.app/radar/tiktok/brazil", headers=UA, timeout=30)
    r.raise_for_status()
    tags = []
    for t in re.findall(r"tiktok\.com/tag/([\w%]+)", r.text):
        if t.lower() not in tags:
            tags.append(t.lower())
    if not tags:
        raise RuntimeError("nenhuma hashtag encontrada na página")
    return tags


FONTES = {"google_trends": google_trends_br, "tiktok_hashtags": tiktok_hashtags_br, "endless_tiktok_br": endless_br,
          "buscas_por_tema": buscas_por_tema, "reddit_semana": reddit_semana}


def coletar():
    res, status = {}, {}
    for nome, fn in FONTES.items():
        try:
            res[nome] = fn(); status[nome] = "ok"
        except Exception as e:
            res[nome] = None; status[nome] = f"falhou: {str(e)[:150]}"
    res["_status"] = status
    return res


if __name__ == "__main__":
    r = coletar()
    for k, v in r["_status"].items():
        print(k, "->", v)
    print(json.dumps({k: (v[:5] if isinstance(v, list) else v) for k, v in r.items() if k != "_status"}, ensure_ascii=False)[:3000])
