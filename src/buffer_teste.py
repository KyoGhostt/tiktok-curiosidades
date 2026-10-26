"""Teste único: publica a Parte 1 agora e remarca as partes 2 e 3 para amanhã (12h e 18h, Brasília)."""
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import buffer_post as bp

Q = """query($o:OrganizationId!){posts(first:30,input:{organizationId:$o,filter:{status:[scheduled]},
 sort:[{field:dueAt,direction:asc}]}){edges{node{id text dueAt assets{source}}}}}"""
E = """mutation($i:EditPostInput!){editPost(input:$i){__typename ... on PostActionSuccess{post{id status dueAt}} ... on MutationError{message}}}"""

org = bp.gql(bp.Q_ORG)["account"]["organizations"][0]["id"]
posts = [e["node"] for e in bp.gql(Q, {"o": org})["posts"]["edges"]]
tz = ZoneInfo("America/Sao_Paulo")
amanha = (datetime.now(tz) + timedelta(days=1)).date()
by = {}
for p in posts:
    m = re.search(r"\(Parte (\d)/3\)", p["text"])
    if m and "Regra da Chefe" in p["text"]:
        by[int(m.group(1))] = p
print("encontradas:", sorted(by))
assert sorted(by) == [1, 2, 3], "nao achei as 3 partes"
t1 = re.sub(r"Parte 2 hoje às 18h!", "Parte 2 amanhã às 12h!", by[1]["text"])
t2 = by[2]["text"].replace("Parte 3 hoje às 21h!", "Parte 3 amanhã às 18h!")
d12 = datetime(amanha.year, amanha.month, amanha.day, 12, 0, tzinfo=tz).isoformat()
d18 = datetime(amanha.year, amanha.month, amanha.day, 18, 0, tzinfo=tz).isoformat()
def inc(p, extra):
    url = p["assets"][0]["source"]
    t = extra.get("text", p["text"])
    return {**extra, "assets": [{"video": {"url": url}}], "metadata": {"tiktok": {"isAiGenerated": True, "title": t.split(" Parte ")[0][:90] + " (Parte %d/3)" % [k for k, v in by.items() if v is p][0]}}}


for pid, inp in [
    (by[2]["id"], inc(by[2], {"text": t2, "mode": "customScheduled", "dueAt": d12, "schedulingType": "automatic"})),
    (by[3]["id"], inc(by[3], {"mode": "customScheduled", "dueAt": d18, "schedulingType": "automatic"})),
    (by[1]["id"], inc(by[1], {"text": t1, "mode": "shareNow", "schedulingType": "automatic"})),   # o teste, por último
]:
    r = bp.gql(E, {"i": {"id": pid, **inp}})["editPost"]
    print(pid, r)
    if r["__typename"] != "PostActionSuccess":
        print(f"::error::editPost {pid}: {r}"); raise SystemExit(1)
    print(f"::notice::editPost {pid} -> {r}")
