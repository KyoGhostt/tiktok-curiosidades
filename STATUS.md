# STATUS — Curioso em Alta (leia SÓ este arquivo ao retomar o trabalho)
Atualizado: 03/11/2026 (conferido contra o código). Detalhes antigos: HISTORICO.md. Motivos das escolhas: DECISOES.md.

## Estado atual (canal PT @curiosoemalta.br)
- 3 vídeos por dia, 12h / 17h / 20h (Brasília). Domingo é folga, sem vídeo (`src/schedule.py`).
- Todo vídeo tem 5:00. Uma história vira de 1 a 5 partes conforme o tamanho do relato (`story.plano`); título "Parte X de N".
- Uma voz por história: Antonio (M) ou Francisca (F), edge-tts, PPM=200 (ainda sem validar numa geração nova).
- Fundo sorteado por história: Minecraft (peso 0,5), GTA mega ramp (3 clipes) e Subway Surfers (3 clipes) da biblioteca em `fundos/aprovados.txt`. GTA e Subway usam cores calmas.
- Histórias: relatos reais do Reddit (12 comunidades) acumulados por `banco.yml`; se faltar, o robô cria uma original.
- Buffer grátis: no máximo 10 agendados por canal. O Telegram avisa postado, erro, fila vazia e chave perto de vencer.
- Horário (12/17/20) e hashtags são testados pelo otimizador, mas só valem para vídeos novos; o que já está agendado nunca muda.

## Workflows (horários de Brasília)
| Arquivo | Quando | Para quê |
|---|---|---|
| `gerar-semana.yml` | domingo e quarta, 06h (ou manual) | repõe o estoque (padrão 18 partes = 1 semana sem domingo) |
| `fila.yml` | a cada 3 h (ou manual: `acao` = retomar, pausar, estado) | completa o Buffer na ordem das partes |
| `banco.yml` | a cada 2 h | pede feeds ao Reddit com espera e guarda relatos em `estado/<idioma>/banco.json` (máx. 120) |
| `monitor.yml` | 06h30, 12h30, 18h30, 21h30 | avisos no Telegram |
| `otimizar.yml` | todo dia 09h30 (ou manual: rodar, simular, schema, fontes) | lê views no Buffer, testa horários e hashtags |
| `biblioteca.yml` | manual | traz fundos novos: `drive=<link> nome=<jogo>`, `normalizar=conferir` (quadros) ou `amostra:<prefixo>` |
Os demais (`fundos-*`, `fontes-reddit`, `sondar-subs`, `voz-*`, `vozes`, `legendas-limpar`, `telegram-conectar`) são testes e manutenção, rodam só manual.

## Branches
`media` (vídeos, limpa o que foi postado há mais de 1 h), `estado` (fila.json, otimizacao.json, banco.json), `previews` (quadros de conferência).

## 13/11: US (en) REATIVADO (canal curioustrending no Buffer). YouTube DESLIGADO (fora do Buffer): gerar-semana sem YT_SHORT/YT_COMPLETO/agendar, yt-diario sem cron. Reativar YT: ver comentarios nesses arquivos.
## Canais EN e ES (código pronto; ES e EN rodando)
- `src/lang.py` (LANG_CODE = pt | en | es). EN: canal `curioustrending`, ET 12h/18h/21h, PPM 175. ES: `curiosoenalza`, Cidade do México 12h/18h/21h, PPM 200.
- Estado separado por idioma em `en/` e `es/`; PT continua na raiz e não depende de LANG_CODE.
- O cron NÃO inclui en/es. Só ligar quando o dono mandar. Há 1 vídeo de teste de cada idioma no estoque, aguardando aprovação.
- Nomes ainda em decisão: Curious Trending vs Trending Curiosity; Curioso en Alza vs Tendencia.

