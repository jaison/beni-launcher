#!/usr/bin/env python3
"""Gera o projeto Scratch "Pista Turbo" (src/scratch/Pista Turbo.sb3).

Um jogo de corrida bem simples, com cara de pista de carrinho de brinquedo
(laranja, chamas, turbo amarelo), feito para a criança jogar e depois mexer:
todos os números importantes estão em variáveis com nome em português no topo
do script do carro (velocidade máxima, curva, quantas voltas...).

Uso: python3 beni/ferramentas/gerar-pista-turbo.py [saida.sb3]
"""

import hashlib
import json
import os
import sys
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "..", "..", "src", "scratch", "Pista Turbo.sb3")

# Cores exatas que o carro "sente" (sensor "tocando na cor")
GRAMA = "#3cb043"
TURBO = "#ffe600"
CHEGADA = "#ffffff"

# ------------------------------------------------------------------ desenhos

def pista_svg():
    """Cenário 480x360: grama, pista oval laranja, chegada xadrez e turbos."""
    quadrados = []
    for linha in range(7):           # linha de chegada: x 232..248, y 285..355
        for col in range(2):
            cor = CHEGADA if (linha + col) % 2 == 0 else "#111111"
            quadrados.append(
                f'<rect x="{232 + col * 8}" y="{285 + linha * 10}" width="8" height="10" fill="{cor}"/>')
    def seta(x, y, angulo):
        return (f'<g transform="translate({x} {y}) rotate({angulo})">'
                f'<path d="M-18,-22 L4,0 L-18,22 L-6,22 L16,0 L-6,-22 Z" fill="{TURBO}"/>'
                f'<path d="M-2,-22 L20,0 L-2,22 L10,22 L32,0 L10,-22 Z" fill="{TURBO}"/></g>')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="480" height="360" viewBox="0 0 480 360">
  <rect width="480" height="360" fill="{GRAMA}"/>
  <!-- borda da pista -->
  <rect x="40" y="40" width="400" height="280" rx="120" fill="none" stroke="#a63c00" stroke-width="84"/>
  <!-- pista -->
  <rect x="40" y="40" width="400" height="280" rx="120" fill="none" stroke="#ff7a00" stroke-width="70"/>
  {seta(220, 40, 180)}
  {seta(440, 180, -90)}
  {"".join(quadrados)}
  <!-- miolo: logo com chamas -->
  <g transform="translate(240 180)">
    <path d="M-120,18 C-95,-30 -70,10 -55,-25 C-40,5 -25,-35 -5,-10 C10,-40 30,0 45,-28 C60,0 85,-30 120,18 Z"
          fill="#ff7a00"/>
    <path d="M-100,18 C-80,-10 -62,10 -48,-10 C-35,8 -20,-18 -5,2 C10,-20 28,6 42,-12 C58,8 78,-12 100,18 Z"
          fill="#ffd000"/>
    <text x="0" y="12" text-anchor="middle" font-family="Arial Black, Arial, sans-serif" font-weight="900"
          font-size="30" fill="#c62828" stroke="#fff3e0" stroke-width="2" font-style="italic">PISTA TURBO</text>
    <text x="0" y="40" text-anchor="middle" font-family="Arial, sans-serif" font-weight="700"
          font-size="13" fill="#fff3e0">setas para dirigir · 3 voltas</text>
  </g>
</svg>'''


def carro_svg():
    """Carrinho de corrida visto de cima, apontando para a direita, com chamas."""
    return '''<svg xmlns="http://www.w3.org/2000/svg" width="44" height="26" viewBox="0 0 44 26">
  <rect x="6" y="0" width="9" height="5" rx="2" fill="#111"/>
  <rect x="28" y="0" width="9" height="5" rx="2" fill="#111"/>
  <rect x="6" y="21" width="9" height="5" rx="2" fill="#111"/>
  <rect x="28" y="21" width="9" height="5" rx="2" fill="#111"/>
  <path d="M2,6 L30,4 C38,4 44,9 44,13 C44,17 38,22 30,22 L2,20 C0,20 0,6 2,6 Z" fill="#1565c0"/>
  <path d="M3,8 C9,6 12,10 16,7 C18,10 22,8 24,10 C20,12 22,14 24,16 C22,18 18,16 16,19 C12,16 9,20 3,18 Z"
        fill="#ff7a00"/>
  <path d="M4,10 C8,9 10,12 13,10 C14,12 17,11 18,13 C17,15 14,14 13,16 C10,14 8,17 4,16 Z" fill="#ffd000"/>
  <path d="M27,8 L35,9 C37,10 37,16 35,17 L27,18 Z" fill="#90caf9"/>
  <rect x="0" y="5" width="3" height="16" rx="1" fill="#0d47a1"/>
