"""Publicador: TikTok Content Posting API (Direct Post). Renova o token sozinho. Sem auditoria o TikTok só aceita privado."""
import os, time, requests

BASE = "https://open.tiktokapis.com"


def access_token():
    if os.environ.get("TIKTOK_ACCESS_TOKEN"):
        return os.environ["TIKTOK_ACCESS_TOKEN"]
    import tokens
    d = tokens.load()
    if not d:
        return None
    if d["expires_at"] - time.time() < 600:  # renova com 10 min de folga
        r = requests.post(f"{BASE}/v2/oauth/token/", timeout=30,
                          headers={"Content-Type": "application/x-www-form-urlencoded"},
                          data={"client_key": os.environ["TIKTOK_CLIENT_KEY"], "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
                                "grant_type": "refresh_token", "refresh_token": d["refresh_token"]})
        n = r.json()
        if "access_token" not in n:
            raise RuntimeError(f"renovação do token falhou: {n.get('error')} {n.get('error_description')} (refaça a autorização)")
        d.update(access_token=n["access_token"], refresh_token=n.get("refresh_token", d["refresh_token"]),
                 expires_at=time.time() + n.get("expires_in", 86400))
        tokens.save(d)
    return d["access_token"]


def publish(video, caption):
    tok = access_token()
    if not tok:
        return "sem token do TikTok: vídeo só salvo (modo rascunho)"
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8"}
    ci = requests.post(f"{BASE}/v2/post/publish/creator_info/query/", headers=h, timeout=30).json()
    if ci.get("error", {}).get("code", "ok") != "ok":
        raise RuntimeError(f"creator_info: {ci['error']}")
    opts = ci.get("data", {}).get("privacy_level_options", ["SELF_ONLY"])
    want = os.environ.get("TIKTOK_PRIVACY", "PUBLIC_TO_EVERYONE")
    privacy = want if want in opts else ("SELF_ONLY" if "SELF_ONLY" in opts else opts[0])
    size = os.path.getsize(video)
    init = requests.post(f"{BASE}/v2/post/publish/video/init/", headers=h, timeout=60, json={
        "post_info": {"title": caption[:2200], "privacy_level": privacy, "is_aigc": True,
                      "disable_duet": False, "disable_comment": False, "disable_stitch": False},
        "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}})
    j = init.json()
    if j.get("error", {}).get("code", "ok") != "ok":
        raise RuntimeError(f"init: {j['error']}")
    d = j["data"]
    with open(video, "rb") as f:
        up = requests.put(d["upload_url"], data=f.read(), timeout=300, headers={
            "Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size-1}/{size}"})
    up.raise_for_status()
    status = "?"
    for _ in range(12):  # acompanha até 1 min
        time.sleep(5)
        s = requests.post(f"{BASE}/v2/post/publish/status/fetch/", headers=h, timeout=30, json={"publish_id": d["publish_id"]}).json()
        status = s.get("data", {}).get("status", "?")
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            break
    return f"TikTok {status} (privacidade {privacy}, publish_id {d['publish_id']})"
