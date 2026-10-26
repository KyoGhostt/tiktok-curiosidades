# Curioso em Alta — histórias do Reddit no TikTok (100% automático e grátis)

Canal **@curiosoemalta.br**. Todo dia o GitHub Actions gera 1 história dividida em 3 vídeos e o Buffer posta sozinho no TikTok.

```
Reddit (RSS) → LLM (Gemini/Groq) adapta p/ PT-BR em 3 partes → voz (edge-tts) → vídeo 9:16 (FFmpeg + Pixabay + legenda karaokê)
→ revisor → branch `media` (link público) → Buffer agenda 12h / 18h / 21h (Brasília) → TikTok
                                                       └→ monitor avisa no Telegram: postado, erro, fila vazia, chave vencendo
```

## Workflows
| Arquivo | Quando | O que faz |
|---|---|---|
| `daily.yml` | todo dia 06h (Brasília) | gera a história, publica os vídeos na branch `media` e agenda no Buffer; avisa no Telegram se falhar |
| `monitor.yml` | 12h30, 18h30, 21h30 | confere o Buffer e avisa no Telegram (✅ postado, ❌ erro, 📭 fila vazia, 🔑 chave perto de vencer) |
| `telegram-conectar.yml` | manual | descobre o chat id do Telegram |

## Secrets (Settings → Secrets → Actions)
- `GEMINI_API_KEY` e/ou `GROQ_API_KEY` — LLM grátis
- `PIXABAY_API_KEY` — vídeos de fundo
- `BUFFER_API_KEY` — chave do Buffer (**vence em 1 ano**; ao trocar, atualize `BUFFER_KEY_CREATED` em `monitor.yml`)
- `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` — avisos

## Branches de apoio
`media` (vídeos do Buffer, apagados após 4 dias) e `previews` (histórico, prévia e agenda).
