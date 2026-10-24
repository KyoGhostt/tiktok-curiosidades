"""Publicador: TikTok Content Posting API (OAuth). Enquanto o app não for auditado, posta como privado."""
import os, requests

TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")


def publish(video, caption):
    if not TOKEN:
        return "sem TIKTOK_ACCESS_TOKEN: vídeo só salvo (modo rascunho)"
    size = os.path.getsize(video)
    init = requests.post("https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json; charset=UTF-8"},
        json={"post_info": {"title": caption[:2000], "privacy_level": os.environ.get("TIKTOK_PRIVACY", "SELF_ONLY"),
                            "is_aigc": True},
              "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}},
        timeout=60)
    init.raise_for_status()
    d = init.json()["data"]
    up = requests.put(d["upload_url"], data=open(video, "rb").read(), timeout=300, headers={
        "Content-Type": "video/mp4", "Content-Range": f"bytes 0-{size-1}/{size}"})
    up.raise_for_status()
    return f"enviado, publish_id={d['publish_id']}"
