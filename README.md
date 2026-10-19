# Beni Launcher

**Um computador para crianças que equilibra aprender e brincar.** É um menu em tela cheia para
notebooks antigos com Linux, pensado para crianças de 5 a 10 anos. A criança só encontra o que
os pais aprovaram. O tempo de tela é controlado por categoria, e o tempo de jogo depende de ela
ter feito a parte de aprendizado.

Ao ligar o notebook, a criança vê **"O que você quer fazer? 📚 Aprender / 🎨 Passatempo / 🎮 Jogar"**.
Cada cartão mostra quanto tempo ainda resta hoje.

![Tela inicial](beni/prints/01-escolha-beni.png)

### Por que este projeto existe

> Eu sou o **Jaison**. Eu queria dar vida nova a um notebook antigo, de 2011, para o meu
> sobrinho **Benício** (o Beni), e transformar uma máquina que ia ficar parada num computador
> que ele pudesse usar sozinho, com segurança.
>
> A premissa era simples:
> - **Teclado e mouse**, como um computador de verdade, e não um tablet. Ele aprende a usar o computador enquanto brinca.
> - **Programas, sites e jogos escolhidos por mim.** Nada de navegar solto: só o que foi testado e aprovado aparece na tela.
> - **Segurança na internet**, com um DNS que bloqueia sites inadequados em qualquer rede, além de Busca Segura e YouTube restrito.
> - **Liga e já funciona.** O notebook entra direto no menu das crianças, sem senha, sem área de trabalho e sem configurar nada.
> - **Logins automáticos.** Ele não precisa decorar e-mail e senha para entrar no Khan Academy ou no Teach Your Monster.
> - **Regras de tempo.** Tempo certo para aprender, para passatempos e para jogar. E o tempo de jogo depende de ele ter feito a parte de aprender.
>
> No caminho, o projeto ganhou um segundo perfil, da minha sobrinha **Bea**, de 5 anos. Para ela
> vieram jogos mais voltados para meninas (vestir, maquiagem, bonecas, cozinhar) e temas próprios
> (Reino do Gelo, Casinha Mágica e Castelo Encantado). Vieram também emuladores e muitas
> correções para hardware antigo. Está tudo aqui, para quem quiser fazer o mesmo com um notebook
> esquecido na gaveta.

### Os quatro pilares

| | |
|---|---|
| ⏳ **Tempo de tela por categoria** | Minutos por dia para Aprender, Passatempo e Jogar, diferentes em cada dia da semana se quiser (mais jogo no fim de semana). O tempo só conta com o app aberto, sobrevive a reinícios e zera à meia-noite. |
| 📚 **Reforço obrigatório de aprendizagem** | Se ontem a criança não cumpriu a meta de Aprender, hoje o Jogar fica menor. Ex.: ontem 0/30 min de Aprender → hoje 15 min de Jogar em vez de 30. Os pais escolhem a meta e o tamanho da redução. |
| 🔑 **Login automático nos sites** | Os pais salvam uma vez o e-mail e a senha da conta de cada criança (Khan Academy, Teach Your Monster). Ao abrir o site, o launcher entra sozinho. Cada criança tem o seu navegador, então as contas não se misturam. |
| 🛡️ **Internet e conteúdo seguros** | DNS com filtro para crianças em qualquer Wi‑Fi, Busca Segura e YouTube restrito obrigatórios, bloqueador de anúncios e sites "limpos" (sem menus de jogos, propagandas ou links para fora). |

