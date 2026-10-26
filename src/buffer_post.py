"""Agenda as 3 partes da história no Buffer (TikTok, publicação automática).
O Buffer precisa de um link PÚBLICO e estável até a hora de postar: os vídeos ficam na branch `media`."""
import json, os, sys
from pathlib import Path
import requests

API = "https://api.buffer.com"
Q_ORG = "query{account{organizations{id}}}"
Q_CHANNELS = "query($o:OrganizationId!){channels(input:{organizationId:$o}){id service isDisconnected isLocked}}"
M_POST = """mutation($i:CreatePostInput!){createPost(input:$i){
  __typename
  ... on PostActionSuccess{post{id status dueAt}}
  ... on MutationError{message}}}"""


def key():
    return (os.environ.get("BUFFER_API_KEY") or os.environ.get("BUFFER_TOKEN") or "").strip()


def gql(query, variables=None):
    r = requests.post(API, json={"query": query, "variables": variables or {}}, timeout=60,
                      headers={"Authorization": f"Bearer {key()}", "Content-Type": "application/json"})
    r.raise_for_status()
    j = r.json()
    if j.get("errors"):
        raise RuntimeError(str(j["errors"])[:500])
    return j["data"]


def tiktok_channel():
    for o in gql(Q_ORG)["account"]["organizations"]:
        for c in gql(Q_CHANNELS, {"o": o["id"]})["channels"]:
            if c["service"] == "tiktok" and not c["isDisconnected"] and not c["isLocked"]:
                return c["id"]
    raise RuntimeError("Nenhum canal TikTok conectado no Buffer")


def schedule(d, base_url):
    d = Path(d)
    info = json.loads((d / "info.json").read_text())
    ch = tiktok_channel()
    for p in info["partes"]:
        if p.get("buffer_id"):
            continue
        url = f"{base_url}/{d.name}/{p['arquivo']}"
        r = gql(M_POST, {"i": {
            "channelId": ch, "schedulingType": "automatic", "mode": "customScheduled",
            "dueAt": p["postar_em"], "text": p["legenda"], "aiAssisted": True,
            "assets": [{"video": {"url": url}}],
            "metadata": {"tiktok": {"isAiGenerated": True, "title": p["titulo"][:90]}}}})["createPost"]
        if r["__typename"] != "PostActionSuccess":
            raise RuntimeError(f"Buffer recusou parte {p['parte']}: {r.get('message')}")
        p["buffer_id"] = r["post"]["id"]
        print(f"buffer: parte {p['parte']} agendada {r['post']['dueAt']} id={p['buffer_id']}")
    (d / "info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if not key():
        print("Buffer não configurado (secret BUFFER_API_KEY ausente)"); sys.exit(0)
    schedule(sys.argv[1], sys.argv[2])
