# Curioso em Alta — histórias do Reddit no TikTok (100% automático e grátis)

Canal **@curiosoemalta.br**. O GitHub Actions gera histórias do Reddit adaptadas para PT-BR, em vídeos de 5:00, e o Buffer posta sozinho no TikTok (3 por dia, 12h / 17h / 20h de Brasília, sem domingo).

```
Reddit (RSS) → banco de relatos → LLM (Gemini/Groq) adapta p/ PT-BR em 1 a 5 partes → voz (edge-tts) → vídeo 9:16 (FFmpeg + fundo + legenda karaokê)
→ revisor → branch `media` (link público) → Buffer agenda → TikTok
                                          └→ monitor avisa no Telegram: postado, erro, fila vazia, chave vencendo
```

**Começando por aqui:** `INDEX.md` (mapa) → `STATUS.md` (estado atual) → `DECISOES.md` (por quê). A lista de workflows e como reverter mudanças estão no `STATUS.md`.

## Secrets (Settings → Secrets → Actions)
- `GEMINI_API_KEY` e/ou `GROQ_API_KEY` — LLM grátis
- `PIXABAY_API_KEY` — usado em partes auxiliares do código
- `BUFFER_API_KEY` — chave do Buffer (**vence em 1 ano**; ao trocar, atualize `BUFFER_KEY_CREATED` em `monitor.yml`)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — avisos
- `YT_COOKIES` — opcional, só para a biblioteca de fundos via YouTube

## Branches de apoio
`media` (vídeos do Buffer), `estado` (fila, otimização, banco de histórias) e `previews` (quadros de conferência).
