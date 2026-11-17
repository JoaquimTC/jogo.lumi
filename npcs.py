"""Diálogos, comerciantes e personagens (NPCs e inimigos comuns)."""
import pygame
from settings import (CHAO_Y, LARGURA, ALTURA, BRANCO, DOURADO, CINZA, ROXO,
                      carregar_imagem, quebrar_texto, retangulo_alpha)
from combat import mover


class NPC:
    def __init__(self, x, nome, falas, cor, mercador=False):
        self.rect = pygame.Rect(x, CHAO_Y - 60, 36, 60)
        self.nome = nome
        self.falas = falas
        self.cor = cor
        self.mercador = mercador
        self.sprite = carregar_imagem(("mercador" if mercador else "anciao") + ".png", (52, 70))

    def perto(self, jogador):
        return abs(jogador.rect.centerx - self.rect.centerx) < 80

    def desenhar(self, tela, cx, perto, fonte):
        r = self.rect.move(-cx, 0)
        if self.sprite:
            tela.blit(self.sprite, self.sprite.get_rect(midbottom=r.midbottom))
        else:
            pygame.draw.rect(tela, self.cor, r, border_radius=10)
            pygame.draw.circle(tela, (235, 215, 190), (r.centerx, r.y + 10), 11)
            if self.mercador:  # mochila
                pygame.draw.rect(tela, (120, 80, 50), (r.right - 6, r.y + 20, 16, 26), border_radius=4)
        if perto:
            img = fonte.render("[E] falar", True, DOURADO)
            tela.blit(img, (r.centerx - img.get_width() // 2, r.y - 26))


class Dialogo:
    VEL = 45  # caracteres por segundo

    def __init__(self, nome, falas, mercador=False):
        self.nome = nome
        self.falas = falas
        self.mercador = mercador
        self.i = 0
        self.t = 0.0

    def update(self, dt):
        self.t += dt

    def avancar(self):
        """Completa a fala atual ou passa para a próxima. True quando acabou."""
        texto = self.falas[self.i]
        if int(self.t * self.VEL) < len(texto):
            self.t = len(texto) / self.VEL + 0.01
            return False
        self.i += 1
        self.t = 0.0
        return self.i >= len(self.falas)

    def desenhar(self, tela, fonte, fonte_p):
        caixa = pygame.Rect(40, ALTURA - 170, LARGURA - 80, 140)
        retangulo_alpha(tela, (8, 8, 20, 230), caixa)
        pygame.draw.rect(tela, DOURADO, caixa, 2)
        tela.blit(fonte.render(self.nome, True, DOURADO), (caixa.x + 18, caixa.y + 10))
        texto = self.falas[self.i][:int(self.t * self.VEL)]
        for k, linha in enumerate(quebrar_texto(texto, fonte_p, caixa.w - 36)):
            tela.blit(fonte_p.render(linha, True, BRANCO), (caixa.x + 18, caixa.y + 48 + k * 24))
        dica = fonte_p.render("[E] continuar", True, CINZA)
        tela.blit(dica, (caixa.right - dica.get_width() - 16, caixa.bottom - 28))


class Loja:
    ITENS = [
        ("Poção de Luz", "Cura 2 corações", 4, "pocao"),
        ("Fragmento de Coração", "+1 coração máximo (até 3x)", 12, "fragmento"),
        ("Sair", "", 0, "sair"),
    ]

    def __init__(self):
        self.sel = 0
        self.msg = ""

    def tecla(self, key, jogador, centelhas):
        """Retorna (centelhas_restantes, fechar_loja)."""
        if key in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(self.ITENS)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(self.ITENS)
        elif key == pygame.K_ESCAPE:
            return centelhas, True
        elif key in (pygame.K_RETURN, pygame.K_e, pygame.K_SPACE):
            _, _, custo, tipo = self.ITENS[self.sel]
            if tipo == "sair":
                return centelhas, True
            if centelhas < custo:
                self.msg = "Centelhas insuficientes."
            elif tipo == "pocao":
                if jogador.hp >= jogador.hp_max:
                    self.msg = "Sua vida já está cheia."
                else:
                    centelhas -= custo
                    jogador.curar(2)
                    self.msg = "Glub glub... bem melhor!"
            elif tipo == "fragmento":
                if jogador.extra_vida_loja >= 3:
                    self.msg = "Estou sem fragmentos."
                else:
                    centelhas -= custo
                    jogador.extra_vida_loja += 1
                    jogador.hp_max += 1
                    jogador.hp += 1
                    self.msg = "Seu coração brilha mais forte."
        return centelhas, False

    def desenhar(self, tela, fonte, fonte_p, centelhas):
        retangulo_alpha(tela, (5, 5, 15, 215), pygame.Rect(0, 0, LARGURA, ALTURA))
        t = fonte.render("Mercador", True, DOURADO)
        tela.blit(t, (LARGURA // 2 - t.get_width() // 2, 50))
        c = fonte_p.render(f"Suas centelhas: {centelhas}", True, BRANCO)
        tela.blit(c, (LARGURA // 2 - c.get_width() // 2, 92))
        y = 150
        for i, (nome, desc, custo, tipo) in enumerate(self.ITENS):
            ativo = i == self.sel
            caixa = pygame.Rect(200, y, LARGURA - 400, 62)
            retangulo_alpha(tela, (60, 70, 120, 200) if ativo else (30, 30, 50, 160), caixa)
            if ativo:
                pygame.draw.rect(tela, DOURADO, caixa, 2)
            tela.blit(fonte_p.render(nome, True, BRANCO), (caixa.x + 14, caixa.y + 8))
            tela.blit(fonte_p.render(desc, True, CINZA), (caixa.x + 14, caixa.y + 34))
            if tipo != "sair":
                p = fonte_p.render(f"{custo} centelhas", True, DOURADO)
                tela.blit(p, (caixa.right - p.get_width() - 14, caixa.y + 20))
            y += 74
        if self.msg:
            m = fonte_p.render(self.msg, True, DOURADO)
            tela.blit(m, (LARGURA // 2 - m.get_width() // 2, ALTURA - 90))


class Sombra:
    """Inimigo comum: patrulha, vira nas bordas e causa dano por contato."""

    def __init__(self, x, y, patrulha=140):
        self.rect = pygame.Rect(x, y, 34, 30)
        self.pos = pygame.Vector2(self.rect.topleft)
        self.vel = pygame.Vector2(0, 0)
        self.no_chao = False
        self.bateu_parede = False
        self.usa_gravidade = True
        self.hp = 2
        self.vivo = True
        self.morreu_agora = False
        self.dano = 1
        self.golpe_id = 0
        self.dir = -1
        self.flash = 0.0
        self.stun = 0.0
        self.origem_x = x
        self.patrulha = patrulha
        self.sprite = carregar_imagem("sombra.png", (40, 36))

    def update(self, dt, plataformas):
        self.flash = max(0.0, self.flash - dt)
        if self.stun > 0:
            self.stun -= dt
            self.vel.x *= 0.9
        else:
            self.vel.x = self.dir * 70
        mover(self, plataformas, dt)
        if self.stun <= 0:
            sonda = pygame.Rect(self.rect.centerx + self.dir * (self.rect.w // 2 + 6),
                                self.rect.bottom + 4, 4, 8)
            sem_chao = self.no_chao and not any(sonda.colliderect(p) for p in plataformas)
            fora = abs(self.rect.x - self.origem_x) > self.patrulha and \
                (self.rect.x - self.origem_x) * self.dir > 0
            if self.bateu_parede or sem_chao or fora:
                self.dir *= -1

    def receber_dano(self, dano, direcao):
        self.hp -= dano
        self.flash = 0.12
        self.stun = 0.25
        self.vel.x = direcao * 220
        self.vel.y = -200
        if self.hp <= 0:
            self.vivo = False
            self.morreu_agora = True
        return True

    def caixas_dano(self):
        return [self.rect.inflate(-6, -6)] if self.vivo else []

    def desenhar(self, tela, cx):
        r = self.rect.move(-cx, 0)
        if self.sprite:
            img = self.sprite if self.dir < 0 else pygame.transform.flip(self.sprite, True, False)
            tela.blit(img, img.get_rect(midbottom=r.midbottom))
            return
        cor = BRANCO if self.flash > 0 else (40, 25, 60)
        pygame.draw.ellipse(tela, cor, r)
        pygame.draw.circle(tela, ROXO, (r.centerx - 6, r.centery - 3), 3)
        pygame.draw.circle(tela, ROXO, (r.centerx + 6, r.centery - 3), 3)
