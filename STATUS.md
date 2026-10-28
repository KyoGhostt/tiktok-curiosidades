# STATUS do projeto (leia isto primeiro ao retomar o trabalho)
Atualizado: 28/10/2026

## Como funciona hoje
- `gerar-semana.yml` (domingo 06h Brasília, ou manual): gera histórias de 3 a 6 partes (≤ ~80 s cada) com fundo de Minecraft parkour
  e capa em cartão, até ter 21 partes em estoque. Vídeos vão para o branch `media`, o manifesto `fila.json` para o branch `estado`.
- `fila.yml` (a cada 6 h, ou manual com `acao`): completa o Buffer (limite grátis = 10 agendados; usamos 9) na ordem das partes,
  nos horários 12h/17h/20h (Brasília). `acao=retomar` despausa; `pausar` pausa; `estado` mostra a fila nas anotações.
- `monitor.yml` (12h30/18h30/21h30): avisa no Telegram (postado, erro, fila vazia, chave do Buffer perto de vencer).
- Títulos: "Parte X de N" (sem horários). O fundo continua de onde a parte anterior parou.

## Feito
- Buffer conectado (canal TikTok curiosoemalta); chave no secret BUFFER_API_KEY (vence ~25/10/2027; atualizar BUFFER_KEY_CREATED no monitor.yml).
- Telegram conectado (avisos). Fundos de Minecraft vertical (Automate Socials, licença livre) baixados e usados.
- 28/10: fila estava PAUSADA por engano (2 dias sem posts); retomada e Buffer reabastecido com 9 partes (até 31/10).

- 28/10: legendas sem "Baseado em relato do Reddit" (código, estoque e 9 posts do Buffer). gerar-semana agora roda domingo e quarta.

## Pendente / ideias
- Fundos de YouTube (GTA V, Roblox, Subway Surfers): TESTADO em 28/10: o YouTube bloqueia o GitHub Actions ("Sign in to confirm you're not a bot"), yt-dlp não funciona sem cookies. Caminho alternativo: usuário baixa os clipes e sobe num dataset do Hugging Face (upload pelo navegador aceita arquivos grandes); o código baixa de lá.
- Conferir no TikTok se a capa (quadro em 1,5 s) foi respeitada.
- Fundo "slime/ASMR" não existe no Pixabay; opção futura: o usuário sobe clipes.
- Workflow "pages build" falha (docs removidos); pode desativar o GitHub Pages.
