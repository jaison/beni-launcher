#!/usr/bin/env python3
"""Tela de carregamento do Cozy Kids Launcher para jogos de navegador.

Cobre a tela inteira assim que o jogo é escolhido e some sozinha quando a janela
do navegador já está em tela cheia (ou depois de 60 s). Assim a criança não vê a
área de trabalho, a barra do Linux nem a janela do navegador piscando.
Uso: carregando.py "<classe da janela que vai abrir>" ["Nome do jogo"]
"""
import subprocess
import sys
import time
import tkinter as tk

CLASSE = (sys.argv[1] if len(sys.argv) > 1 else "chromium").lower()
NOME = sys.argv[2] if len(sys.argv) > 2 else ""
INICIO = time.time()
PRONTO_DESDE = None

root = tk.Tk(className="cozy-carregando")
root.overrideredirect(True)
L, A = root.winfo_screenwidth(), root.winfo_screenheight()
root.geometry(f"{L}x{A}+0+0")
root.configure(bg="#1b1f3b", cursor="watch")
root.attributes("-topmost", True)
c = tk.Canvas(root, bg="#1b1f3b", highlightthickness=0, width=L, height=A)
c.pack(fill="both", expand=True)
c.create_text(L // 2, A // 2 - 70, text="🎮", font=("Noto Color Emoji", 64), fill="white")
c.create_text(L // 2, A // 2 + 20, text="Carregando" + (f" {NOME}" if NOME else "") + "…",
              font=("DejaVu Sans", 30, "bold"), fill="white")
c.create_text(L // 2, A // 2 + 70, text="Só um pouquinho!", font=("DejaVu Sans", 18), fill="#c8cdf5")
pontos = [c.create_oval(L // 2 - 60 + i * 40, A // 2 + 120, L // 2 - 40 + i * 40, A // 2 + 140,
                        fill="#ffd34d", outline="") for i in range(4)]
passo = 0


def janela_pronta():
    """True quando existe janela da classe pedida em tela cheia."""
    try:
        saida = subprocess.run(["wmctrl", "-lx"], capture_output=True, text=True, timeout=2).stdout
    except Exception:
        return False
    for linha in saida.splitlines():
        partes = linha.split(None, 4)
        if len(partes) >= 3 and CLASSE in partes[2].lower():
            try:
                estado = subprocess.run(["xprop", "-id", partes[0], "_NET_WM_STATE"],
                                        capture_output=True, text=True, timeout=2).stdout
            except Exception:
                continue
            if "FULLSCREEN" in estado:
                return True
    return False


def tique():
    global passo, PRONTO_DESDE
    passo += 1
    for i, p in enumerate(pontos):
        c.itemconfigure(p, fill="#ffd34d" if i == passo % 4 else "#4a5190")
    pass  # o botão ❌ do launcher fica por cima (ele se levanta sozinho)
    if janela_pronta():
        PRONTO_DESDE = PRONTO_DESDE or time.time()
    # espera um pouco depois da janela ficar pronta, para o jogo desenhar a 1a tela
    if (PRONTO_DESDE and time.time() - PRONTO_DESDE > 2.5) or time.time() - INICIO > 60:
        root.destroy()
        return
    root.after(400, tique)


root.after(100, tique)
root.mainloop()
