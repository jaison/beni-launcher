#!/usr/bin/env python3
"""Cozy Jogos: lista de jogos em tela cheia para crianças (SNES e PS1).

Uso: jogos.py snes | ps1

Mostra os jogos da pasta ~/Jogos/SNES ou ~/Jogos/PS1 como cartões grandes
(com capa, se houver uma imagem com o mesmo nome do jogo). Funciona com
teclado (setas + Enter), mouse/touchpad e controle (/dev/input/js*).
Ao escolher um jogo, abre o emulador e, quando ele fecha, volta para a lista.
Não troca a resolução da tela e não prende o mouse.
"""

import base64
import glob
import io
import os
import queue
import re
import struct
import subprocess
import sys
import threading
import tkinter as tk

HOME = os.path.expanduser("~")
JOGOS = os.path.join(HOME, "Jogos")
CFG_DIR = os.path.join(HOME, ".config", "cozy-jogos")
SNES9X_CORE = "/usr/lib/x86_64-linux-gnu/libretro/snes9x_libretro.so"

SISTEMAS = {
    "snes": {
        "titulo": "Super Nintendo",
        "pasta": os.path.join(JOGOS, "SNES"),
        "exts": (".sfc", ".smc", ".swc", ".fig", ".bs", ".zip"),
        "cor": "#7b5cd6",
    },
    "ps1": {
        "titulo": "PlayStation",
        "pasta": os.path.join(JOGOS, "PS1"),
        "exts": (".cue", ".iso", ".img", ".mdf", ".pbp", ".bin"),
        "cor": "#2f7fd8",
    },
}
IMG_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".gif")
BIOS_NOMES = ("scph1001.bin", "scph5501.bin", "scph7001.bin", "scph5500.bin",
              "scph5502.bin", "scph7502.bin", "scph101.bin", "scph1000.bin")

# Layout (tela 1366x768)
COLS = 4
CARD_W, CARD_H = 290, 300
CAPA_W, CAPA_H = 266, 220
GAP = 26
TOPO = 120
FUNDO = "#1b1f3b"
CARTAO = "#2a3060"
DESTAQUE = "#ffd34d"


def nome_bonito(caminho):
    nome = os.path.splitext(os.path.basename(caminho))[0]
    nome = re.sub(r"\s*[\(\[][^\)\]]*[\)\]]", "", nome)
    nome = nome.replace("_", " ").strip()
    return nome or os.path.basename(caminho)


def listar_jogos(sistema):
    info = SISTEMAS[sistema]
    pasta = info["pasta"]
    arquivos = []
    for raiz, dirs, nomes in os.walk(pasta):
        # A pasta BIOS não tem jogos
        dirs[:] = [d for d in dirs if d.upper() != "BIOS" and not d.startswith(".")]
        for n in nomes:
            if n.lower().endswith(info["exts"]):
                arquivos.append(os.path.join(raiz, n))
    if sistema == "ps1":
        # .bin que pertence a um .cue não aparece sozinho
        usados = set()
        for f in arquivos:
            if f.lower().endswith(".cue"):
                try:
                    with open(f, "r", errors="ignore") as h:
                        for linha in h:
                            m = re.match(r'\s*FILE\s+"?(.+?)"?\s+\S+\s*$', linha, re.I)
                            if m:
                                usados.add(os.path.normpath(os.path.join(os.path.dirname(f), m.group(1))).lower())
                except OSError:
                    pass
        arquivos = [f for f in arquivos
                    if not (f.lower().endswith(".bin") and os.path.normpath(f).lower() in usados)]
    jogos = [(nome_bonito(f), f) for f in arquivos]
    jogos.sort(key=lambda j: j[0].lower())
    return jogos


def achar_capa(rom):
    base = os.path.splitext(rom)[0]
    pasta = os.path.dirname(rom)
    candidatos = [base + e for e in IMG_EXTS]
    nome = os.path.basename(base)
    for sub in ("capas", "Capas"):
        candidatos += [os.path.join(pasta, sub, nome + e) for e in IMG_EXTS]
    for c in candidatos:
        if os.path.isfile(c):
            return c
    return None


