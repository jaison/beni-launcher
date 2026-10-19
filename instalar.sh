#!/usr/bin/env bash
# =============================================================================
#  Beni Launcher — instalador
#  Prepara um notebook com Linux Mint (XFCE) para crianças: instala o launcher
#  (baseado no Cozy Kids Launcher), os apps/jogos, os emuladores, os temas e
#  todos os ajustes descritos no README.
#
#  Uso (como o usuário que a criança vai usar, NÃO como root):
#     ./instalar.sh            instala/atualiza tudo
#     ./instalar.sh --sem-apps só o launcher e os ajustes (pula apt/flatpak)
#
#  É seguro rodar de novo: atualiza os arquivos e NÃO apaga a configuração
#  existente (~/.config/cozy-kids-launcher/config.json) nem os jogos.
# =============================================================================
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$HOME/.local/share/cozy-kids-launcher"
CFG_DIR="$HOME/.config/cozy-kids-launcher"
BIN="$HOME/.local/bin"
CHROMIUM_DIR="$HOME/.var/app/org.chromium.Chromium"
SEM_APPS=0
[[ "${1:-}" == "--sem-apps" ]] && SEM_APPS=1

passo() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
aviso() { printf '\033[1;33m[aviso]\033[0m %s\n' "$*"; }

if [[ $EUID -eq 0 ]]; then
  echo "Rode como o usuário normal (sem sudo). O script pede a senha quando precisar."; exit 1
fi

# -----------------------------------------------------------------------------
if [[ $SEM_APPS -eq 0 ]]; then
  passo "Pacotes do sistema (apt) — vai pedir a senha"
  sudo apt-get update
  sudo apt-get install -y \
    python3 python3-tk firefox wmctrl xdotool x11-utils x11-xserver-utils gcc \
    flatpak network-manager librsvg2-bin espeak-ng speech-dispatcher \
    tuxmath supertuxkart supertux pingus hex-a-hop frogatto stellarium \
    retroarch libretro-snes9x pcsxr

  passo "Apps do Flathub (versões novas e caprichadas)"
  sudo flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
  sudo flatpak install -y --noninteractive flathub \
    org.kde.gcompris org.tuxpaint.Tuxpaint org.turbowarp.TurboWarp org.luanti.luanti \
    net.sourceforge.Klavaro org.gnome.Klotski org.chromium.Chromium
fi

