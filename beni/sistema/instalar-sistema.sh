#!/usr/bin/env bash
# =============================================================================
#  Beni Launcher — parte do SISTEMA (roda como root)
#  Chamado pelo instalar.sh (com sudo) e pelo atualizador automático (no boot).
#
#   instalar-sistema.sh [opções] USUARIO
#     --sem-pacotes   não mexe em apt/flatpak
#     --so-pacotes    só instala os pacotes que faltam (usado para tentar de novo)
#     --atualizacao   rodando pelo atualizador: falha de pacote não interrompe
#
#  Faz: pacotes (pacotes-apt.txt / pacotes-flatpak.txt, só os que faltam),
#  políticas do Firefox, DNS com filtro e o próprio atualizador automático.
# =============================================================================
set -euo pipefail

AQUI="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$AQUI/../.." && pwd)"
STATE_DIR=/var/lib/beni-launcher
PENDENTES="$STATE_DIR/pacotes-pendentes"
SEM_PACOTES=0; SO_PACOTES=0; ATUALIZACAO=0; USUARIO=""
for arg in "$@"; do
  case "$arg" in
    --sem-pacotes) SEM_PACOTES=1 ;;
    --so-pacotes) SO_PACOTES=1 ;;
    --atualizacao) ATUALIZACAO=1 ;;
    -*) echo "opção desconhecida: $arg" >&2; exit 2 ;;
    *) USUARIO="$arg" ;;
  esac
done
[[ $EUID -eq 0 ]] || { echo "rode como root (sudo)" >&2; exit 1; }
id "$USUARIO" >/dev/null 2>&1 || { echo "uso: $0 [opções] USUARIO" >&2; exit 2; }

passo() { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
aviso() { printf '\033[1;33m[aviso]\033[0m %s\n' "$*"; }
lista() { grep -v '^\s*#' "$1" | sed 's/\s*#.*//' | awk 'NF'; }
mkdir -p "$STATE_DIR"

# ----------------------------------------------------------------- pacotes
pacotes() {
  local faltam=() p
  for p in $(lista "$AQUI/pacotes-apt.txt"); do
    dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q "install ok installed" || faltam+=("$p")
  done
  if ((${#faltam[@]})); then
    passo "Pacotes do sistema que faltam: ${faltam[*]}"
    apt-get update
    DEBIAN_FRONTEND=noninteractive apt-get install -y "${faltam[@]}"
  fi
  local fp=()
  for p in $(lista "$AQUI/pacotes-flatpak.txt"); do
    flatpak info --system "$p" >/dev/null 2>&1 || fp+=("$p")
  done
  if ((${#fp[@]})); then
    passo "Apps do Flathub que faltam: ${fp[*]}"
    flatpak remote-add --system --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo
    flatpak install --system -y --noninteractive flathub "${fp[@]}"
  fi
}
if [[ $SEM_PACOTES -eq 0 ]]; then
  if [[ $ATUALIZACAO -eq 1 || $SO_PACOTES -eq 1 ]]; then
    # sem internet no boot: o atualizador tenta de novo na próxima verificação
    if pacotes; then rm -f "$PENDENTES"; else touch "$PENDENTES"; aviso "pacotes ficaram pendentes"; fi
  else
    pacotes
    rm -f "$PENDENTES"
  fi
fi
[[ $SO_PACOTES -eq 1 ]] && exit 0

# ------------------------------------------------------ políticas do Firefox
passo "Políticas do Firefox (bloqueios, uBlock, sem DNS próprio)"
install -D -m 0644 "$REPO/beni/firefox/policies.json" /etc/firefox/policies/policies.json

# ------------------------------------------------------------ DNS com filtro
passo "DNS com filtro para crianças (CleanBrowsing Family) em qualquer rede"
# O NetworkManager 1.46 ignora o DNS global quando usa o systemd-resolved; por isso
# ele para de repassar o DNS do roteador e o resolved usa só o DNS com filtro.
mudou=0
instala_se_mudou() {  # origem destino
  if ! cmp -s "$1" "$2"; then install -D -m 0644 "$1" "$2"; mudou=1; fi
}
instala_se_mudou "$AQUI/dns-familia-resolved.conf" /etc/systemd/resolved.conf.d/dns-familia.conf
instala_se_mudou "$AQUI/90-dns-familia.conf" /etc/NetworkManager/conf.d/90-dns-familia.conf
if [[ $mudou -eq 1 ]]; then
  systemctl restart systemd-resolved NetworkManager || aviso "reinicie o computador para o DNS com filtro valer"
fi

# ------------------------------------------------------ atualizador automático
passo "Atualizador automático (Releases do GitHub)"
install -D -m 0755 "$AQUI/beni-atualizar" /usr/local/sbin/beni-atualizar
install -d -m 0755 /usr/local/lib/beni-launcher
install -m 0755 "$AQUI/instalar-sistema.sh" /usr/local/lib/beni-launcher/instalar-sistema.sh
install -m 0644 "$AQUI/pacotes-apt.txt" "$AQUI/pacotes-flatpak.txt" /usr/local/lib/beni-launcher/
for unit in beni-atualizar-verificar.service beni-atualizar-verificar.timer beni-atualizar-aplicar.service; do
  install -m 0644 "$AQUI/$unit" "/etc/systemd/system/$unit"
done
install -d -m 0755 /etc/beni-launcher
if [[ ! -f /etc/beni-launcher/atualizar.conf ]]; then
  cat > /etc/beni-launcher/atualizar.conf <<EOF
# Atualizador automático do Beni Launcher (beni-atualizar)
# Usuário das crianças (onde o launcher está instalado)
USUARIO=$USUARIO
# Repositório do GitHub de onde vêm as Releases (tag vX.Y.Z)
REPO=jaison/beni-launcher
# Notebook sempre ligado: versão não forçada é instalada nesta janela (horas)
JANELA_INICIO=2
JANELA_FIM=5
EOF
fi
chmod 0644 /etc/beni-launcher/atualizar.conf
touch /var/log/beni-atualizar.log; chmod 0644 /var/log/beni-atualizar.log
systemctl daemon-reload
systemctl enable beni-atualizar-aplicar.service >/dev/null
if [[ $ATUALIZACAO -eq 1 ]]; then
  systemctl enable beni-atualizar-verificar.timer >/dev/null
else
  systemctl enable --now beni-atualizar-verificar.timer >/dev/null
fi
echo "  atualizador ligado: $(systemctl is-enabled beni-atualizar-verificar.timer) (veja: beni-atualizar estado)"