def carregar_capa(caminho):
    """Devolve um tk.PhotoImage redimensionado (usa PIL para JPG/redimensionar)."""
    try:
        from PIL import Image
        img = Image.open(caminho)
        img.thumbnail((CAPA_W, CAPA_H))
        buf = io.BytesIO()
        img.convert("RGB").save(buf, format="PNG")
        return tk.PhotoImage(data=base64.b64encode(buf.getvalue()))
    except Exception:
        try:
            return tk.PhotoImage(file=caminho)
        except Exception:
            return None


def comando_jogo(sistema, rom):
    if sistema == "snes":
        return ["retroarch", "-f", "-c", os.path.join(CFG_DIR, "retroarch.cfg"),
                "-L", SNES9X_CORE, rom]
    # O pcsxr procura o -cfg relativo a ~/.pcsxr
    cfg = os.path.relpath(preparar_pcsxr_cfg(), os.path.join(HOME, ".pcsxr"))
    # O vídeo do pcsxr não acha modo de tela cheia neste driver: abre em janela e o
    # cozy-fullscreen coloca a janela em tela cheia (sem trocar a resolução).
    return ["cozy-fullscreen", "pcsxr", "pcsxr", "-nogui", "-cfg", cfg, "-cdfile", rom]


def preparar_pcsxr_cfg():
    """Gera a config do pcsxr; usa BIOS real se o dono colocou uma, senão HLE."""
    bios_dir = os.path.join(SISTEMAS["ps1"]["pasta"], "BIOS")
    bios = "HLE"
    try:
        presentes = {n.lower(): n for n in os.listdir(bios_dir)}
    except OSError:
        presentes = {}
    for n in BIOS_NOMES:
        if n in presentes:
            bios = presentes[n]
            break
    mc = os.path.join(JOGOS, ".saves", "ps1-memcards")
    os.makedirs(mc, exist_ok=True)
    cfg = os.path.join(CFG_DIR, "pcsxr.cfg")
    linhas = {
        "Bios": bios,
        "Gpu": "libpeopsxgl.so",  # o DFXVideo precisa de Xv RGB/YUV, que este driver não tem
        "Spu": "libDFSound.so",
        "Cdr": "libDFCdrom.so",
        "Sio1": "libBladeSio1.so",
        "Net": "Disabled",
        "Pad1": "libDFInput.so",
        "Pad2": "libDFInput.so",
        "Mcd1": os.path.join(mc, "card1.mcd"),
        "Mcd2": os.path.join(mc, "card2.mcd"),
        "BiosDir": bios_dir + "/",
        "PluginsDir": "/usr/lib/x86_64-linux-gnu/psemu/",
        "IsoImgDir": SISTEMAS["ps1"]["pasta"],
        "Xa": 0, "SioIrq": 0, "Mdec": 0, "PsxAuto": 1, "Cdda": 0,
        "SlowBoot": 0, "Dbg": 0, "PsxOut": 0, "SpuIrq": 0, "RCntFix": 0,
        "VSyncWA": 0, "Widescreen": 0, "Cpu": 0, "PsxType": 0,
    }
    with open(cfg, "w") as h:
        for k, v in linhas.items():
            h.write(f"{k} = {v}\n")
    return cfg


