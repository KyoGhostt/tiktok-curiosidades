# TikTok Curiosidades (PT-BR) - pipeline automático e gratuito
Scout (Wikipedia) -> Roteirista (LLM via Hugging Face) -> Voz (edge-tts) -> Vídeo (FFmpeg + Pexels) -> Revisor -> Publicador (TikTok API).
Roda 2x/dia pelo GitHub Actions. Se falhar, abre uma Issue.

Secrets necessários (Settings > Secrets > Actions):
- HF_TOKEN (obrigatório, token "read" do Hugging Face)
- PEXELS_API_KEY (opcional, grátis em pexels.com/api; sem ele usa fundo gradiente)
- TIKTOK_ACCESS_TOKEN (depois do OAuth; sem ele os vídeos ficam só como artefato)
