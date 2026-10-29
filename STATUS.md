# STATUS do projeto (leia isto primeiro ao retomar o trabalho)
Atualizado: 28/10/2026

## Como funciona hoje
- `gerar-semana.yml` (domingo 06h Brasília, ou manual): gera histórias de 3 a 6 partes (≤ ~80 s cada) com fundo de Minecraft parkour
  e capa em cartão, até ter 21 partes em estoque. Vídeos vão para o branch `media`, o manifesto `fila.json` para o branch `estado`.
- `fila.yml` (a cada 6 h, ou manual com `acao`): completa o Buffer (limite grátis = 10 agendados) na ordem das partes,
  nos horários 12h/17h/20h (Brasília). `acao=retomar` despausa; `pausar` pausa; `estado` mostra a fila nas anotações.
- `monitor.yml` (12h30/18h30/21h30): avisa no Telegram (postado, erro, fila vazia, chave do Buffer perto de vencer).
- Títulos: "Parte X de N" (sem horários). O fundo continua de onde a parte anterior parou.

## Otimizador diário (`otimizar.yml`, todo dia 09h30 Brasília, ou manual: rodar | simular | schema | fontes)
- Lê o desempenho real dos posts no Buffer (views, só posts com +36 h) e pesquisa na web (Google Trends BR, autocompletar YouTube/Google).
  TikTok Creative Center (hashtags em alta) e Reddit RSS bloqueiam o Actions: indisponíveis.
- Horários: testa 1 h antes/depois de um dos 3 horários por vez (precisa de 3 posts maduros por horário; troca se render +15% views).
  Vale SÓ para os próximos vídeos; posts já agendados no Buffer NUNCA mudam de horário.
- Hashtags: 5 por post (#parteN + #historiasdoreddit + 3 variáveis por tema). Reordena pelas que mais deram views + explora novas
  (candidatas da pesquisa só entram se aparecem no YouTube E no Google). Só reescreve legenda/hashtags dos posts agendados.
- Estado em branch `estado`: `otimizacao.json` (horários, hashtags, histórico), `otimizar-log.txt` (último relatório). Relatório no Telegram.
- Código: `src/otimo.py` (config lida por schedule/fila/main_story), `src/otimizar.py`, `src/fontes.py`.

## Fundos de jogos (29/10)
- Pixabay descartado (não tem gameplay). YouTube bloqueado no Actions; Piped/Invidious/cobalt também (403/auth).
- Internet Archive funciona no Actions: `src/mc.py` agora sorteia por história entre Minecraft (Automate Socials) e Subway Surfers
  vertical (itens `subway-surfers-2024-gameplay-4-k-9x-16-no-copyright-1` (CC0), `vcompress_452`, `vcompress_144`, `recorder-18052024-072057`);
  se uma fonte cair, usa a outra. `MC_JOGO=minecraft|subway` força um. Amostra: workflow `fundos-jogos`.
- Roblox/GTA V no Archive só existem em 16:9 (horizontal) e GTA é violento: não usados (cortar perderia qualidade).

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
