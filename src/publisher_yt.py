"""Publicador YouTube Shorts (Data API v3, upload resumível). Grátis: 100 uploads/dia."""
import json, os, time, requests

TOKEN_URL = "https://oauth2.googleapis.com/token"


def access_token():
    import tokens
    d = tokens.load("youtube.json")
    if not d:
        return None
    if d["expires_at"] - time.time() < 300:
        r = requests.post(TOKEN_URL, timeout=30, data={
            "client_id": os.environ["GOOGLE_CLIENT_ID"], "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
            "refresh_token": d["refresh_token"], "grant_type": "refresh_token"})
        n = r.json()
        if "access_token" not in n:
            raise RuntimeError(f"renovação do token do YouTube falhou: {n.get('error')} {n.get('error_description')} (refaça a autorização)")
        d.update(access_token=n["access_token"], expires_at=time.time() + n.get("expires_in", 3600))
        tokens.save(d, "youtube.json")
    return d["access_token"]


def publish(video, title, description, tags):
    tok = access_token()
    if not tok:
        return "YouTube: sem autorização (pulado)"
    meta = {"snippet": {"title": title[:95], "description": description[:4900] + "\n\n#Shorts",
                        "tags": [t[:30] for t in tags][:15], "categoryId": "27", "defaultLanguage": "pt", "defaultAudioLanguage": "pt"},
            "status": {"privacyStatus": os.environ.get("YT_PRIVACY", "public"), "selfDeclaredMadeForKids": False,
                       "containsSyntheticMedia": True}}
    size = os.path.getsize(video)
    init = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                         timeout=60, data=json.dumps(meta), headers={
                             "Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
                             "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"})
    if init.status_code != 200:
        raise RuntimeError(f"YouTube init {init.status_code}: {init.text[:300]}")
    with open(video, "rb") as f:
        up = requests.put(init.headers["Location"], data=f.read(), timeout=600, headers={"Content-Type": "video/mp4"})
    if up.status_code not in (200, 201):
        raise RuntimeError(f"YouTube upload {up.status_code}: {up.text[:300]}")
    j = up.json()
    return f"YouTube enviado: https://youtube.com/shorts/{j['id']} (privacidade {j['status'].get('privacyStatus')})"
