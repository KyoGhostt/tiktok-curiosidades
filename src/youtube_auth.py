"""Troca o código do Google por tokens (refresh token) e guarda no cofre privado. Nunca imprime segredos."""
import os, sys, time, requests, tokens


def main():
    r = requests.post("https://oauth2.googleapis.com/token", timeout=30, data={
        "client_id": os.environ["GOOGLE_CLIENT_ID"], "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "code": os.environ["CODE"].strip(), "grant_type": "authorization_code", "redirect_uri": os.environ["REDIRECT_URI"]})
    d = r.json()
    if "refresh_token" not in d:
        print("ERRO Google:", d.get("error"), d.get("error_description"), "| (sem refresh_token: refaça com prompt=consent)")
        sys.exit(1)
    tokens.save({"access_token": d["access_token"], "refresh_token": d["refresh_token"],
                 "expires_at": time.time() + d.get("expires_in", 3600), "scope": d.get("scope")}, "youtube.json")
    print("OK: YouTube autorizado, escopo:", d.get("scope"))


if __name__ == "__main__":
    main()