> **Base:** este projeto nasceu do [Cozy Kids Launcher](https://github.com/TrissyGE/cozy-kids-launcher)
> (Tristan e colaboradores, licença MIT), versão **0.6.0** (commit `91b7157`). O núcleo vem de lá:
> servidor local, supervisão dos apps, ❌ por cima dos jogos, perfis, PIN dos pais e horários.
> O histórico original foi mantido. Hoje o projeto está bem diferente: tem tela de categorias,
> limites, reforço de aprendizado, login automático, filtro de internet, apps e sites próprios,
> emuladores e correções para hardware antigo. O README original está em
> [README.original.md](README.original.md).
> Feito para dois notebooks antigos de duas crianças brasileiras (Beni, 8 anos, e Bea, 5 anos).

---

## Para as crianças

### Três categorias, cada uma com o seu tempo
- **Tela inicial "Aprender / Passatempo / Jogar"**: cartões grandes com barrinha e "faltam 18 min".
  - A lista mostra só a categoria escolhida, com **⬅ Voltar** (ou Esc).
  - Quando o tempo acaba, o cartão fica cinza com 🔒 "Amanhã tem mais!".
- **Medidores** verde/amarelo/vermelho no launcher. Durante o jogo, uma barra discreta mostra o tempo restante. Ela fica meio transparente, dá para arrastar para outro canto e tem o ❌ para fechar.
- Nos **sites** aparece também um botão **‹ Voltar** no canto inferior esquerdo.
- Nos **10 segundos finais**, uma contagem grande avisa ("Seu tempo de jogos está acabando! 8…") e sugere o que ainda dá para fazer ("Você ainda pode brincar de Aprender (18 min)").
- Com o **reforço de aprendizagem** ligado:
  - os cartões Jogar e Passatempo explicam com carinho: "Hoje 15 min — ontem faltou aprender 📚";
  - o cartão Aprender mostra quanto falta para ter o Jogar inteiro amanhã ("Meta de hoje cumprida! ⭐").

### O que tem em cada categoria
| 📚 Aprender | 🎨 Passatempo | 🎮 Jogar |
|---|---|---|
| Khan Academy (login automático) | Desenhar (**Kleki**, desenhos salvos em Imagens/Desenhos) | Luanti (parecido com Minecraft) |
| **PhET** com tela para escolher a matéria (Física, Matemática, Química, Terra e Espaço, Biologia), já no Ensino Fundamental 1 | **Autodraw** | SuperTux, SuperTuxKart, Frogatto |
| **Escola Games** sem anúncios e sem o menu de jogos de diversão | **Colorir** (só os desenhos, sem propaganda de outros jogos) | **Super Nintendo e PlayStation** (lista com capas, teclado/mouse/controle) |
| Scratch (TurboWarp), Blockly Games | **Teach Your Monster** (login automático) | jogos de navegador do **itch.io** em tela cheia de verdade |
| Digitação (Klavaro), Planetário (Stellarium) | GCompris, Pingus, Hex-a-hop, Klotski, Music Lab | jogos de vestir/maquiagem/boneca sem anúncios |

Os pais mudam qualquer app de categoria em Pais → Tempo de tela.

### Visual
- **6 temas novos** com arte original em SVG (nenhum personagem ou logo de marca):
  - **Herói Aranha** (quadrinhos), **Blocos de Montar** e **Dojo Ninja**;
  - **Reino do Gelo**, **Casinha Mágica** e **Castelo Encantado**, com letras grandes e redondas para quem está aprendendo a ler.
- **Tudo em português do Brasil**, na tela das crianças e na área dos pais.

---

## Para os pais

### ⏳ Tempo de tela (Pais → Tempo de tela)
- **Limite diário por categoria e total do dia**, por exemplo 30 min de Aprender + 30 min de Jogar.
- O **Passatempo divide o tempo com os Jogos**: desenhar 10 min deixa 20 para jogar. Também pode ter tempo próprio.
- **Tempo diferente em cada dia da semana**: uma tabela Seg–Dom, com o dia de hoje destacado.
- **Categoria de cada app** escolhida numa lista, e um botão **"Zerar o tempo de hoje"**.
- Horários permitidos por dia e por app (do projeto original).

### 📚 Reforço obrigatório de aprendizagem (no mesmo quadro)
- **Meta**: fazer pelo menos *X*% do tempo de Aprender do dia (padrão 50%: com 30 min de Aprender, a meta é 15).
- **Consequência**: se a meta não foi cumprida ontem, hoje o Jogar (e o Passatempo, que divide o mesmo tempo) fica com *Y*% (padrão 50%).
- **Modo proporcional** (opcional): quem aprendeu um pouco perde menos.
- **Justo com a criança**:
  - dia sem uso do notebook não conta;
  - o Aprender e o total do dia nunca diminuem;
  - o próprio launcher fecha o jogo no limite reduzido.
- Os pais veem o motivo, por exemplo: "Hoje: Jogar reduzido para 15 min (de 30) porque ontem Aprender foi 0/30 min".
- Vem desligado e é ligado por perfil.

### 🔑 Login automático nos sites (Pais → Crianças)
- Quadro **"Login automático nos sites"**, com e-mail/usuário e senha **por criança**.
  - Hoje: Khan Academy e Teach Your Monster (conta de família, aba "Home").
- Ao abrir o site, o launcher preenche o login e clica em "Entrar". Se a sessão ainda estiver aberta, não digita nada.
- **A senha fica só neste computador**, num arquivo separado da configuração e legível só pelo usuário. Depois de salva, ela nunca aparece de novo na tela.
- **Cada criança tem o seu navegador de sites** (cookies e logins separados): o Khan da Bea não abre com a conta do Beni.
- Para acrescentar outro site, basta descrever a página de login em `src/site_logins.py`.

### 🛡️ Internet e conteúdo
- **DNS CleanBrowsing Family** em qualquer Wi‑Fi:
  - bloqueia sites adultos, proxies e VPNs;
  - força a Busca Segura do Google/Bing e o Modo Restrito do YouTube.
- Os navegadores não conseguem contornar o filtro, porque o DNS‑over‑HTTPS está desligado.
- **uBlock Origin** nos sites, já ajustado para os jogos do Escola Games abrirem sem anúncio.
- **Sites limpos com CSS próprio**:
  - Escola Games sem o menu "Jogos";
  - Colorir sem a barra de cima, banners e redes sociais;
  - Autodraw sem "Share" e links externos.

  As páginas proibidas também ficam bloqueadas por política do Firefox.
- Downloads vão direto para `~/Imagens/Desenhos`, sem o painel do Firefox, que abriria o gerenciador de arquivos.

### Outros
- **Coleções do itch.io**: cada criança tem uma coleção pública. Jogo adicionado na coleção vira ícone (com capa), e jogo removido some. A sincronização roda no login e a cada 30 min, então os pais testam antes e só então liberam.
- Em Pais → Aparência → **Tela inicial**, você liga ou desliga a pergunta Aprender/Passatempo/Jogar em cada perfil.

---

## Correções para notebooks antigos e jogos "rebeldes"
| Problema | Solução |
|---|---|
| Nenhum app abria (o ❌ por cima falhava) | `python3-tk` passa a ser instalado |
| GCompris não abria (`gcompris` × `gcompris-qt`) | atalho `beni/bin/gcompris` |
| TuxMath, Pingus etc. **prendiam o mouse** e o ❌ não funcionava | `nograb.so` (LD_PRELOAD) anula o "prender mouse" do SDL 1.2/SDL2 |
| SuperTuxKart trocava a resolução e **a tela ficava apagada** ao fechar | os atalhos sempre usam a resolução atual da tela |
| Apps que abrem em janela (Scratch, Klavaro, Klotski) | `cozy-fullscreen` coloca em tela cheia via `wmctrl` |
| Depois de fechar um app pelo ❌, o próximo abria **escondido atrás do menu** | o launcher só fica "por cima" por um instante |
| Ctrl+Alt+Del bloqueava a tela, e ao voltar ficava preta | atalho e bloqueios automáticos desligados |
| Barra do Linux aparecia ao abrir jogos | painéis do XFCE escondidos (aparecem com o mouse na borda) |
| Linha vertical piscando no launcher (F7 do Firefox) | navegação com cursor desligada |
| Esc numa mensagem de "tempo acabou" saía do modo infantil | agora Esc só fecha a mensagem |
| Jogos 3D de navegador lentos no Firefox | jogos de navegador abrem no Chromium com aceleração forçada (≈2× mais FPS neste hardware) |
| Jogos do Escola Games ficavam em "Loading…" com bloqueador de anúncios | o uBlock só bloqueia o script do Google (o jogo tem saída quando ele falha) |
| O DNS global do NetworkManager 1.46 era ignorado | o DNS com filtro vai direto no `systemd-resolved` |

A lista detalhada, arquivo por arquivo, está em [beni/MUDANCAS.md](beni/MUDANCAS.md).

---

## Ambiente em que foi feito e testado

| | |
|---|---|
| Notebook | Samsung RV419/RV420 (≈2011) |
| Processador | Intel Celeron B800 1.5 GHz, 2 núcleos |
| Memória | 2,8 GB |
| Vídeo | Intel HD Graphics 2000 (Sandy Bridge), OpenGL 3.3 (Mesa 25.0) |
| Tela | 1366×768 |
| Rede | Atheros AR9285 (só Wi-Fi, **sem Bluetooth**) |
| Sistema | **Linux Mint 22.3 "Zena" XFCE** (base Ubuntu 24.04), kernel 6.14, sessão X11 |
| Navegadores | Firefox 146 (launcher e sites) · Chromium 155 via Flathub (jogos de navegador) |
| Python | 3.12 (só biblioteca padrão) |

**Requisitos:**
- Linux Mint XFCE ou outra distro baseada em Ubuntu 24.04 com XFCE.
- Sessão **X11** (não Wayland).
- Internet na instalação.
- Um usuário comum para as crianças, com login automático.

Em Mint Cinnamon/MATE quase tudo funciona, mas os ajustes de barra e bloqueio são específicos do XFCE.

---

## Instalação num notebook novo

1. Instale o **Linux Mint XFCE**, crie o usuário e ative o **login automático**.
2. Baixe este repositório e rode o instalador **como o usuário da criança**, sem `sudo` (ele pede a senha quando precisa):
   ```bash
   git clone https://github.com/jaison/beni-launcher.git
   cd beni-launcher
   ./instalar.sh
   ```
   São uns 2–3 GB de downloads: apps do Flathub, Chromium e emuladores. O instalador também
   configura o DNS com filtro, o bloqueador de anúncios e as políticas do Firefox.
3. Saia da sessão e entre de novo. O launcher abre sozinho.
4. **Antes de entregar** para a criança:
   - **Pais → Sistema: crie o PIN dos pais.** Sem PIN, qualquer um entra no painel, sai do modo infantil, zera o tempo ou vê o e-mail das contas salvas.
   - Ajuste nomes, temas e limites em Pais. A configuração inicial traz dois perfis de exemplo, com os apps já separados em Aprender/Passatempo/Jogar.
   - Se quiser, ligue o **reforço de aprendizagem** (Pais → Tempo de tela) e salve os **logins dos sites** (Pais → Crianças).
   - Luanti: abra uma vez e instale o jogo **Mineclonia** (Conteúdo → Procurar).
   - Coloque seus jogos de SNES/PS1 em `~/Jogos/SNES` e `~/Jogos/PS1`. A BIOS do PS1 vai em `~/Jogos/PS1/BIOS` (veja `~/Jogos/LEIA-ME.txt`).
   - Troque as coleções do itch.io em `~/.config/cozy-kids-launcher/itch-colecoes.json`. O arquivo liga o **id do perfil** à URL pública da coleção.

Rodar `./instalar.sh` de novo atualiza os arquivos e **não apaga** a configuração, os logins
salvos nem os jogos. Use `./instalar.sh --sem-apps` para atualizar só o launcher, sem apt/flatpak.

---

## Como funciona (resumo técnico)

```
login → ~/.config/autostart → cozy-iniciar
          ├─ cozy-itch-sync      (coleções do itch.io → tiles "itch-*" no config.json)
          └─ cozy-kids-launcher  (servidor Python em 127.0.0.1:38431 + Firefox em modo quiosque)
                 ├─ usage_limits.py   (tempo por categoria, dia da semana, reforço de aprendizagem)
                 └─ tocar num ícone → process_supervisor.py + overlay.py (❌, tempo, ‹ Voltar)
                        ├─ apps locais: atalhos em ~/.local/bin (supertux, gcompris, …)
                        ├─ sites: Firefox em modo quiosque, um perfil por criança
                        │     (uBlock, CSS dos sites; site_logins.py faz o login pelo Marionette)
                        └─ jogos de navegador: navegador-jogos → Chromium em modo quiosque
                               → cozy-jogo.html (amplia o jogo) + carregando.py (tela de espera)
```

| Onde | O quê |
|---|---|
| `src/` | código do launcher (original + mudanças) → `~/.local/share/cozy-kids-launcher` |
| `src/usage_limits.py`, `src/frontend/usage-limits.*` | tempo de tela por categoria, dia da semana e reforço de aprendizagem |
| `src/site_logins.py`, `src/frontend/site-logins.*` | login automático nos sites (senhas em `~/.config/cozy-kids-launcher/site-logins.json`) |
| `src/frontend/escolha.*` | tela Aprender/Passatempo/Jogar |
| `src/sites/phet.html` | pré-tela de matérias do PhET |
| `src/frontend/cozy-temas.css`, `themes/*.svg`, `themes/fonts/` | temas novos |
| `src/frontend/locales/pt.json` | tradução |
| `beni/bin/` | atalhos dos apps, `cozy-itch-sync`, `navegador-jogos`, `cozy-iniciar` … → `~/.local/bin` |
| `beni/firefox/` | uBlock Origin, CSS dos sites e políticas do Firefox (`/etc/firefox/policies`) |
| `beni/sistema/` | DNS com filtro (systemd-resolved + NetworkManager) |
| `beni/lib/cozy-fixes/` | `nograb.c` (compilado na instalação) e `carregando.py` |
| `beni/cozy-jogos/jogos.py` | lista de jogos SNES/PS1 |
| `beni/chromium/cozy-jogo.html` | moldura que amplia jogos de navegador |
| `beni/config/` | configuração inicial (perfis, apps, categorias, limites) e coleções do itch.io |
| `beni/emuladores/` | configurações do RetroArch, PCSX-R e Luanti para hardware fraco |
| `beni/systemd/` | timer da sincronização do itch.io |
| `beni/ferramentas/` | scripts que geram os SVG dos temas |

O código ainda usa os nomes internos do original (`cozy-kids-launcher`, porta 38431, pastas em
`~/.local/share/cozy-kids-launcher`). Assim fica fácil comparar com o projeto original e trazer
correções de lá.

### Testes
`python3 -m unittest discover -s tests` roda **316 testes**, os do projeto original e os novos:
limites por categoria e dia da semana, categorias que dividem tempo, reforço de aprendizagem e
login automático. Três testes do original foram ajustados ao comportamento novo: textos já
traduzidos e o campo `limitBlocked`.

---

## Limitações conhecidas
- Jogos de navegador demoram 10 a 50 s para abrir num Celeron. Jogos 3D pesados ficam abaixo de 10 FPS e foram escondidos.
- O emulador de PS1 (PCSX-R) é antigo. O core `pcsx_rearmed` do RetroArch seria melhor, mas não está nos repositórios do Ubuntu.
- **Login automático**:
  - Só funciona com contas de e-mail/usuário e senha (não "Entrar com Google").
  - Se o site mudar a página de login, é preciso ajustar `src/site_logins.py`.
  - A senha fica protegida só pela permissão do arquivo, sem cifra. Proteja a área dos pais com PIN.
- O filtro de DNS pode bloquear algum site inofensivo. Para desligar, veja `beni/MUDANCAS.md`.
- O `src/index.html` (e outros arquivos com textos) já vem em pt-BR, não é mais um modelo com `{{…}}`. O `scripts/install.sh` original continua funcionando, mas o caminho recomendado é o `instalar.sh`.
- ROMs comerciais não são fornecidas. Use cópias dos seus próprios discos/cartuchos ou jogos homebrew.

## Créditos e licenças
- **[Cozy Kids Launcher](https://github.com/TrissyGE/cozy-kids-launcher)** © 2026 Tristan e colaboradores, **licença MIT**. Ela continua valendo para todo o código ([LICENSE](LICENSE)), e as mudanças deste projeto são publicadas sob a mesma licença.
- Fontes dos temas (Bangers, Bungee, Shojumaru, Fredoka): SIL Open Font License, veja [themes/fonts/LEIA-ME.md](themes/fonts/LEIA-ME.md).
- uBlock Origin (GPLv3) © Raymond Hill, incluído sem modificações.
- Os apps, jogos e sites (GCompris, TurboWarp, Luanti, SuperTux, Kleki, Khan Academy, PhET, Escola Games, Teach Your Monster, itch.io…) pertencem aos seus autores e só são baixados ou abertos das fontes oficiais.
- Feito com a ajuda do Claude (Anthropic) via Claude Code.

## Galeria
| | |
|---|---|
| ![Temas do Beni](beni/prints/04-temas-beni.jpg) | ![Temas da Bea](beni/prints/05-temas-bea.jpg) |
| ![Lista de jogos](beni/prints/03-lista-jogos.png) | ![Contagem final](beni/prints/06-contagem-final.png) |
| ![Área dos pais](beni/prints/07-area-dos-pais.png) | ![Jogo do itch.io em tela cheia](beni/prints/09-jogo-itch-tela-cheia.png) |
| ![Jogos de vestir](beni/prints/10-jogos-vestir.jpg) | ![Apps](beni/prints/11-apps.jpg) |
