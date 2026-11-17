"""Chefes, padrões de ataque e fases. Boss atual: Ogro Guardião (2 fases)."""
import math
import random
import pygame
from settings import (CHAO_Y, BRANCO, DOURADO, VERMELHO, aproximar,
                      carregar_imagem, retangulo_alpha)
from combat import mover

ATAQUES = {
    "pancada":   dict(tele=0.95, ativo=0.22, rec=1.00),
    "investida": dict(tele=0.85, ativo=0.80, rec=1.10),
    "chuva":     dict(tele=0.80, ativo=1.40, rec=0.90),
}


class Onda:
    """Onda de choque que corre pelo chão (dá para pular por cima)."""

    def __init__(self, x, direcao, vel=330):
        self.x = float(x)
        self.rect = pygame.Rect(int(x), CHAO_Y - 36, 30, 36)
        self.dir = direcao
        self.vel = vel
        self.vivo = True
        self.dano = 1
        self.golpe_id = 0

    def update(self, dt, limites):
        self.x += self.dir * self.vel * dt
        self.rect.x = int(self.x)
        if self.rect.right < limites[0] or self.rect.left > limites[1]:
            self.vivo = False

    def caixas_dano(self):
        return [self.rect]

    def desenhar(self, tela, cx):
        r = self.rect.move(-cx, 0)
        pygame.draw.polygon(tela, DOURADO, [(r.left, r.bottom), (r.centerx, r.top), (r.right, r.bottom)])