</svg>'''


# ------------------------------------------------------------------- blocos

class Blocos:
    """Monta o dicionário de blocos do Scratch 3 de um jeito legível."""

    def __init__(self):
        self.blocos = {}
        self.n = 0

    def _id(self):
        self.n += 1
        return f"b{self.n}"

    def bloco(self, opcode, inputs=None, fields=None, shadow=False, top=None, mutation=None):
        bid = self._id()
        b = {"opcode": opcode, "next": None, "parent": None, "inputs": inputs or {},
             "fields": fields or {}, "shadow": shadow, "topLevel": top is not None}
        if top is not None:
            b["x"], b["y"] = top
        if mutation:
            b["mutation"] = mutation
        self.blocos[bid] = b
        for value in (inputs or {}).values():
            for item in value[1:]:
                if isinstance(item, str) and item in self.blocos:
                    self.blocos[item]["parent"] = bid
        return bid

    def pilha(self, ids, parent=None):
        """Encadeia uma lista de blocos (next/parent); devolve o primeiro."""
        anterior = parent
        for i, bid in enumerate(ids):
            self.blocos[bid]["parent"] = anterior
            if i + 1 < len(ids):
                self.blocos[bid]["next"] = ids[i + 1]
            anterior = bid
        return ids[0] if ids else None

    # entradas
    @staticmethod
    def num(v):
        return [1, [4, str(v)]]

    @staticmethod
    def ang(v):
        return [1, [8, str(v)]]

    @staticmethod
    def txt(v):
        return [1, [10, str(v)]]

    def rep(self, bid, padrao=0):
        return [3, bid, [4, str(padrao)]]

    def rep_txt(self, bid):
        return [3, bid, [10, ""]]

    def var(self, nome, vid):
        return [3, [12, nome, vid], [4, "0"]]

    def var_txt(self, nome, vid):
        return [3, [12, nome, vid], [10, ""]]

    def cond(self, bid):
        return [2, bid]

    def sub(self, ids, dono):
        primeiro = self.pilha(ids, parent=dono)
        return [2, primeiro]

    # blocos usados
    def tecla(self, nome):
        menu = self.bloco("sensing_keyoptions", fields={"KEY_OPTION": [nome, None]}, shadow=True)
        return self.bloco("sensing_keypressed", {"KEY_OPTION": [1, menu]})

    def cor(self, hexa):
        return self.bloco("sensing_touchingcolor", {"COLOR": [1, [9, hexa]]})

    def se(self, condicao, corpo):
        bid = self.bloco("control_if", {"CONDITION": self.cond(condicao)})
        self.blocos[condicao]["parent"] = bid
        self.blocos[bid]["inputs"]["SUBSTACK"] = self.sub(corpo, bid)
        return bid

    def sempre(self, corpo):
        bid = self.bloco("control_forever")
        self.blocos[bid]["inputs"]["SUBSTACK"] = self.sub(corpo, bid)
        return bid

    def definir(self, nome, vid, valor):
        return self.bloco("data_setvariableto", {"VALUE": valor}, {"VARIABLE": [nome, vid]})

    def mudar(self, nome, vid, valor):
        return self.bloco("data_changevariableby", {"VALUE": valor}, {"VARIABLE": [nome, vid]})

    def op(self, opcode, a, b, nomes=("NUM1", "NUM2")):
        return self.bloco(opcode, {nomes[0]: a, nomes[1]: b})


def projeto():
    B = Blocos()
    V = {nome: f"v_{i}" for i, nome in enumerate(
        ["velocidade", "voltas", "passou do meio", "velocidade máxima", "curva",
         "aceleração", "voltas para vencer"])}
    vel, voltas, meio = "velocidade", "voltas", "passou do meio"
    vmax, curva, acel, meta = "velocidade máxima", "curva", "aceleração", "voltas para vencer"

    # ---- script 1: quando a bandeira verde for clicada
    inicio = B.bloco("event_whenflagclicked", top=(20, 20))
    ajustes = [
        B.definir(vmax, V[vmax], B.num(6)),
        B.definir(curva, V[curva], B.num(5)),
        B.definir(acel, V[acel], B.num(0.4)),
        B.definir(meta, V[meta], B.num(3)),
        B.definir(vel, V[vel], B.num(0)),
        B.definir(voltas, V[voltas], B.num(0)),
        B.definir(meio, V[meio], B.num(0)),
        B.bloco("motion_gotoxy", {"X": B.num(-40), "Y": B.num(-140)}),
        B.bloco("motion_pointindirection", {"DIRECTION": B.ang(90)}),
        B.bloco("looks_sayforsecs", {"MESSAGE": B.txt("3... 2... 1... JÁ! Use as setas!"), "SECS": B.num(2)}),
        B.bloco("sensing_resettimer"),
    ]

    # acelerar / frear
    acelera = B.se(B.tecla("up arrow"), [B.mudar(vel, V[vel], B.var(acel, V[acel]))])
    freia = B.se(B.tecla("down arrow"), [B.mudar(vel, V[vel], B.num(-0.6))])
    # limite de velocidade
    passou = B.op("operator_gt", B.var(vel, V[vel]), B.var(vmax, V[vmax]), ("OPERAND1", "OPERAND2"))
    limite = B.se(passou, [B.definir(vel, V[vel], B.var(vmax, V[vmax]))])
    # atrito: a cada passo perde um pouco
    atrito_vezes = B.op("operator_multiply", B.var(vel, V[vel]), B.num(0.97))
    atrito = B.definir(vel, V[vel], B.rep(atrito_vezes))
    # na grama fica bem mais devagar
    grama_vezes = B.op("operator_multiply", B.var(vel, V[vel]), B.num(0.85))
    grama = B.se(B.cor(GRAMA), [B.definir(vel, V[vel], B.rep(grama_vezes))])
    # turbo amarelo
    turbo_vezes = B.op("operator_multiply", B.var(vmax, V[vmax]), B.num(1.8))
    turbo = B.se(B.cor(TURBO), [B.definir(vel, V[vel], B.rep(turbo_vezes))])
    # curvas
    esquerda = B.se(B.tecla("left arrow"), [B.bloco("motion_turnleft", {"DEGREES": B.var(curva, V[curva])})])
    direita = B.se(B.tecla("right arrow"), [B.bloco("motion_turnright", {"DEGREES": B.var(curva, V[curva])})])
    anda = B.bloco("motion_movesteps", {"STEPS": B.var(vel, V[vel])})
    # meio da pista (reta de cima): vale para a volta contar
    em_cima = B.op("operator_gt", B.rep(B.bloco("motion_yposition")), B.num(100), ("OPERAND1", "OPERAND2"))
    marca_meio = B.se(em_cima, [B.definir(meio, V[meio], B.num(1))])
    # linha de chegada
    meio_ok = B.op("operator_equals", B.var_txt(meio, V[meio]), B.txt(1), ("OPERAND1", "OPERAND2"))
    na_chegada = B.op("operator_and", B.cond(B.cor(CHEGADA)), B.cond(meio_ok), ("OPERAND1", "OPERAND2"))
    venceu_cond = B.op("operator_equals", B.var_txt(voltas, V[voltas]), B.var_txt(meta, V[meta]),
                       ("OPERAND1", "OPERAND2"))
    tempo = B.bloco("operator_round", {"NUM": B.rep(B.bloco("sensing_timer"))})
    frase = B.op("operator_join", B.txt("🏆 VOCÊ VENCEU em "),
                 B.rep_txt(B.op("operator_join", B.rep_txt(tempo), B.txt(" segundos!"), ("STRING1", "STRING2"))),
                 ("STRING1", "STRING2"))
    venceu = B.se(venceu_cond, [
        B.bloco("looks_say", {"MESSAGE": B.rep_txt(frase)}),
        B.bloco("control_stop", fields={"STOP_OPTION": ["this script", None]},
                mutation={"tagName": "mutation", "children": [], "hasnext": "false"}),
    ])
    volta = B.se(na_chegada, [
        B.mudar(voltas, V[voltas], B.num(1)),
        B.definir(meio, V[meio], B.num(0)),
        venceu,
    ])
    laco = B.sempre([acelera, freia, limite, atrito, grama, turbo, esquerda, direita, anda, marca_meio, volta])
    B.pilha([inicio] + ajustes + [laco])

    # comentário para a criança
    comentario = {
        "c1": {"blockId": None, "x": 520, "y": 20, "width": 330, "height": 230, "minimized": False,
               "text": ("OI, PILOTO! Este jogo é seu: mude o que quiser!\n\n"
                        "• velocidade máxima: o carro corre mais (tente 8)\n"
                        "• curva: vira mais rápido (tente 7)\n"
                        "• voltas para vencer: corrida mais longa\n"
                        "• Pinte o carro em Fantasias, ou a pista em Cenários.\n"
                        "• Grama verde deixa devagar; o amarelo é TURBO!\n\n"
                        "Dica: salve com outro nome em Arquivo → Salvar.")},
    }

    pista = pista_svg().encode()
    carro = carro_svg().encode()

    def costume(nome, dados, cx, cy):
        md5 = hashlib.md5(dados).hexdigest()
        return {"name": nome, "assetId": md5, "md5ext": f"{md5}.svg", "dataFormat": "svg",
                "rotationCenterX": cx, "rotationCenterY": cy, "bitmapResolution": 1}, (f"{md5}.svg", dados)

    c_pista, f_pista = costume("Pista", pista, 240, 180)
    c_carro, f_carro = costume("Carro azul", carro, 22, 13)

    stage = {
        "isStage": True, "name": "Stage",
        "variables": {V[n]: [n, 0] for n in V},
        "lists": {}, "broadcasts": {}, "blocks": {}, "comments": {},
        "currentCostume": 0, "costumes": [c_pista], "sounds": [], "volume": 100,
        "layerOrder": 0, "tempo": 60, "videoTransparency": 50, "videoState": "on",
        "textToSpeechLanguage": None,
    }
    sprite = {
        "isStage": False, "name": "Carro",
        "variables": {}, "lists": {}, "broadcasts": {}, "blocks": B.blocos, "comments": comentario,
        "currentCostume": 0, "costumes": [c_carro], "sounds": [], "volume": 100,
        "layerOrder": 1, "visible": True, "x": -40, "y": -140, "size": 100, "direction": 90,
        "draggable": False, "rotationStyle": "all around",
    }

    def monitor(nome, x, y):
        return {"id": V[nome], "mode": "default", "opcode": "data_variable",
                "params": {"VARIABLE": nome}, "spriteName": None, "value": 0,
                "width": 0, "height": 0, "x": x, "y": y, "visible": True,
                "sliderMin": 0, "sliderMax": 100, "isDiscrete": True}

    project = {
        "targets": [stage, sprite],
        "monitors": [monitor(voltas, 5, 5)],
        "extensions": [],
        "meta": {"semver": "3.0.0", "vm": "0.2.0", "agent": "beni-launcher"},
    }
    return project, [f_pista, f_carro]


def main(argv):
    saida = argv[1] if len(argv) > 1 else SAIDA
    os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
    project, arquivos = projeto()
    with zipfile.ZipFile(saida, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("project.json", json.dumps(project, ensure_ascii=False))
        for nome, dados in arquivos:
            z.writestr(nome, dados)
    print(saida)


if __name__ == "__main__":
    main(sys.argv)
