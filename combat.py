"""Ataques, dano, colisões e esquivas.

Regras:
- toda entidade tem .rect (hurtbox), .pos, .vel e usa mover() para colidir;
- 'perigo' é qualquer objeto com caixas_dano() -> [Rect], .dano e .golpe_id;
- esquivar (K) dá invencibilidade; ser "atingido" durante a esquiva = esquiva perfeita.
"""
import random
import pygame
from settings import (GRAVIDADE, VEL_QUEDA_MAX, BRANCO, DOURADO, AZUL_LUZ,
                      VERMELHO)


def mover(ent, plataformas, dt):
    """Movimento com colisão eixo a eixo contra uma lista de Rects."""
    if getattr(ent, "usa_gravidade", True):
        ent.vel.y = min(ent.vel.y + GRAVIDADE * dt, VEL_QUEDA_MAX)

    ent.pos.x += ent.vel.x * dt
    ent.rect.x = round(ent.pos.x)
    ent.bateu_parede = False
    for p in plataformas:
        if ent.rect.colliderect(p):
            if ent.vel.x > 0:
                ent.rect.right = p.left
            elif ent.vel.x < 0:
                ent.rect.left = p.right
            else:
                continue
            ent.pos.x = ent.rect.x
            ent.bateu_parede = True

    ent.pos.y += ent.vel.y * dt
    ent.rect.y = round(ent.pos.y)
    ent.no_chao = False
    for p in plataformas:
        if ent.rect.colliderect(p):
            if ent.vel.y > 0:
                ent.rect.bottom = p.top
                ent.no_chao = True
            elif ent.vel.y < 0:
                ent.rect.top = p.bottom
            else:
                continue
            ent.pos.y = ent.rect.y
            ent.vel.y = 0


class Efeitos:
    """Hitstop, câmera lenta, tremor de tela, partículas e textos flutuantes."""

    def __init__(self):
        self.textos = []
        self.particulas = []
        self.hitstop = 0.0
        self.slowmo = 0.0
        self.tremor = 0.0

    def texto(self, x, y, txt, cor=BRANCO):
        self.textos.append({"x": x, "y": y, "txt": txt, "cor": cor, "vida": 1.0})

    def fagulhas(self, x, y, cor=DOURADO, n=8):
        for _ in range(n):
            v = pygame.Vector2(random.uniform(-220, 220), random.uniform(-260, -40))
            self.particulas.append({"pos": pygame.Vector2(x, y), "vel": v, "cor": cor,
                                    "vida": random.uniform(0.25, 0.5)})

    def ajustar_dt(self, dt):
        if self.hitstop > 0:
            return 0.0
        if self.slowmo > 0:
            return dt * 0.35
        return dt

    def update(self, dt_real):
        self.hitstop = max(0.0, self.hitstop - dt_real)
        self.slowmo = max(0.0, self.slowmo - dt_real)
        self.tremor = max(0.0, self.tremor - dt_real)
        for t in self.textos:
            t["y"] -= 40 * dt_real
            t["vida"] -= dt_real
        self.textos = [t for t in self.textos if t["vida"] > 0]
        for p in self.particulas:
            p["vel"].y += 900 * dt_real
            p["pos"] += p["vel"] * dt_real
            p["vida"] -= dt_real
        self.particulas = [p for p in self.particulas if p["vida"] > 0]

    def deslocamento_tremor(self):
        if self.tremor <= 0:
            return 0
        return int(random.uniform(-1, 1) * min(self.tremor, 0.3) * 30)

    def desenhar_particulas(self, tela, cx):
        for p in self.particulas:
            pygame.draw.rect(tela, p["cor"], (int(p["pos"].x - cx), int(p["pos"].y), 4, 4))

    def desenhar_textos(self, tela, cx, fonte):
        for t in self.textos:
            img = fonte.render(t["txt"], True, t["cor"])
            tela.blit(img, (t["x"] - cx - img.get_width() // 2, t["y"]))


def golpe_do_jogador(jogador, alvos, efeitos):
    """Aplica a katana do jogador nos alvos (cada alvo só é atingido 1x por golpe)."""
    caixa = jogador.hitbox_ataque()
    if not caixa:
        return 0
    acertos = 0
    for alvo in alvos:
        if not alvo.vivo or id(alvo) in jogador.acertados:
            continue
        if caixa.colliderect(alvo.rect):
            jogador.acertados.add(id(alvo))
            dano = jogador.dano_do_golpe()
            if alvo.receber_dano(dano, jogador.facing):
                acertos += 1
                efeitos.fagulhas(*caixa.clamp(alvo.rect).center, DOURADO)
                efeitos.texto(alvo.rect.centerx, alvo.rect.top - 6, str(dano), DOURADO)
                final = jogador.atq_step == 3
                efeitos.hitstop = 0.09 if final else 0.05
                if final:
                    efeitos.tremor = 0.15
    return acertos


def perigos_no_jogador(jogador, perigos, efeitos):
    """Testa perigos contra o jogador. Retorna True se ele tomou dano."""
    for p in perigos:
        if not getattr(p, "vivo", True):
            continue
        for caixa in p.caixas_dano():
            if not caixa.colliderect(jogador.rect):
                continue
            if jogador.esq_t > 0:  # esquiva perfeita
                chave = (id(p), getattr(p, "golpe_id", 0))
                if chave not in jogador.esquivados:
                    jogador.esquivados.add(chave)
                    jogador.esq_cd = 0.0  # devolve o cooldown
                    efeitos.slowmo = 0.35
                    efeitos.texto(jogador.rect.centerx, jogador.rect.top - 12, "Esquiva!", AZUL_LUZ)
                break
            if jogador.receber_dano(p.dano, caixa.centerx):
                efeitos.tremor = 0.2
                efeitos.fagulhas(jogador.rect.centerx, jogador.rect.centery, VERMELHO, 10)
                return True
    return False
