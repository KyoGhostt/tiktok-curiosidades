"""Envia um video para o YouTube (API oficial, upload resumivel). Uso: python yt_upload.py arquivo.mp4 "Titulo" "Descricao" [privacy]
Projetos OAuth nao auditados: o YouTube forca 'private'. O usuario muda para publico no Studio (ou apos a auditoria sai publico)."""
import os, sys, json, requests

TOKEN_URL = "https://oauth2.googleapis.com/token"


def access_token():
    r = requests.post(TOKEN_URL, data={"client_id": os.environ["YT_CLIENT_ID"], "client_secret": os.environ["YT_CLIENT_SECRET"],
                                       "refresh_token": os.environ["YT_REFRESH_TOKEN"], "grant_type": "refresh_token"}, timeout=60)
    r.raise_for_status()
    return r.json()["access_token"]


def upload(path, titulo, descricao, privacy="private", categoria="24", tags=None):
    tok = access_token()
    meta = {"snippet": {"title": titulo[:100], "description": descricao[:4900], "categoryId": categoria, "tags": tags or [],
                        "defaultLanguage": "pt-BR", "defaultAudioLanguage": "pt-BR"},
            "status": {"privacyStatus": privacy, "selfDeclaredMadeForKids": False}}
    size = os.path.getsize(path)
    h = {"Authorization": f"Bearer {tok}", "Content-Type": "application/json; charset=UTF-8",
         "X-Upload-Content-Length": str(size), "X-Upload-Content-Type": "video/mp4"}
    r = requests.post("https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
                      headers=h, data=json.dumps(meta), timeout=60)
    r.raise_for_status()
    url = r.headers["Location"]
    chunk = 32 * 1024 * 1024
    with open(path, "rb") as f:
        pos = 0
        while pos < size:
            b = f.read(chunk)
            end = pos + len(b) - 1
            for t in range(5):
                try:
                    rr = requests.put(url, data=b, headers={"Content-Range": f"bytes {pos}-{end}/{size}", "Content-Type": "video/mp4"}, timeout=600)
                    break
                except requests.RequestException as e:
                    print("retry", t, e, flush=True)
            if rr.status_code in (200, 201):
                vid = rr.json()["id"]
                print(f"enviado: https://youtu.be/{vid} (privacy={rr.json()['status']['privacyStatus']})", flush=True)
                return vid
            if rr.status_code != 308:
                raise RuntimeError(f"falha no envio {rr.status_code}: {rr.text[:300]}")
            pos = end + 1
    raise RuntimeError("envio nao concluiu")


if __name__ == "__main__":
    a = sys.argv
    upload(a[1], a[2], a[3], a[4] if len(a) > 4 else "private")
