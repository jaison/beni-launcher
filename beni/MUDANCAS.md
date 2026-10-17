# Mudanças em relação ao Cozy Kids Launcher 0.6.0

Base: [TrissyGE/cozy-kids-launcher](https://github.com/TrissyGE/cozy-kids-launcher), commit `91b7157`
(02/09/2026). Para ver o diff completo: `git diff 91b7157 -- src scripts tests`.

> Os arquivos `src/index.html`, `src/frontend/state.js` e outros com textos eram **modelos**
> (`{{JSON_ADMIN_TITLE}}`…) que o `scripts/install.sh` preenchia. Aqui eles foram copiados da
> instalação real, já preenchidos e traduzidos. Por isso o diff desses arquivos é grande, mesmo
> quando a lógica mudou pouco.

## Arquivos novos (`src/`)
| Arquivo | Para quê |
|---|---|
| `usage_limits.py` | Limite diário por perfil e por categoria (`jogos`, `educativo`, …). Conta o tempo só com o app aberto, grava em `~/.local/state/cozy-kids-launcher/usage-today.json`, zera à meia-noite, bloqueia tiles e fecha o app que passar do limite. |
| `frontend/usage-limits.js` / `.css` | Medidores na barra de baixo, mensagens de "tempo acabou" e painel em Pais → Tempo de tela. |
| `frontend/escolha.js` / `.css` | Tela inicial "O que você quer fazer? Aprender / Jogar" e lista filtrada por categoria. |
| `frontend/cozy-temas.css` | Temas heroi, blocos, ninja, gelo, casinha e castelo; estilos da prévia; capas de jogos nos tiles. |
| `frontend/locales/pt.json` | Português do Brasil (todas as 237 chaves do inglês). |
| `../themes/*.svg`, `../themes/fonts/` | Fundos dos temas novos e fontes (OFL). |

## Arquivos alterados (`src/`)
| Arquivo | Mudança |
|---|---|
| `server.py` | Junta os bloqueios por horário com os bloqueios por limite (motivos `category_limit` e `daily_limit`, campo `limitBlocked`); endpoints `GET /api/usage/status` e `POST /api/usage/reset`; liga o contador ao abrir um tile; idioma `pt`. |
| `config_validation.py`, `profile_config.py` | Aceitam `tile.category`, `profile.categoryLimits`, `profile.choiceScreenEnabled` e o idioma `pt`. |
| `overlay.py` | Tempo restante da categoria ao lado do ❌ (com cores), contagem grande nos últimos 10 s, fechamento no 0; reposiciona a janela via X11 quando o jogo a joga para 0,0; textos em pt. |
| `timer_watchdog.py`, `browser.html`, `media.html`, `no-media.html` | Textos em pt. O `browser.html` tinha um erro de JS de origem (`'Time's up!'`), corrigido com a tradução. |
| `speech_feedback.py` | Voz em português (`spd-say -l pt-BR` / `espeak-ng -v pt-br`). |
| `recommendations.json` | Campos `label_pt`, `name_pt`, `desc_pt`, `hint_pt`. |
| `frontend/icons.js` | `createTileVisual` aceita `img:covers/arquivo.png` (capa de jogo no lugar do emoji). |
| `frontend/launcher-ui.js` | Lista filtrada pela categoria escolhida; clique em tile bloqueado por limite; nomes dos temas novos e em pt. |
| `frontend/theme-runtime.js` | Registra os 6 temas novos como "mundos ilustrados". |
| `frontend/runtime-controls.js` | Teclado na tela de escolha; Esc na lista volta para a escolha; Esc com a mensagem de "tempo acabou" aberta só fecha a mensagem (antes saía do modo infantil). |
| `frontend/parent-settings.js` | Painel dos limites; opção "Tela inicial"; recomendações em pt; botão Desligar aparece já no carregamento. |
| `frontend/schedule-controls.js` | Repassa os motivos de bloqueio por limite; não mostra `img:…` cru no seletor. |
| `frontend/state.js`, `localization.js`, `profiles.js`, `first-run.js`, `activity-dashboard.js`, `media-library.js` | Suporte ao idioma `pt` (textos de perfis, datas pt-BR, opção 🇧🇷 no primeiro uso). |
| `index.html` | Textos em pt; links dos CSS/JS novos; botão Voltar e selo de tempo; quadros "Limite diário por categoria" e "Tela inicial". |

## `scripts/` e `tests/`
- `scripts/install.sh`: também copia `usage_limits.py`, `pt.json` e os CSS/JS novos.
- `tests/test_server.py`: 2 asserções ajustadas (texto já traduzido; campo `limitBlocked`).
- `tests/test_overlay.py` passa sem mudança. O `overlay.py` só pede `XMoveWindow` ao X11 quando vai usar.

## Fora do launcher (`beni/`)
| Pasta/arquivo | Instalado em | Para quê |
|---|---|---|
| `bin/cozy-kids-launcher` | `~/.local/bin` | Script de início do launcher, já preenchido (porta 38431, Firefox em modo quiosque). |
| `bin/cozy-iniciar` | `~/.local/bin` | Usado no login: espera a rede, sincroniza o itch.io e abre o launcher. |
| `bin/cozy-itch-sync` | `~/.local/bin` + timer systemd | Coleções do itch.io → tiles `itch-*` com capa, tamanho do jogo e corte da faixa do Unity. |
| `bin/navegador-jogos` | `~/.local/bin` | Chromium em modo quiosque com aceleração, pt-BR, sem barra de tradução, mais a tela "Carregando…". |
| `bin/cozy-fullscreen` | `~/.local/bin` | Põe em tela cheia apps que abrem em janela (`wmctrl`). |
| `bin/cozy-jogos` | `~/.local/bin` | Abre a lista de jogos SNES/PS1. |
| `bin/gcompris`, `tuxpaint`, `turbowarp`, `luanti`, `klavaro`, `klotski` | `~/.local/bin` | Abrem as versões do Flathub em tela cheia (GCompris só com atividades de nível 3–6). |
| `bin/tuxmath`, `pingus`, `hex-a-hop`, `supertux`, `frogatto` | `~/.local/bin` | Tela cheia na resolução atual + `nograb.so`. |
| `bin/supertuxkart` | `~/.local/bin` | Força a resolução atual na configuração do jogo (evita a tela apagada). |
| `bin/planetario` | `~/.local/bin` | Stellarium em tela cheia. |
| `lib/cozy-fixes/nograb.c` | `~/.local/lib/cozy-fixes/nograb.so` | Anula `SDL_WM_GrabInput` (SDL 1.2) e `SDL_SetWindowGrab`/`MouseGrab` (SDL2, também via `dlsym`). |
| `lib/cozy-fixes/carregando.py` | `~/.local/lib/cozy-fixes` | Tela "Carregando…" até o navegador estar em tela cheia. |
| `cozy-jogos/jogos.py` | `~/.local/share/cozy-jogos` | Lista de jogos SNES/PS1 em Tk, com capas, teclado, mouse e controle. |
| `chromium/cozy-jogo.html` | `~/.var/app/org.chromium.Chromium` | Moldura que amplia jogos de tamanho fixo (`#w=&h=&fh=&u=`). |
| `emuladores/retroarch.cfg` | `~/.config/cozy-jogos` | RetroArch sem menu, sem prender o mouse, sem trocar a resolução, Esc sai. |
| `emuladores/gpuPeopsMesaGL.cfg` | `~/.pcsxr/plugins` | Vídeo OpenGL do PCSX-R (o DFXVideo não funciona com o driver modesetting). |
| `emuladores/luanti-minetest.conf` | `~/.var/app/org.luanti.luanti/.minetest` | Luanti leve (distância de visão curta, sem sombras). |
| `config/config.json` | `~/.config/cozy-kids-launcher` (se não existir) | Dois perfis com apps, categorias, temas e limites 60/30/30. |
| `config/itch-colecoes.json` | idem | Perfil → coleção pública do itch.io. |
| `systemd/cozy-itch-sync.{service,timer}` | `~/.config/systemd/user` | Sincronização a cada 30 min. |
| `ferramentas/gerar-temas*.py` | — | Geram os SVG dos temas (Python puro). |

## Ajustes do sistema feitos pelo `instalar.sh`
- `python3-tk`, `wmctrl`, `xdotool` e os apps/emuladores (apt e Flathub).
- XFCE: remove os atalhos Ctrl+Alt+Del e Ctrl+Alt+L (bloqueio); desliga o bloqueio ao suspender, ao fechar a sessão e depois do protetor de tela (light-locker); deixa os painéis em "esconder sempre".
- Firefox do launcher: `accessibility.browsewithcaret` desligado (era a linha vertical piscando).
- Autostart `~/.config/autostart/cozy-kids-launcher-autostart.desktop` → `cozy-iniciar`.
