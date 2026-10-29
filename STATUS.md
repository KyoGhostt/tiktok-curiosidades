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
  vertical, SÓ o item `subway-surfers-2024-gameplay-4-k-9x-16-no-copyright-1` (CC0, 193 s, tela limpa sem HUD; conferido). Os outros itens
  (vcompress_*, recorder_*) têm placar/menus/anúncios na tela: descartados (risco de strike). Subway usa cores mais calmas (calmo=True);
  se uma fonte cair, usa a outra. `MC_JOGO=minecraft|subway` força um. Amostra: workflow `fundos-jogos`.
- Roblox/GTA V no Archive só existem em 16:9, com webcam/menus na tela (o usuário quer GTA só de parkour de carro, sem violência): não usados. Precisa de clipe vertical limpo vindo do usuário.

## Biblioteca de fundos (29/10) — PRONTA, falta o cookie
- Ideia: baixar UMA vez os vídeos do YouTube (Subway, GTA parkour de carro, Roblox, Minecraft) e guardar no release `fundos` do repo;
  o robô nunca mais depende do YouTube. Se o cookie vencer depois, nada quebra (só não entram vídeos novos).
- Fluxo: lista em `fundos/links.txt` (`jogo|link`, só verticais) -> workflow `biblioteca` (usa secret `YT_COOKIES`, formato cookies.txt)
  -> padroniza 1080x1920 sem áudio (máx. 20 min) -> guarda no release + quadros de conferência no branch `previews`
  -> depois de conferir (sem placar/menus/webcam) o arquivo entra em `fundos/aprovados.txt` -> `mc.pick_biblioteca()` passa a sorteá-lo.
- `fundos/links.txt` já tem 12 links verticais achados pelo vidIQ (GTA mega ramp e Roblox/Minecraft do canal OrbitalNCG/Orbital, Roblox Glide Tower da Bloxu, Subway). Decisão do dono: sem crédito dos canais nas legendas (o pedido deles não é exigência).
- Alternativa sem cookie: o dono sobe os MP4 direto na página do release `fundos` no github.com (até 2 GB por arquivo, sem limite total prático) com nome `raw_<jogo>_<id>.mp4`; workflow `biblioteca` com `normalizar=sim` converte (1080x1920, sem áudio, máx. 20 min, ~300 MB/10 min), gera quadros de conferência e apaga o raw. Hugging Face não é necessário.
- vidIQ trim_media baixa só 144p (testado 29/10): inútil. generate_clips falha em vídeo sem fala.
- Pendente: usuário criar o secret YT_COOKIES (conta secundária) e rodar o workflow `biblioteca`; depois conferir quadros e preencher `fundos/aprovados.txt`.

## vidIQ (conectado em 29/10, plano grátis: 150 créditos/mês; busca de outliers TikTok/IG = 5 créditos)
- Só funciona nas sessões do Claude (não roda no Actions). Uso manual, ~1x/semana, para achar hashtags/temas que bombam no TikTok BR.
- Achado 29/10: #historiasdetiktok (2 mi de views), séries "Pt.2" e histórias de chefe/trabalho (#trabalho) vão bem no Brasil; vídeos de 87-233 s também.
  `#historiasdetiktok` entrou no teste de hashtags (`otimo.GLOBAIS`).

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

- 29/10: parte 3 de 'Meu marido esqueceu...' ficou 'Este som está indisponível' no TikTok (só ela; as outras estão ok). Arquivo tinha áudio normal -> provável falso positivo do TikTok no áudio. Mitigação em video._final: áudio 48 kHz estéreo + ruído rosa bem baixo (único por vídeo). Parte 3 corrigida enviada ao dono para repostar; parte 4 (já no Buffer) mantém áudio antigo.