class Controles(threading.Thread):
    """Lê todos os /dev/input/js* e manda 'cima/baixo/esq/dir/ok' para a fila."""

    def __init__(self, fila):
        super().__init__(daemon=True)
        self.fila = fila
        self.ativo = True
        self.abertos = {}
        self.eixos = {}

    def run(self):
        import select
        while True:
            for dev in glob.glob("/dev/input/js*"):
                if dev not in self.abertos:
                    try:
                        self.abertos[dev] = os.open(dev, os.O_RDONLY | os.O_NONBLOCK)
                    except OSError:
                        pass
            fds = list(self.abertos.values())
            if not fds:
                threading.Event().wait(2)
                continue
            prontos, _, _ = select.select(fds, [], [], 2)
            for fd in prontos:
                try:
                    dados = os.read(fd, 8 * 32)
                except OSError:
                    for d, f in list(self.abertos.items()):
                        if f == fd:
                            os.close(fd)
                            del self.abertos[d]
                    continue
                for i in range(0, len(dados) - 7, 8):
                    _t, valor, tipo, num = struct.unpack("IhBB", dados[i:i + 8])
                    if tipo & 0x80 or not self.ativo:
                        continue
                    self.evento(fd, tipo, num, valor)

    def evento(self, fd, tipo, num, valor):
        if tipo == 1 and valor == 1:  # botão apertado
            self.fila.put("ok")
        elif tipo == 2:  # eixo
            chave = (fd, num)
            antes = self.eixos.get(chave, 0)
            agora = -1 if valor < -16000 else (1 if valor > 16000 else 0)
            self.eixos[chave] = agora
            if agora and agora != antes:
                horizontal = num % 2 == 0
                if horizontal:
                    self.fila.put("dir" if agora > 0 else "esq")
                else:
                    self.fila.put("baixo" if agora > 0 else "cima")


