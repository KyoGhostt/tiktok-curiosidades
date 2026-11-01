"""Sondagem (só leitura): quais comunidades do Reddit dão relatos longos no idioma. Uso: sondar_subs.py sub1,sub2,..."""
import sys, time
import story
for sub in sys.argv[1].split(","):
    for kind in ("top", "controversial"):
        try:
            ps = story.fetch_posts(sub, kind)
            longos = [p for p in ps if len(p["text"]) >= 2500]
            print(f"r/{sub}/{kind}: {len(ps)} posts, {len(longos)} com 2500+ chars; ex.: {(longos or ps or [{'title':'-'}])[0]['title'][:70]}", flush=True)
        except Exception as e:
            print(f"r/{sub}/{kind}: ERRO {type(e).__name__} {str(e)[:60]}", flush=True)
        time.sleep(5)