class Pedra:
    """Pedra que cai: mostra um aviso no chão antes de despencar."""

    def __init__(self, x, aviso=0.9):
        self.x = x
        self.aviso = aviso
        self.y = -60.0
        self.rect = pygame.Rect(x - 20, -60, 40, 40)
        self.vivo = True
        self.dano = 1
        self.golpe_id = 0

    def update(self, dt):
        if self.aviso > 0:
            self.aviso -= dt
            return
        self.y += 640 * dt
        self.rect.y = int(self.y)
        if self.rect.bottom >= CHAO_Y:
            self.vivo = False

    def caixas_dano(self):
        return [self.rect] if self.aviso <= 0 else []

    def desenhar(self, tela, cx):
        if self.aviso > 0:
            larg = int(30 + 40 * (1 - max(self.aviso, 0) / 0.9))
            retangulo_alpha(tela, (255, 60, 60, 120), pygame.Rect(self.x - cx - larg // 2, CHAO_Y - 6, larg, 6))
        else:
            pygame.draw.circle(tela, (120, 120, 130), self.rect.move(-cx, 0).center, 20)


class Ogro:
    """Ogro Guardião. Fase 1 é didática (avisos longos, dicas na tela).
    Ao 'morrer' pela primeira vez ele se levanta enfurecido na fase 2."""

    def __init__(self, x, arena):
        self.arena = arena  # (x_esquerda, x_direita)
        self.rect = pygame.Rect(x, CHAO_Y - 130, 90, 130)
        self.pos = pygame.Vector2(self.rect.topleft)
        self.vel = pygame.Vector2(0, 0)
        self.no_chao = False
        self.bateu_parede = False
        self.usa_gravidade = True
        self.fase = 1
        self.hp_max = 20
        self.hp = 20
        self.vivo = True
        self.derrotado = False
        self.estado = "dormindo"
        self.t = 0.0
        self.facing = -1
        self.golpe_id = 0
        self.dano = 1
        self.ataque = None
        self.ultimo = None
        self.exausto = False
        self.rec_extra = None
        self.flash = 0.0
        self.ondas = []
        self.pedras = []
        self.eventos = []
        self.sprite = carregar_imagem("ogro.png", (150, 160))

    # ---------- propriedades ----------
    @property
    def mult(self):
        return 1.0 if self.fase == 1 else 1.4

    @property
    def nome(self):
        return "Ogro Guardião" + ("" if self.fase == 1 else " (Enfurecido)")

    def dur(self, chave):
        if chave == "rec" and self.rec_extra is not None:
            return self.rec_extra
        base = ATAQUES[self.ataque][chave]
        return base if chave == "ativo" else base / self.mult

    def acordar(self):
        if self.estado == "dormindo":
            self.estado = "idle"
            self.t = -0.8  # respiro antes do primeiro ataque
            self.eventos.append("acordou")

    # ---------- combate ----------
    def receber_dano(self, dano, direcao):
        if self.estado in ("dormindo", "caindo", "levantando", "morto"):
            return False
        if self.estado == "recuperar" and self.exausto:
            dano = math.ceil(dano * 1.5)  # exausto = leva mais dano
        self.hp -= dano
        self.flash = 0.1
        if self.hp <= 0:
            self.hp = 0
            self.exausto = False
            self.ondas, self.pedras = [], []
            if self.fase == 1:
                self.estado, self.t = "caindo", 0.0
            else:
                self.estado, self.t = "morto", 0.0
                self.vivo = False
                self.derrotado = True
        return True

    def _zona_pancada(self):
        x = self.rect.right - 10 if self.facing > 0 else self.rect.left - 110
        return pygame.Rect(x, self.rect.bottom - 100, 120, 100)

    def caixas_dano(self):
        if self.estado != "atacar":
            return []
        if self.ataque == "pancada":
            return [self._zona_pancada()]
        if self.ataque == "investida":
            return [self.rect.inflate(-10, -10)]
        return []

    def perigos(self):
        return [self] + self.ondas + self.pedras

    def dica(self):
        """Textos de ajuda para o jogador iniciante (só na fase 1)."""
        if self.fase != 1:
            return ""
        if self.estado == "telegrafar":
            return {"pancada": "PANCADA! Afaste-se ou esquive com K.",
                    "investida": "INVESTIDA! Pule por cima ou esquive com K."}.get(self.ataque, "")
        if self.estado == "recuperar" and self.exausto:
            return "Ele ficou exausto! Ataque agora (J)!"
        return ""

    # ---------- IA ----------
    def _escolher_ataque(self, jogador):
        dist = abs(jogador.rect.centerx - self.rect.centerx)
        opcoes = ["pancada", "investida"] + (["chuva"] if self.fase == 2 else [])
        pesos = []
        for o in opcoes:
            p = 1.0
            if o == "pancada" and dist < 170:
                p = 3.0
            if o == "investida" and dist >= 170:
                p = 3.0
            if o == self.ultimo:
                p *= 0.3
            pesos.append(p)
        self.ataque = random.choices(opcoes, pesos)[0]
        self.ultimo = self.ataque
        self.facing = 1 if jogador.rect.centerx > self.rect.centerx else -1
        self.estado, self.t, self.rec_extra = "telegrafar", 0.0, None

    def _comecar_ataque(self, jogador, efeitos):
        self.estado, self.t = "atacar", 0.0
        self.golpe_id += 1
        if self.ataque == "pancada":
            efeitos.tremor = 0.25
            efeitos.fagulhas(self._zona_pancada().centerx, CHAO_Y, DOURADO, 12)
            if self.fase == 2:
                self.ondas.append(Onda(self.rect.left, -1))
                self.ondas.append(Onda(self.rect.right, 1))
        elif self.ataque == "chuva":
            xs = [jogador.rect.centerx] + [jogador.rect.centerx + d + random.randint(-30, 30)
                                           for d in (-210, -90, 90, 210)]
            for x in xs:
                x = max(self.arena[0] + 50, min(self.arena[1] - 50, x))
                self.pedras.append(Pedra(x))

    def _recuperar(self, duracao=None):
        self.estado, self.t, self.rec_extra = "recuperar", 0.0, duracao

    def update(self, dt, jogador, plataformas, efeitos):
        self.flash = max(0.0, self.flash - dt)
        for o in self.ondas:
            o.update(dt, self.arena)
        for p in self.pedras:
            p.update(dt)
        self.ondas = [o for o in self.ondas if o.vivo]
        self.pedras = [p for p in self.pedras if p.vivo]

        if self.estado == "dormindo":
            mover(self, plataformas, dt)
            return
        self.t += dt

        if self.estado == "idle":
            self.facing = 1 if jogador.rect.centerx > self.rect.centerx else -1
            self.vel.x = self.facing * 85 * self.mult
            if self.t >= 1.3 / self.mult:
                self._escolher_ataque(jogador)
        elif self.estado == "telegrafar":
            self.vel.x = 0
            if self.t >= self.dur("tele"):
                self._comecar_ataque(jogador, efeitos)
        elif self.estado == "atacar":
            if self.ataque == "investida":
                self.vel.x = self.facing * 520 * (1 + (self.mult - 1) * 0.6)
                if self.bateu_parede and self.t > 0.12:
                    self.exausto = True
                    efeitos.tremor = 0.3
                    efeitos.fagulhas(self.rect.centerx + self.facing * 45, self.rect.centery, BRANCO, 14)
                    self._recuperar(1.7 if self.fase == 1 else 1.1)
                elif self.t >= self.dur("ativo"):
                    self._recuperar()
            else:
                self.vel.x = 0
                if self.t >= self.dur("ativo"):
                    self._recuperar()
        elif self.estado == "recuperar":
            self.vel.x = aproximar(self.vel.x, 0, 1500 * dt)
            if self.t >= self.dur("rec"):
                self.estado, self.t, self.exausto = "idle", 0.0, False
        elif self.estado == "caindo":
            self.vel.x = 0
            if self.t >= 2.2:
                self.estado, self.t = "levantando", 0.0
        elif self.estado == "levantando":
            if self.t >= 1.4:
                self.fase = 2
                self.hp_max = self.hp = 28
                self.estado, self.t = "idle", -0.4
                self.eventos.append("fase2")
        else:  # morto
            self.vel.x = 0
        mover(self, plataformas, dt)

    # ---------- desenho ----------
    def desenhar(self, tela, cx, fonte=None):
        r = self.rect.move(-cx, 0)
        if self.estado == "telegrafar":
            prog = min(self.t / self.dur("tele"), 1.0)
            if self.ataque == "pancada":
                retangulo_alpha(tela, (255, 60, 60, int(40 + 100 * prog)), self._zona_pancada().move(-cx, 0))
            elif self.ataque == "investida":
                x0 = r.centerx + self.facing * 70
                x1 = x0 + self.facing * int(120 + 160 * prog)
                pygame.draw.line(tela, VERMELHO, (x0, r.bottom - 20), (x1, r.bottom - 20), 4)
                pygame.draw.polygon(tela, VERMELHO, [(x1, r.bottom - 32), (x1, r.bottom - 8),
                                                     (x1 + self.facing * 18, r.bottom - 20)])
        if self.sprite:
            img = self.sprite if self.facing > 0 else pygame.transform.flip(self.sprite, True, False)
            tela.blit(img, img.get_rect(midbottom=r.midbottom))
        else:
            self._desenhar_forma(tela, r)

    def desenhar_aviso(self, tela, cx, fonte):
        if self.exausto and self.estado == "recuperar":
            img = fonte.render("EXAUSTO!", True, DOURADO)
            tela.blit(img, (self.rect.centerx - cx - img.get_width() // 2, self.rect.top - 30))

    def _aura(self, tela, r, t):
        """Aura roxa e brasas flutuando (fase Eclipse)."""
        aura = pygame.Surface((r.w + 120, r.h + 70), pygame.SRCALPHA)
        for i, a in enumerate((26, 36, 48)):
            pygame.draw.ellipse(aura, (140, 50, 210, a), aura.get_rect().inflate(-i * 22, -i * 16))
        tela.blit(aura, aura.get_rect(center=(r.centerx, r.centery + 10)))
        for k in range(7):
            ex = r.centerx + math.sin(t * 1.7 + k * 1.9) * (36 + k * 5)
            ey = r.bottom - ((t * 55 + k * 41) % (r.h + 40))
            pygame.draw.rect(tela, (200, 120, 255), (int(ex), int(ey), 4, 4))

    def _desenhar_forma(self, tela, r):
        t = pygame.time.get_ticks() / 1000.0
        pal = PALETAS[self.fase]
        branco = self.flash > 0
        pele = BRANCO if branco else pal["pele"]
        sombra = BRANCO if branco else pal["sombra"]
        luz = BRANCO if branco else pal["luz"]
        ctn = pal["contorno"]
        osso = (205, 196, 175)
        metal = (110, 110, 124)
        f = self.facing
        dormindo = self.estado in ("dormindo", "morto")
        baixo = self.estado in ("caindo", "levantando", "morto", "dormindo")
        agachado = self.estado == "telegrafar" and self.ataque == "investida"
        desl = 50 if baixo else (22 if agachado else 0)
        leg_h = int(34 - desl * 0.5)
        top = r.y + 28 + desl
        bot = r.bottom - leg_h + 4
        cxm = r.centerx

        # sombra no chão e aura
        chao = pygame.Surface((130, 18), pygame.SRCALPHA)
        pygame.draw.ellipse(chao, (0, 0, 0, 120), chao.get_rect())
        tela.blit(chao, (cxm - 65, r.bottom - 9))
        if self.fase == 2 and self.estado != "morto":
            self._aura(tela, r, t)

        # pernas com ataduras
        for dx in (-32, 6):
            perna = pygame.Rect(cxm + dx, r.bottom - leg_h, 26, leg_h)
            pygame.draw.rect(tela, sombra, perna)
            pygame.draw.rect(tela, (70, 60, 55), (perna.x, perna.bottom - 9, perna.w, 9))
            pygame.draw.rect(tela, ctn, perna, 2)

        # corcunda + torso largo
        pygame.draw.circle(tela, sombra, (cxm - f * 30, top + 6), 24)
        torso = [(cxm - 50, top), (cxm + 50, top), (cxm + 38, bot), (cxm - 38, bot)]
        pygame.draw.polygon(tela, pele, torso)
        peito = pygame.Rect(0, 0, 54, max(16, int((bot - top) * 0.62)))
        peito.center = (cxm + f * 8, (top + bot) // 2 + 4)
        pygame.draw.ellipse(tela, luz, peito)
        pygame.draw.polygon(tela, ctn, torso, 3)
        if desl == 0:
            pygame.draw.line(tela, sombra, (cxm + f * 18, top + 14), (cxm + f * 4, top + 40), 3)   # cicatrizes
            pygame.draw.line(tela, sombra, (cxm + f * 10, top + 20), (cxm + f * 26, top + 34), 3)
            if self.fase == 2:  # rachaduras brilhando
                zz = [(cxm - 12, top + 8), (cxm - 4, top + 24), (cxm - 16, top + 38), (cxm - 6, top + 56)]
                pygame.draw.lines(tela, (255, 70, 90), False, zz, 3)
        for k in range(9):  # corrente atravessada no peito
            u = k / 8
            px, py = int(cxm - 42 + 80 * u), int(top + 6 + (bot - top - 12) * u)
            pygame.draw.circle(tela, (118, 118, 132), (px, py), 4)
            pygame.draw.circle(tela, ctn, (px, py), 4, 1)

        # tecido rasgado
        j1, j2 = min(bot + 18, r.bottom - 2), min(bot + 8, r.bottom - 3)
        pygame.draw.polygon(tela, pal["pano"], [
            (cxm - 40, bot - 8), (cxm + 40, bot - 8), (cxm + 44, j1), (cxm + 30, j2), (cxm + 18, j1),
            (cxm + 4, j2), (cxm - 10, j1), (cxm - 24, j2), (cxm - 38, j1)])

        # braço de trás
        bx = cxm - f * 50
        braco = pygame.Rect(0, 0, 22, max(28, bot - top - 4))
        braco.midtop = (bx, top + 8)
        pygame.draw.ellipse(tela, sombra, braco)
        pygame.draw.ellipse(tela, ctn, braco, 2)
        pygame.draw.circle(tela, pele, (bx, braco.bottom - 2), 11)
        pygame.draw.circle(tela, ctn, (bx, braco.bottom - 2), 11, 2)

        # cabeça (curvada para frente), chifres/espinhos, presas e olhos
        queda = 12 if dormindo else (6 if baixo else 0)
        hx, hy = cxm + f * 18, top - 10 + queda
        if self.fase == 2:
            for s in (-1, 1):
                chifre = [(hx + s * 12, hy - 12), (hx + s * 34, hy - 46), (hx + s * 6, hy - 18)]
                pygame.draw.polygon(tela, osso, chifre)
                pygame.draw.polygon(tela, ctn, chifre, 2)
        else:
            for dx in (-12, 0, 12):
                esp = [(hx + dx - 4, hy - 16), (hx + dx, hy - 30), (hx + dx + 4, hy - 16)]
                pygame.draw.polygon(tela, osso, esp)
                pygame.draw.polygon(tela, ctn, esp, 2)
        pygame.draw.circle(tela, pele, (hx, hy), 21)
        pygame.draw.circle(tela, ctn, (hx, hy), 21, 2)
        mand = pygame.Rect(hx - 17, hy + 4, 34, 15)
        pygame.draw.rect(tela, sombra, mand, border_radius=4)
        pygame.draw.rect(tela, ctn, mand, 2, border_radius=4)
        for dx in (-11, 9):
            presa = [(hx + dx, hy + 8), (hx + dx + 5, hy + 8), (hx + dx + 2, hy - 5)]
            pygame.draw.polygon(tela, osso, presa)
        pygame.draw.rect(tela, ctn, (hx - 19, hy - 9, 38, 6))  # sobrancelha
        if dormindo:
            for dx in (-8, 6):
                pygame.draw.line(tela, ctn, (hx + dx, hy - 2), (hx + dx + 7, hy - 2), 2)
        else:
            _brilho(tela, (hx + f * 3, hy - 2), 20, pal["olho"], 90 if self.fase == 2 else 40)
            for dx in (-9, 5):
                pygame.draw.rect(tela, pal["olho"], (hx + f * 3 + dx, hy - 4, 7, 5))

        # ombreira com espinhos + braço da clava
        ombro = pygame.Vector2(cxm + f * 42, top + 8)
        mao = pygame.Vector2(cxm + f * 48, top + 34)
        if self.estado == "telegrafar" and self.ataque in ("pancada", "chuva"):
            ang = -100 + random.uniform(-3, 3)
        elif self.estado == "atacar" and self.ataque == "pancada":
            ang = 60 if self.t > 0.08 else -100 + 160 * (self.t / 0.08)
        else:
            ang = 50
        d = pygame.Vector2(1, 0).rotate(ang)
        d.x *= f
        ponta = mao + d * 90
        pygame.draw.line(tela, ctn, ombro, mao, 24)
        pygame.draw.line(tela, pele, ombro, mao, 18)
        pygame.draw.circle(tela, metal, (int(ombro.x), int(ombro.y)), 17)
        pygame.draw.circle(tela, ctn, (int(ombro.x), int(ombro.y)), 17, 2)
        for a in (-120, -90, -60):
            u = pygame.Vector2(1, 0).rotate(a)
            n = pygame.Vector2(-u.y, u.x)
            b0 = ombro + u * 15
            pygame.draw.polygon(tela, (150, 150, 165), [b0 + n * 4, ombro + u * 28, b0 - n * 4])
        pygame.draw.line(tela, ctn, mao, ponta, 20)
        pygame.draw.line(tela, (84, 58, 38), mao, ponta, 14)
        pygame.draw.circle(tela, (84, 58, 38), (int(ponta.x), int(ponta.y)), 18)
        pygame.draw.circle(tela, ctn, (int(ponta.x), int(ponta.y)), 18, 2)
        for a in range(0, 360, 60):
            u = pygame.Vector2(1, 0).rotate(a)
            n = pygame.Vector2(-u.y, u.x)
            b0 = ponta + u * 15
            pygame.draw.polygon(tela, (150, 150, 165), [b0 + n * 4, ponta + u * 26, b0 - n * 4])
        if self.fase == 2:
            _brilho(tela, (int(ponta.x), int(ponta.y)), 22, (190, 110, 255), 110)
            pygame.draw.circle(tela, (210, 140, 255), (int(ponta.x), int(ponta.y)), 5)


PALETAS = {
    1: dict(pele=(80, 116, 66), sombra=(48, 76, 46), luz=(118, 156, 90), contorno=(10, 18, 12),
            olho=(235, 215, 110), pano=(88, 28, 30)),
    2: dict(pele=(98, 58, 134), sombra=(56, 30, 84), luz=(146, 96, 184), contorno=(16, 6, 24),
            olho=(255, 40, 50), pano=(24, 10, 34)),
}


def _brilho(tela, pos, raio, cor, alpha):
    s = pygame.Surface((raio * 2, raio * 2), pygame.SRCALPHA)
    for k, a in ((1.0, alpha // 3), (0.66, alpha // 2), (0.33, alpha)):
        pygame.draw.circle(s, (*cor, a), (raio, raio), int(raio * k))
    tela.blit(s, (pos[0] - raio, pos[1] - raio))
