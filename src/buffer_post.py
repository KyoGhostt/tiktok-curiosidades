"""Cliente mínimo da API do Buffer (GraphQL)."""
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