## Como reverter (git revert <commit> e push, ou pedir ao Claude)
- Roteiro com pergunta central e capa com título: 402f366 e bd0287e (só vale para histórias geradas depois).
- Escolha de histórias (12 comunidades, top + controversial): c9237cf e e633d17.
- Multi-idioma: commits "Multi-idioma ...". Banco de histórias: apagar `banco.yml` e as linhas `_banco()` de `story.py`.
- Tirar um fundo do sorteio: apagar a linha dele em `fundos/aprovados.txt`.

## Pendências
- Decidir: apagar o estoque antigo (vídeos de 1–2 min) e regenerar em 5 min; filtro de temas sensíveis.
- Validar PPM=200 numa geração nova; conferir no TikTok se a capa (quadro em 1,5 s) foi respeitada.
- Áudio mudo no TikTok: causa desconhecida; o dono avisa se repetir (plano B: mudar o timbre da voz).
- Dono vai subir zips do Drive (slime, sabonete, Roblox, mais Subway/GTA): rodar `biblioteca`, conferir quadros, aprovar.
- Desativar o GitHub Pages (o workflow "pages build" falha). Ação do dono.
- Chave do Buffer vence ~25/10/2027: ao trocar, atualizar `BUFFER_KEY_CREATED` em `monitor.yml`.
- vidIQ (plano grátis, 150 créditos/mês) só roda nas sessões do Claude; uso manual, ~1x por semana.

## 07/11 — Canal US (EN) DESATIVADO
- Motivo: usuario troca o canal US do Buffer pelo YouTube. Codigo EN (src/lang.py etc.) intacto.
- Removido "en" de: banco.yml, fila.yml, gerar-semana.yml (padrao "todos"), monitor.yml.
- Reativar: voltar a incluir "en" nesses 4 workflows (ou rodar manualmente com lang=en) + reconectar TikTok US no Buffer.
- Proximo: conectar YouTube no Buffer (Shorts auto; longos manual), confirmar ID do canal.

## 07/11 — YouTube (canal curiosoemalta, Buffer id 6aeeb178e29c69a1718e4a04)
- Canal US (EN) desativado nos workflows (reativar: incluir "en" em banco/fila/gerar-semana/monitor).
- Shorts (<=3 min, vertical): Buffer YouTube; src/yt_short.py faz resumo ~90 s por historia -> release yts-<id> -> agenda 18h/21h seg-sab. Teste em yt-teste.yml.
- Video completo (16:9, <=105 MB): src/yt_longo.py; fica em release RASCUNHO yt-<id> (max 7); yt-diario.yml publica 1/dia 12h seg-sab; ZAP do usuario (GitHub New Release -> YouTube Upload Video, Public) envia.
- Upload direto pela API do Google fica PRIVADO/travado ate auditoria (secrets YT_* existem, token expira em 7 dias em modo Teste): nao usar.
- Zapier MCP: YouTube conectado (so executa na sessao; nao cria Zaps).

## 09/11 — Duracao e roteiro (analise por comunidade)
- Dados (Buffer): BR ~1 min = 44% visto, ~585 views; 5:00 = ~15% visto; ES 5:00 = 8% visto, ~190 views. Gente sai em 25-50 s.
- Fim do 5:00 fixo: cada historia sorteia 1:30/2:00/2:30 (lang.py alvo_opcoes, POR comunidade; ALVO_MIN no ambiente forca). Comparar retencao por duracao e por comunidade (BR, ES, US sempre separados).
- Roteiro: toda parte >=2 abre com mini-resumo; gancho a cada ~100 palavras; final com pergunta polemica. Historias de trabalho/chefe/vinganca/relacionamento vem primeiro (_PREF em story.py).
- Reverter: git revert do commit "Duracao 1:30-2:30..." (volta ao 5:00).
- CEREBRO v2 (09/11): cerebro.py + cerebro.yml (diario coleta; SO muda pesos aos domingos, passo max 15 pts). Avalia historia inteira (todas as partes, 7+ dias) com views, retencao, curtidas, comentarios, compartilhamentos. Saida na branch `analises` (<lang>/RELATORIO.md, cerebro.json, historias.json) - Claude le com git fetch origin analises. story.py le CEREBRO_DIR. Desligar: apagar cerebro.yml.