# -----------------------------------------------------------------------------
passo "Launcher (código em $APP_ROOT)"
mkdir -p "$APP_ROOT/themes/covers" "$APP_ROOT/themes/fonts"
# copia o código; não apaga capas baixadas (themes/covers)
cp -r "$REPO/src/." "$APP_ROOT/"
rm -f "$APP_ROOT/launcher.sh"   # template do projeto original; usamos beni/bin/cozy-kids-launcher
cp "$REPO"/themes/*.jpg "$REPO"/themes/*.svg "$APP_ROOT/themes/"
cp "$REPO"/themes/fonts/* "$APP_ROOT/themes/fonts/"
mkdir -p "$APP_ROOT/themes/themes" && cp "$REPO"/themes/*.jpg "$APP_ROOT/themes/themes/"
echo "0.6.0-beni" > "$APP_ROOT/version"
cp "$REPO/beni/ferramentas/"gerar-temas*.py "$APP_ROOT/themes/"

passo "Comandos em $BIN (atalhos dos apps, sincronização do itch.io etc.)"
mkdir -p "$BIN"
for f in "$REPO"/beni/bin/*; do install -m 0755 "$f" "$BIN/$(basename "$f")"; done
if ! grep -q '.local/bin' <<<"$PATH"; then aviso "~/.local/bin não está no PATH (o Mint coloca no próximo login)."; fi

passo "Correções (impedir que jogos prendam o mouse; tela de carregamento)"
mkdir -p "$HOME/.local/lib/cozy-fixes"
cp "$REPO/beni/lib/cozy-fixes/"* "$HOME/.local/lib/cozy-fixes/"
gcc -shared -fPIC -O2 -o "$HOME/.local/lib/cozy-fixes/nograb.so" "$HOME/.local/lib/cozy-fixes/nograb.c" -ldl

passo "Lista de jogos SNES/PS1 e moldura de tela cheia dos jogos de navegador"
mkdir -p "$HOME/.local/share/cozy-jogos" "$HOME/.config/cozy-jogos" "$CHROMIUM_DIR"
cp "$REPO/beni/cozy-jogos/jogos.py" "$HOME/.local/share/cozy-jogos/"
cp "$REPO/beni/emuladores/retroarch.cfg" "$HOME/.config/cozy-jogos/"
cp "$REPO/beni/chromium/cozy-jogo.html" "$CHROMIUM_DIR/"
mkdir -p "$HOME/Jogos/SNES" "$HOME/Jogos/PS1/BIOS" "$HOME/Jogos/.saves/ps1-memcards" "$HOME/Jogos/.saves/snes"
cp "$REPO/beni/emuladores/Jogos-LEIA-ME.txt" "$HOME/Jogos/LEIA-ME.txt"
mkdir -p "$HOME/.pcsxr/plugins"
cp "$REPO/beni/emuladores/gpuPeopsMesaGL.cfg" "$HOME/.pcsxr/plugins/"
mkdir -p "$HOME/.var/app/org.luanti.luanti/.minetest"
[[ -f "$HOME/.var/app/org.luanti.luanti/.minetest/minetest.conf" ]] || \
  cp "$REPO/beni/emuladores/luanti-minetest.conf" "$HOME/.var/app/org.luanti.luanti/.minetest/minetest.conf"

passo "Configuração (só cria se ainda não existir)"
mkdir -p "$CFG_DIR"; chmod 700 "$CFG_DIR"
if [[ ! -f "$CFG_DIR/config.json" ]]; then
  sed "s|{{HOME}}|$HOME|g" "$REPO/beni/config/config.json" > "$CFG_DIR/config.json"
  chmod 600 "$CFG_DIR/config.json"
  echo "  config.json criado com os perfis de exemplo (ajuste nomes/limites em Pais)."
else
  echo "  config.json já existe — mantido."
fi
[[ -f "$CFG_DIR/itch-colecoes.json" ]] || cp "$REPO/beni/config/itch-colecoes.json" "$CFG_DIR/"
echo "firefox" > "$CFG_DIR/browser"

# Firefox do launcher: desliga a "navegação com cursor" (F7), que mostra uma linha piscando
for P in "$HOME/.cache/cozy-kids-launcher/firefox-profile" "$HOME/.cache/cozy-kids-launcher/external-firefox-profile"; do
  mkdir -p "$P"
  grep -q browsewithcaret "$P/user.js" 2>/dev/null || printf '%s\n' \
    'user_pref("accessibility.browsewithcaret", false);' \
    'user_pref("accessibility.browsewithcaret_shortcut.enabled", false);' >> "$P/user.js"
done
# Sites abertos pelo launcher (Escola Games etc.): bloqueador de anúncios uBlock Origin
P="$HOME/.cache/cozy-kids-launcher/external-firefox-profile"
mkdir -p "$P/extensions"
cp "$REPO/beni/firefox/uBlock0@raymondhill.net.xpi" "$P/extensions/"
grep -q autoDisableScopes "$P/user.js" 2>/dev/null || printf '%s\n' \
  'user_pref("extensions.autoDisableScopes", 0);' \
  'user_pref("extensions.enabledScopes", 15);' >> "$P/user.js"
# Escola Games conta como "Aprender": esconde o menu "Jogos" (diversão) e bloqueia essas páginas
mkdir -p "$P/chrome"
cp "$REPO/beni/firefox/userContent.css" "$P/chrome/"
grep -q legacyUserProfileCustomizations "$P/user.js" || \
  echo 'user_pref("toolkit.legacyUserProfileCustomizations.stylesheets", true);' >> "$P/user.js"
sudo install -D -m 0644 "$REPO/beni/firefox/policies.json" /etc/firefox/policies/policies.json

passo "Abrir sozinho no login + sincronizar o itch.io a cada 30 min"
mkdir -p "$HOME/.config/autostart" "$HOME/.config/systemd/user"
cat > "$HOME/.config/autostart/cozy-kids-launcher-autostart.desktop" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Beni Launcher (Cozy Kids Launcher)
Exec=$BIN/cozy-iniciar --autostart
Terminal=false
NoDisplay=true
X-KDE-autostart-phase=2
EOF
mkdir -p "$HOME/.local/share/applications"
cat > "$HOME/.local/share/applications/cozy-kids-launcher.desktop" <<EOF
[Desktop Entry]
Type=Application
Name=Beni Launcher
Comment=Menu infantil em tela cheia
Exec=$BIN/cozy-iniciar
Icon=applications-games
Terminal=false
Categories=Education;Game;
EOF
cp "$REPO/beni/systemd/"cozy-itch-sync.* "$HOME/.config/systemd/user/"
systemctl --user daemon-reload 2>/dev/null || true
systemctl --user enable --now cozy-itch-sync.timer 2>/dev/null || aviso "não consegui ativar o timer (ative depois: systemctl --user enable --now cozy-itch-sync.timer)"

passo "Ajustes do XFCE (sem bloqueio de tela, barra escondida)"
if command -v xfconf-query >/dev/null && [[ -n "${DISPLAY:-}" ]]; then
  for k in '<Primary><Alt>Delete' '<Primary><Alt>l'; do
    xfconf-query -c xfce4-keyboard-shortcuts -p "/commands/custom/$k" -r 2>/dev/null || true
  done
  xfconf-query -c xfce4-session -p /shutdown/LockScreen -n -t bool -s false 2>/dev/null || true
  xfconf-query -c xfce4-power-manager -p /xfce4-power-manager/lock-screen-suspend-hibernate -n -t bool -s false 2>/dev/null || true
  for p in $(xfconf-query -c xfce4-panel -p /panels 2>/dev/null | grep -E '^[0-9]+$'); do
    xfconf-query -c xfce4-panel -p "/panels/panel-$p/autohide-behavior" -n -t uint -s 2 2>/dev/null || true
  done
  gsettings set apps.light-locker lock-on-suspend false 2>/dev/null || true
  gsettings set apps.light-locker lock-after-screensaver 0 2>/dev/null || true
  gsettings set apps.light-locker late-locking false 2>/dev/null || true
else
  aviso "fora de uma sessão XFCE: rode de novo dentro da sessão gráfica para aplicar estes ajustes."
fi

passo "Jogos das coleções do itch.io (precisa de internet)"
"$BIN/cozy-itch-sync" || aviso "sincronização falhou (sem internet?). Ela roda de novo no próximo login."

cat <<'EOF'

==========================================================================
 Pronto! Saia da sessão e entre de novo (ou reinicie) para o launcher abrir.

 Antes de entregar o notebook:
  1. Pais → Sistema: crie o PIN dos pais.
  2. Ajuste nomes, temas e limites de tempo em Pais.
  3. Luanti: abra uma vez e instale o jogo "Mineclonia" (Conteúdo → Jogos).
  4. Coloque seus jogos de SNES/PS1 em ~/Jogos (veja ~/Jogos/LEIA-ME.txt).
  5. Ajuste as coleções do itch.io em ~/.config/cozy-kids-launcher/itch-colecoes.json
==========================================================================
EOF