class App:
    def __init__(self, sistema):
        self.sistema = sistema
        self.info = SISTEMAS[sistema]
        self.jogos = listar_jogos(sistema)
        self.sel = 0
        self.proc = None
        self.capas = []
        self.fila = queue.Queue()

        self.root = tk.Tk(className="cozy-jogos")
        self.root.title("Jogos - " + self.info["titulo"])
        self.root.configure(bg=FUNDO, cursor="hand2")
        self.largura = self.root.winfo_screenwidth()
        self.altura = self.root.winfo_screenheight()
        self.root.geometry(f"{self.largura}x{self.altura}+0+0")
        self.root.attributes("-fullscreen", True)

        self.canvas = tk.Canvas(self.root, bg=FUNDO, highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        for tecla, acao in (("<Left>", "esq"), ("<Right>", "dir"), ("<Up>", "cima"),
                            ("<Down>", "baixo"), ("<Return>", "ok"), ("<KP_Enter>", "ok"),
                            ("<space>", "ok")):
            self.root.bind(tecla, lambda e, a=acao: self.acao(a))
        self.canvas.bind("<Button-4>", lambda e: self.rolar(-1))
        self.canvas.bind("<Button-5>", lambda e: self.rolar(1))

        self.controles = Controles(self.fila)
        self.controles.start()
        self.desenhar()
        self.root.after(100, self.ler_fila)
        self.root.after(300, self.root.focus_force)

    # ---------- desenho ----------
    def desenhar(self):
        c = self.canvas
        c.delete("all")
        self.capas = []
        w = self.largura
        c.create_text(w // 2, 52, text=self.info["titulo"], fill="white",
                      font=("DejaVu Sans", 34, "bold"), tags="fixo")
        if not self.jogos:
            pasta = self.info["pasta"].replace(HOME, "~")
            c.create_text(w // 2, self.altura // 2 - 20,
                          text="Ainda não tem jogos aqui.",
                          fill="white", font=("DejaVu Sans", 30, "bold"))
            c.create_text(w // 2, self.altura // 2 + 40,
                          text=f"Peça para um adulto colocar os jogos na pasta {pasta}",
                          fill="#c8cdf5", font=("DejaVu Sans", 18))
            return
        total_w = COLS * CARD_W + (COLS - 1) * GAP
        x0 = (w - total_w) // 2
        self.cartoes = []
        for i, (nome, rom) in enumerate(self.jogos):
            lin, col = divmod(i, COLS)
            x = x0 + col * (CARD_W + GAP)
            y = TOPO + lin * (CARD_H + GAP)
            tag = f"j{i}"
            c.create_rectangle(x, y, x + CARD_W, y + CARD_H, fill=CARTAO,
                               outline=CARTAO, width=6, tags=(tag, f"borda{i}"))
            capa = achar_capa(rom)
            img = carregar_capa(capa) if capa else None
            cx, cy = x + CARD_W // 2, y + 12 + CAPA_H // 2
            if img:
                self.capas.append(img)
                c.create_image(cx, cy, image=img, tags=tag)
            else:
                c.create_rectangle(x + 12, y + 12, x + CARD_W - 12, y + 12 + CAPA_H,
                                   fill=self.info["cor"], outline="", tags=tag)
                c.create_text(cx, cy, text=nome, fill="white", width=CAPA_W - 20,
                              justify="center", font=("DejaVu Sans", 20, "bold"), tags=tag)
            c.create_text(cx, y + CARD_H - 34, text=nome, fill="white",
                          width=CARD_W - 16, justify="center",
                          font=("DejaVu Sans", 14, "bold"), tags=tag)
            c.tag_bind(tag, "<Enter>", lambda e, k=i: self.selecionar(k))
            c.tag_bind(tag, "<Button-1>", lambda e, k=i: self.jogar(k))
        linhas = (len(self.jogos) + COLS - 1) // COLS
        altura_total = TOPO + linhas * (CARD_H + GAP) + 60
        c.configure(scrollregion=(0, 0, w, max(altura_total, self.altura)))
        self.selecionar(self.sel)

    def selecionar(self, k):
        if not self.jogos:
            return
        k = max(0, min(len(self.jogos) - 1, k))
        self.canvas.itemconfigure(f"borda{self.sel}", outline=CARTAO)
        self.sel = k
        self.canvas.itemconfigure(f"borda{k}", outline=DESTAQUE)
        # Rolar para manter o cartão escolhido visível
        lin = k // COLS
        y = TOPO + lin * (CARD_H + GAP)
        topo_vis = self.canvas.canvasy(0)
        sr = self.canvas.cget("scrollregion").split()
        total = float(sr[3]) if sr else self.altura
        if y + CARD_H > topo_vis + self.altura - 20 or y < topo_vis + TOPO:
            alvo = max(0, y - TOPO)
            self.canvas.yview_moveto(alvo / total)

    def rolar(self, d):
        self.canvas.yview_scroll(d, "units")

    # ---------- entrada ----------
    def ler_fila(self):
        try:
            while True:
                self.acao(self.fila.get_nowait())
        except queue.Empty:
            pass
        self.root.after(80, self.ler_fila)

    def acao(self, a):
        if self.proc is not None or not self.jogos:
            return
        if a == "esq":
            self.selecionar(self.sel - 1)
        elif a == "dir":
            self.selecionar(self.sel + 1)
        elif a == "cima":
            self.selecionar(self.sel - COLS)
        elif a == "baixo":
            self.selecionar(self.sel + COLS)
        elif a == "ok":
            self.jogar(self.sel)

    # ---------- jogo ----------
    def jogar(self, k):
        if self.proc is not None:
            return
        self.selecionar(k)
        nome, rom = self.jogos[k]
        try:
            self.proc = subprocess.Popen(comando_jogo(self.sistema, rom))
        except OSError as e:
            print("Erro ao abrir o jogo:", e, file=sys.stderr)
            self.proc = None
            return
        self.controles.ativo = False
        self.root.after(1500, self.root.withdraw)
        self.root.after(1000, self.esperar)

    def esperar(self):
        if self.proc.poll() is None:
            self.root.after(500, self.esperar)
            return
        self.proc = None
        # Esvazia comandos que chegaram durante o jogo
        while not self.fila.empty():
            self.fila.get_nowait()
        self.root.deiconify()
        self.root.attributes("-fullscreen", True)
        self.root.lift()
        self.root.after(200, self.root.focus_force)
        self.root.after(600, self.reativar_controles)

    def reativar_controles(self):
        self.controles.ativo = True


def main():
    sistema = (sys.argv[1] if len(sys.argv) > 1 else "snes").lower()
    if sistema not in SISTEMAS:
        print("uso: cozy-jogos snes|ps1", file=sys.stderr)
        return 2
    os.makedirs(CFG_DIR, exist_ok=True)
    app = App(sistema)
    app.root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
