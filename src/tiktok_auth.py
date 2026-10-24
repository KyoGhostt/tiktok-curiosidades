"""Troca o código de autorização por tokens e guarda no cofre. Nunca imprime segredos."""
import os, sys, time, requests, tokens

URL = "https://open.tiktokapis.com/v2/oauth/token/"


def main():
    r = requests.post(URL, data={
        "client_key": os.environ["TIKTOK_CLIENT_KEY"], "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
        "code": os.environ["CODE"].strip(), "grant_type": "authorization_code",
        "redirect_uri": os.environ["REDIRECT_URI"]}, headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=30)
    d = r.json()
    if "access_token" not in d:
        print("ERRO TikTok:", d.get("error"), d.get("error_description"))
        sys.exit(1)
    tokens.save({"access_token": d["access_token"], "refresh_token": d["refresh_token"],
                 "expires_at": time.time() + d.get("expires_in", 86400),
                 "refresh_expires_at": time.time() + d.get("refresh_expires_in", 31536000),
                 "open_id": d.get("open_id"), "scope": d.get("scope")})
    print("OK: autorizado, escopos:", d.get("scope"), "| tokens salvos no cofre privado")


if __name__ == "__main__":
    main()
