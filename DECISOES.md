# DECISÕES — o que foi escolhido e por quê (para não rediscutir)
Só leia quando for mudar algo parecido. Estado atual está em STATUS.md.

## Custo e infraestrutura
- Tudo grátis: GitHub Actions, LLM Gemini/Groq, voz edge-tts, Buffer grátis (limite de 10 agendados por canal). Hugging Face não é necessário na biblioteca de fundos.
- vidIQ no plano grátis (150 créditos/mês, busca de outliers = 5 créditos): só nas sessões do Claude, ~1x por semana.
- Sessões do Claude são o recurso escasso do dono (conta grátis): o robô deve rodar sozinho no Actions; o Claude entra só para mudar ou consertar.

## Conteúdo
- Histórias reais da comunidade (Reddit) têm prioridade; IA só cria história original se faltar relato. Polêmicas e com plot que prenda (30/10).
- Todo vídeo tem 5:00 (pedido do dono, 31/10). O número de partes vem do tamanho do relato.
- PPM medido em 31/10: ~198 palavras por minuto (antes se supunha 240); por isso PPM=200.
- Legenda sem "Continua", sem abertura "Gente", sem "Baseado em relato do Reddit". TTS limpa asteriscos.
- Uma voz por história, escolhida pelo gênero do narrador (`genero_narrador`: Antonio ou Francisca).
- Sem crédito aos canais de gameplay nas legendas (decisão do dono; o pedido deles não é exigência).

## Fundos de vídeo
- Pixabay descartado como fundo: não tem gameplay.
- YouTube bloqueia o GitHub Actions ("confirme que você não é um robô") e Piped/Invidious/cobalt também. Por isso a biblioteca: baixar UMA vez, guardar no release `fundos` e nunca mais depender do YouTube.
- Só entra fundo vertical, sem placar, menu, anúncio ou webcam (risco de strike). Cada arquivo passa por conferência de quadros antes de entrar em `fundos/aprovados.txt`.
- GTA só de parkour de carro, sem violência. Minecraft tem peso 0,5 no sorteio porque já há muitos vídeos dele no ar (31/10).
- Internet Archive funciona no Actions (Minecraft Automate Socials, licença livre; Subway CC0).
- vidIQ trim_media baixa só 144p (inútil) e generate_clips falha em vídeo sem fala.

## Fontes de histórias
- Reddit via RSS. Bloqueados no Actions: Arctic Shift, PullPush, old.reddit, reddit json, espelhos (redlib, safereddit, opnxng), TikTok Creative Center.
- Por isso o banco: `banco.yml` guarda relatos de 2 em 2 h, para a geração não depender de acertar o Reddit na hora.
- Plano B se o RSS piorar: chave oficial do Reddit (reddit.com/prefs/apps, tipo script). Reserva: Lemmy (pequeno).

## Postagem e otimização
- Horários e hashtags testados pelo otimizador só valem para vídeos novos; posts já agendados NUNCA mudam.
- Horário: testa 1 h antes ou depois, um por vez; troca se render +15% de views (precisa de 3 posts maduros, com +36 h).
- Hashtag candidata só entra se aparece no YouTube E no Google.
- Áudio de cada vídeo: 48 kHz estéreo + ruído rosa bem baixo e único (29/10), para evitar o falso positivo "Este som está indisponível" do TikTok.

## Multi-idioma
- Estado e vídeos separados por idioma; PT na raiz, inalterado. O limite de 10 agendados é por canal.
- EN e ES só começam a postar quando o dono mandar. ES tem poucos relatos longos; se faltar, cria original.

## Como o Claude deve trabalhar neste repo
- Ler INDEX.md e STATUS.md primeiro. Perguntar antes de alterar e dizer sempre como reverter.
- No fim de cada bloco de trabalho, atualizar o STATUS.md só com o que mudou (até ~10 linhas).
- 07/11: YouTube = Shorts via Buffer (auto) + video completo via Zap do GitHub Release (API direta trava em privado sem auditoria). Dono quer tudo automatico.
