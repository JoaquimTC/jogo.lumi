"""Cenários, mapa e exploração: fases, plataformas, checkpoints, centelhas e portal."""
import math
import random
import pygame
from settings import (LARGURA, ALTURA, CHAO_Y, BRANCO, DOURADO, AZUL_LUZ, ROXO)
from npcs import NPC, Sombra


class Espinho:
    def __init__(self, x, largura=90):
        self.rect = pygame.Rect(x, CHAO_Y - 24, largura, 24)
        self.dano = 1
        self.golpe_id = 0
        self.vivo = True

    def caixas_dano(self):
        return [self.rect.inflate(-8, -6)]

    def desenhar(self, tela, cx):
        r = self.rect.move(-cx, 0)
        n = max(1, r.w // 18)
        for i in range(n):
            x = r.x + i * (r.w / n)
            pygame.draw.polygon(tela, (170, 170, 190),
                                [(x, r.bottom), (x + r.w / n / 2, r.top), (x + r.w / n, r.bottom)])


def _chao(trechos):
    return [pygame.Rect(x, CHAO_Y, w, ALTURA - CHAO_Y + 80) for x, w in trechos]


def _flut(itens):
    return [pygame.Rect(x, y, w, 22) for x, y, w in itens]


class Fase:
    def __init__(self, nome, largura, chao, flutuantes, spawn, portal_x, cores,
                 musica="", espinhos=(), checkpoints=(), sombras=(), npcs=(),
                 centelhas_extra=(), boss=False, paredes=False, eclipse=False, lua=False):
        self.nome = nome
        self.largura = largura
        self.flutuantes = _flut(flutuantes)
        base = _chao(chao)
        if paredes:  # arena fechada
            base += [pygame.Rect(-60, -200, 60, ALTURA + 400),
                     pygame.Rect(largura, -200, 60, ALTURA + 400)]
        self.plataformas = base + self.flutuantes
        # chão e paredes apenas: inimigos altos (Ogro) não colidem com plataformas flutuantes
        self.solidos_grandes = base
        self.spawn = spawn
        self.cores = cores
        self.musica = musica
        self.boss = boss
        self.espinhos = [Espinho(x) for x in espinhos]
        self.checkpoints = [{"rect": pygame.Rect(x, CHAO_Y - 80, 22, 80), "ativo": False}
                            for x in checkpoints]
        self.sombras = [Sombra(x, CHAO_Y - 30, p) for x, p in sombras]
        self.npcs = list(npcs)
        self.centelhas = [pygame.Rect(p.centerx + d - 8, p.y - 34, 16, 16)
                          for p in self.flutuantes for d in (-20, 20)]
        self.centelhas += [pygame.Rect(x, y, 16, 16) for x, y in centelhas_extra]
        self.portal = pygame.Rect(portal_x, CHAO_Y - 110, 56, 110)
        self.portal_ativo = not boss
        self.t = 0.0
        self.eclipse = eclipse
        self.lua = lua
        self._fundo = self._gerar_fundo()
        self._nevoa, self._wisp = self._gerar_nevoa()
        self._astro = self._gerar_astro()
        rnd = random.Random(nome)
        self._arvores = {f: [(x, rnd.randint(90, 220)) for x in
                             range(0, int(largura * f) + LARGURA + 200, rnd.randint(70, 130))]
                         for f in (0.25, 0.5)}

    def _gerar_fundo(self):
        topo, base = self.cores
        s = pygame.Surface((LARGURA, ALTURA))
        for y in range(ALTURA):
            k = y / ALTURA
            s.fill(tuple(int(topo[i] + (base[i] - topo[i]) * k) for i in range(3)), (0, y, LARGURA, 1))
        return s

    def update(self, dt):
        self.t += dt

    def coletar(self, jogador):
        pegas = [c for c in self.centelhas if c.colliderect(jogador.rect.inflate(10, 10))]
        self.centelhas = [c for c in self.centelhas if c not in pegas]
        return len(pegas)

    def checar_checkpoints(self, jogador):
        """Retorna a posição de respawn se um checkpoint novo foi ativado."""
        for cp in self.checkpoints:
            if not cp["ativo"] and cp["rect"].colliderect(jogador.rect):
                cp["ativo"] = True
                return (cp["rect"].x, CHAO_Y - jogador.rect.h)
        return None

    def no_portal(self, jogador):
        return self.portal_ativo and self.portal.colliderect(jogador.rect)

    def _gerar_nevoa(self):
        cor = tuple(min(255, int(c * 1.6) + 18) for c in self.cores[1])
        s = pygame.Surface((LARGURA, 150), pygame.SRCALPHA)
        for y in range(150):
            s.fill((*cor, int(95 * (y / 150) ** 1.6)), (0, y, LARGURA, 1))
        wisp = pygame.Surface((340, 50), pygame.SRCALPHA)
        pygame.draw.ellipse(wisp, (*cor, 40), wisp.get_rect())
        pygame.draw.ellipse(wisp, (*cor, 40), wisp.get_rect().inflate(-80, -20))
        return s, wisp

    def _gerar_astro(self):
        if self.eclipse:  # sol negro com coroa vermelha
            s = pygame.Surface((300, 300), pygame.SRCALPHA)
            for i in range(10, 0, -1):
                pygame.draw.circle(s, (210, 60, 40, 8 + (10 - i) * 3), (150, 150), 46 + i * 9)
            pygame.draw.circle(s, (6, 2, 10), (150, 150), 46)
            pygame.draw.circle(s, (240, 110, 60), (150, 150), 46, 3)
            return s
        if self.lua:  # lua pálida
            s = pygame.Surface((140, 140), pygame.SRCALPHA)
            for i in range(5, 0, -1):
                pygame.draw.circle(s, (190, 205, 210, 10 + (5 - i) * 4), (70, 70), 30 + i * 7)
            pygame.draw.circle(s, (205, 218, 222), (70, 70), 30)
            return s
        return None

    @staticmethod
    def _arvore_morta(tela, sx, h, cor):
        tr = max(8, h // 12)
        pygame.draw.polygon(tela, cor, [(sx - tr, CHAO_Y), (sx - tr // 2, CHAO_Y - h),
                                        (sx + tr // 2, CHAO_Y - h), (sx + tr, CHAO_Y)])
        e = max(3, tr // 2)
        pygame.draw.line(tela, cor, (sx, CHAO_Y - h * 0.62), (sx - h * 0.28, CHAO_Y - h * 0.92), e)
        pygame.draw.line(tela, cor, (sx, CHAO_Y - h * 0.45), (sx + h * 0.30, CHAO_Y - h * 0.78), e)
        pygame.draw.line(tela, cor, (sx - h * 0.28, CHAO_Y - h * 0.92), (sx - h * 0.40, CHAO_Y - h * 0.90), 3)
        pygame.draw.line(tela, cor, (sx, CHAO_Y - h), (sx + h * 0.08, CHAO_Y - h - 20), 3)

    def desenhar(self, tela, cx):
        tela.blit(self._fundo, (0, 0))
        if self._astro:
            tela.blit(self._astro, self._astro.get_rect(center=(int(LARGURA * 0.70 - cx * 0.03), 115)))
        base = self.cores[1]
        for f, k in ((0.25, 0.55), (0.5, 0.32)):
            cor = tuple(int(c * k) for c in base)
            for x, h in self._arvores[f]:
                sx = int(x - cx * f)
                if -90 < sx < LARGURA + 90:
                    self._arvore_morta(tela, sx, h, cor)
        tela.blit(self._nevoa, (0, CHAO_Y - 120))
        for k in range(5):
            x = (k * 270 + self.t * (14 + 9 * (k % 2))) % (LARGURA + 400) - 200
            tela.blit(self._wisp, (x, CHAO_Y - 50 + (k % 3) * 10 + math.sin(self.t * 0.6 + k) * 6))
        for p in self.plataformas:
            r = p.move(-cx, 0)
            if r.right < 0 or r.left > LARGURA:
                continue
            pygame.draw.rect(tela, (22, 17, 24), r)
            pygame.draw.rect(tela, (38, 62, 48), (r.x, r.y, r.w, 7))
            pygame.draw.rect(tela, (60, 92, 70), (r.x, r.y, r.w, 2))
        for e in self.espinhos:
            e.desenhar(tela, cx)
        for cp in self.checkpoints:
            r = cp["rect"].move(-cx, 0)
            pygame.draw.rect(tela, (90, 70, 60), (r.centerx - 3, r.y, 6, r.h))
            cor = DOURADO if cp["ativo"] else (80, 80, 95)
            pygame.draw.circle(tela, cor, (r.centerx, r.y + 6), 9)
            if cp["ativo"]:
                pygame.draw.circle(tela, (255, 240, 180), (r.centerx, r.y + 6), 4)
        for c in self.centelhas:
            y = c.y + math.sin(self.t * 4 + c.x) * 4
            pos = (int(c.centerx - cx), int(y + 8))
            pygame.draw.circle(tela, (120, 100, 40), pos, 12, 1)
            pygame.draw.polygon(tela, DOURADO, [(pos[0], pos[1] - 8), (pos[0] + 5, pos[1]),
                                                (pos[0], pos[1] + 8), (pos[0] - 5, pos[1])])
        if self.portal_ativo:
            r = self.portal.move(-cx, 0)
            pulso = int(4 * math.sin(self.t * 5))
            pygame.draw.ellipse(tela, ROXO, r.inflate(pulso, pulso))
            pygame.draw.ellipse(tela, AZUL_LUZ, r.inflate(-20 + pulso, -30 + pulso), 3)

def criar_fase(i):
    if i == 0:
        return Fase(
            "Floresta dos Sussurros", 3800,
            chao=[(0, 1100), (1250, 800), (2200, 700), (3050, 750)],
            flutuantes=[(560, 370, 140), (780, 310, 140), (1000, 370, 120), (1500, 360, 160),
                        (1780, 300, 140), (2400, 370, 160), (2650, 310, 140), (3300, 360, 140)],
            spawn=(80, CHAO_Y - 56), portal_x=3640, cores=((6, 12, 16), (22, 46, 42)),
            musica="floresta.ogg", lua=True, checkpoints=(1300, 2300),
            sombras=[(800, 120), (1500, 160), (1850, 120), (2500, 150), (2800, 120), (3400, 150)],
            npcs=[NPC(400, "Velha Lanterna", [
                "Ah, uma faísca de luz! Que bom te ver, pequeno Lumi.",
                "Mova-se com A/D ou as setas. Pule com W, Espaço ou seta pra cima.",
                "Ataque com J: três golpes seguidos formam um combo. O terceiro é o mais forte!",
                "Esquive com K: durante a esquiva nada te machuca. Se esquivar na hora certa, o tempo desacelera.",
                "Junte centelhas: a cada cinco você ganha um ponto de habilidade. Abra a árvore com Tab.",
                "Acenda as lanternas pelo caminho, elas guardam seu progresso. Boa sorte!"], (150, 120, 80))],
            centelhas_extra=[(300, 420), (700, 420), (1300, 420), (2100, 420), (2900, 420), (3500, 420)])
    if i == 1:
        return Fase(
            "Vale da Eclipse", 4400,
            chao=[(0, 900), (1050, 600), (1800, 450), (2400, 600), (3150, 500), (3800, 600)],
            flutuantes=[(400, 370, 140), (1200, 360, 140), (1450, 300, 140), (2000, 350, 140),
                        (2600, 360, 140), (2850, 290, 130), (3300, 370, 140), (3500, 300, 120)],
            spawn=(80, CHAO_Y - 56), portal_x=4250, cores=((8, 3, 16), (58, 16, 44)),
            musica="vale.ogg", eclipse=True, espinhos=(1350, 2750, 3250), checkpoints=(1100, 2450, 3200),
            sombras=[(600, 140), (1150, 120), (1350, 80), (1900, 120), (2500, 150),
                     (2800, 100), (3300, 120), (3900, 150)],
            npcs=[NPC(500, "Mercador Errante", [
                "Psiu! Nada de olhar torto, eu só vendo luz engarrafada.",
                "Centelhas por poções e fragmentos de coração. Preço justo!"],
                (120, 90, 150), mercador=True)],
            centelhas_extra=[(300, 420), (700, 420), (1500, 420), (2200, 420), (2900, 420), (3600, 420), (4100, 420)])
    return Fase(
        "Covil do Ogro", 1400, chao=[(0, 1400)],
        flutuantes=[(300, 350, 140), (960, 350, 140)],
        spawn=(80, CHAO_Y - 56), portal_x=1300, cores=((12, 3, 6), (66, 20, 22)),
        musica="boss.ogg", checkpoints=(120,), boss=True, paredes=True)


NUM_FASES = 3
