"""Personagem, movimentação e katana (combo de 3 golpes)."""
import pygame
from settings import (carregar_imagem, carregar_som, aproximar, AZUL_LUZ, BRANCO,
                      PRETO, DOURADO)
from combat import mover

# Cada golpe: dano, duração total, janela ativa (hitbox), alcance, altura, avanço e giro.
GOLPES = {
    1: dict(dano=1, dur=0.30, ativo=(0.07, 0.19), alcance=62, alt=46, avanco=140, giro=False),
    2: dict(dano=1, dur=0.30, ativo=(0.07, 0.19), alcance=70, alt=50, avanco=140, giro=True),
    3: dict(dano=3, dur=0.52, ativo=(0.18, 0.32), alcance=96, alt=74, avanco=320, giro=False),
}


class Jogador:
    VEL = 280
    FORCA_PULO = 780
    VEL_ESQUIVA = 560
    DUR_ESQUIVA = 0.22

    def __init__(self, x, y):
        self.rect = pygame.Rect(x, y, 30, 56)
        self.pos = pygame.Vector2(self.rect.topleft)
        self.vel = pygame.Vector2(0, 0)
        self.no_chao = False
        self.bateu_parede = False
        self.usa_gravidade = True
        self.facing = 1
        self.dir_input = 0

        self.hp_max = 5
        self.hp = 5
        self.invul = 0.0
        self.stun = 0.0

        # bônus aplicados por skills.py / loja
        self.bonus_dano = 0
        self.bonus_alcance = 0
        self.cd_esquiva = 0.75
        self.pulos_max = 1
        self.extra_vida_loja = 0

        self.coyote = 0.0
        self.buffer_pulo = 0.0
        self.pulos_extra_usados = 0

        self.esq_t = 0.0
        self.esq_cd = 0.0
        self.esquivados = set()
        self.rastros = []        # frames fantasmas do dash
        self._rastro_t = 0.0

        self.atq_step = 0
        self.atq_t = 0.0
        self.atq_cd = 0.0
        self.janela = 0.0
        self.proximo_golpe = 1
        self.buffer_atq = False
        self.acertados = set()

        self.sprite = carregar_imagem("jogador.png", (48, 64))
        self.som_katana = carregar_som("katana.wav")
        self.som_pulo = carregar_som("pulo.wav")
        self.som_esquiva = carregar_som("esquiva.wav")
        self.som_dano = carregar_som("dano.wav")

    # ---------- estado ----------
    @property
    def invulneravel(self):
        return self.invul > 0 or self.esq_t > 0

    def reaparecer(self, x, y, vida_cheia=True):
        self.rect.topleft = (x, y)
        self.pos = pygame.Vector2(x, y)
        self.vel = pygame.Vector2(0, 0)
        self.stun = 0.0
        self.esq_t = 0.0
        self.usa_gravidade = True
        self.atq_step = 0
        self.janela = 0.0
        self.proximo_golpe = 1
        self.invul = 1.0
        if vida_cheia:
            self.hp = self.hp_max

    def curar(self, n):
        self.hp = min(self.hp_max, self.hp + n)

    def dano_do_golpe(self):
        return GOLPES[self.atq_step]["dano"] + self.bonus_dano

    def receber_dano(self, dano, origem_x):
        if self.invulneravel:
            return False
        self.hp -= dano
        self.invul = 1.0
        self.stun = 0.22
        self.atq_step = 0
        self.buffer_atq = False
        self.janela = 0.0
        self.proximo_golpe = 1
        direcao = 1 if self.rect.centerx >= origem_x else -1
        self.vel.x = direcao * 320
        self.vel.y = -380
        self.no_chao = False
        self.som_dano.play()
        return True

    # ---------- ações (chamadas pelos eventos de tecla) ----------
    def pular(self):
        self.buffer_pulo = 0.12

    def soltar_pulo(self):
        if self.vel.y < -200:
            self.vel.y *= 0.5  # pulo variável

    def esquivar(self):
        if self.esq_cd > 0 or self.stun > 0 or self.esq_t > 0:
            return
        self.esq_t = self.DUR_ESQUIVA
        self.esq_cd = self.cd_esquiva
        if self.dir_input:
            self.facing = self.dir_input
        self.atq_step = 0
        self.buffer_atq = False
        self.janela = 0.0
        self.proximo_golpe = 1
        self.esquivados.clear()
        self._rastro_t = 0.0
        self.som_esquiva.play()

    def atacar(self):
        if self.esq_t > 0 or self.stun > 0:
            return
        if self.atq_step:
            self.buffer_atq = True  # guarda o input para encadear o próximo golpe
        elif self.atq_cd <= 0:
            self._iniciar_golpe(self.proximo_golpe)

    def _iniciar_golpe(self, n):
        g = GOLPES[n]
        self.atq_step = n
        self.atq_t = 0.0
        self.buffer_atq = False
        self.acertados = set()
        self.janela = 0.0
        self.proximo_golpe = n + 1 if n < 3 else 1
        if self.dir_input:
            self.facing = self.dir_input
        self.vel.x = self.facing * g["avanco"]
        self.som_katana.play()

    def hitbox_ataque(self):
        if not self.atq_step:
            return None
        g = GOLPES[self.atq_step]
        a0, a1 = g["ativo"]
        if not (a0 <= self.atq_t <= a1):
            return None
        alc = g["alcance"] + self.bonus_alcance
        alt = g["alt"]
        y = self.rect.centery - alt // 2
        if g["giro"]:
            return pygame.Rect(self.rect.left - alc, y, alc * 2 + self.rect.w, alt)
        if self.facing > 0:
            return pygame.Rect(self.rect.right - 6, y, alc, alt)
        return pygame.Rect(self.rect.left + 6 - alc, y, alc, alt)

    # ---------- update ----------
    def update(self, dt, keys, plataformas):
        self.invul = max(0.0, self.invul - dt)
        self.stun = max(0.0, self.stun - dt)
        self.esq_cd = max(0.0, self.esq_cd - dt)
        self.atq_cd = max(0.0, self.atq_cd - dt)
        self.buffer_pulo = max(0.0, self.buffer_pulo - dt)
        self.coyote = max(0.0, self.coyote - dt)

        if self.no_chao:
            self.coyote = 0.1
            self.pulos_extra_usados = 0

        self.dir_input = int(bool(keys[pygame.K_d] or keys[pygame.K_RIGHT])) - \
            int(bool(keys[pygame.K_a] or keys[pygame.K_LEFT]))

        if self.esq_t > 0:
            self.esq_t -= dt
            self.usa_gravidade = False
            self.vel.x = self.facing * self.VEL_ESQUIVA
            self.vel.y = 0
            if self.esq_t <= 0:
                self.esq_t = 0.0
                self.usa_gravidade = True
                self.vel.x *= 0.3
        else:
            self.usa_gravidade = True
            self._movimento(dt)
            self._pulo()
            self._atualizar_ataque(dt)

        # rastro azul do dash: um "framezinho" a cada 0.04s
        if self.esq_t > 0:
            self._rastro_t -= dt
            if self._rastro_t <= 0:
                self._rastro_t = 0.04
                self.rastros.append({"x": self.rect.x, "y": self.rect.y,
                                     "f": self.facing, "vida": 0.32})
        for g in self.rastros:
            g["vida"] -= dt
        self.rastros = [g for g in self.rastros if g["vida"] > 0]

        mover(self, plataformas, dt)

    def _movimento(self, dt):
        if self.stun > 0:
            self.vel.x = aproximar(self.vel.x, 0, 900 * dt)
            return
        atacando = self.atq_step > 0
        if self.dir_input and not atacando:
            self.facing = self.dir_input
        alvo = self.dir_input * self.VEL * (0.35 if atacando else 1.0)
        accel = 1400 if atacando else (3200 if self.no_chao else 2200)
        self.vel.x = aproximar(self.vel.x, alvo, accel * dt)

    def _pulo(self):
        if self.buffer_pulo > 0 and self.stun <= 0:
            if self.coyote > 0:
                self._saltar()
            elif self.pulos_extra_usados < self.pulos_max - 1:
                self.pulos_extra_usados += 1
                self._saltar()

    def _saltar(self):
        self.vel.y = -self.FORCA_PULO
        self.buffer_pulo = 0.0
        self.coyote = 0.0
        self.no_chao = False
        self.som_pulo.play()

    def _atualizar_ataque(self, dt):
        if self.atq_step:
            self.atq_t += dt
            if self.atq_t >= GOLPES[self.atq_step]["dur"]:
                n = self.atq_step
                self.atq_step = 0
                quer_encadear = self.buffer_atq
                self.buffer_atq = False
                if quer_encadear and n < 3:
                    self._iniciar_golpe(n + 1)
                elif n == 3:
                    self.atq_cd = 0.45
                    self.proximo_golpe = 1
                else:
                    self.janela = 0.28  # tempo extra para continuar o combo
        elif self.janela > 0:
            self.janela -= dt
            if self.janela <= 0:
                self.proximo_golpe = 1
                self.atq_cd = 0.12

    # ---------- desenho ----------
    def desenhar(self, tela, cx):
        for g in self.rastros:
            self._silhueta(tela, g, cx)
        if self.invul > 0 and self.esq_t <= 0 and int(self.invul * 18) % 2 == 0:
            return
        r = self.rect.move(-cx, 0)
        if self.sprite:
            img = self.sprite if self.facing > 0 else pygame.transform.flip(self.sprite, True, False)
            tela.blit(img, img.get_rect(midbottom=r.midbottom))
        else:
            pygame.draw.rect(tela, (60, 80, 130), r, border_radius=8)
            pygame.draw.rect(tela, AZUL_LUZ, (r.x, r.y + 30, r.w, 6))
            pygame.draw.circle(tela, (235, 215, 190), (r.centerx, r.y + 12), 11)
            pygame.draw.circle(tela, PRETO, (r.centerx + self.facing * 5, r.y + 11), 2)
        self._desenhar_katana(tela, r)

    def _silhueta(self, tela, g, cx):
        """Um frame fantasma azul do dash (some aos poucos)."""
        alpha = int(170 * g["vida"] / 0.32)
        w, h = self.rect.w, self.rect.h
        s = pygame.Surface((w + 8, h + 8), pygame.SRCALPHA)
        pygame.draw.rect(s, (70, 150, 255, alpha), (4, 4, w, h), border_radius=8)
        pygame.draw.rect(s, (190, 230, 255, min(255, alpha + 40)), (4, 4, w, h), 2, border_radius=8)
        pygame.draw.circle(s, (160, 215, 255, alpha), (4 + w // 2, 16), 11)
        pygame.draw.circle(s, (10, 20, 60, alpha), (4 + w // 2 + g["f"] * 5, 15), 2)
        tela.blit(s, (g["x"] - cx - 4, g["y"] - 4))

    def _desenhar_katana(self, tela, r):
        f = self.facing
        mao = pygame.Vector2(r.centerx + f * 8, r.y + 28)
        if not self.atq_step:
            costas = (r.centerx - f * 10, r.y + 22)
            ponta = (r.centerx - f * 22, r.y - 2)
            pygame.draw.line(tela, (40, 28, 30), costas, ponta, 4)
            pygame.draw.line(tela, DOURADO, costas, (costas[0] - f * 3, costas[1] - 4), 4)
            return
        g = GOLPES[self.atq_step]
        p = self.atq_t / g["dur"]
        comp = 46 + self.bonus_alcance * 0.5 + (16 if self.atq_step == 3 else 0)
        inicio = KATANA_QUADROS[self.atq_step][1][0]
        if p > inicio:
            self._rastro_katana(tela, mao, f, comp, p, inicio)
        self._lamina(tela, mao, f, angulo_katana(self.atq_step, p), comp)

    def _rastro_katana(self, tela, mao, f, comp, p, p0):
        """Meia-lua de corte que vai sumindo atrás da lâmina."""
        lado = int(comp * 2 + 40)
        area = pygame.Rect(0, 0, lado, lado)
        area.center = (int(mao.x), int(mao.y))
        s = pygame.Surface(area.size, pygame.SRCALPHA)
        centro = pygame.Vector2(lado / 2, lado / 2)
        p_ini = max(p0, p - 0.30)
        n = 7
        for i in range(n):
            pa = p_ini + (p - p_ini) * i / n
            pb = p_ini + (p - p_ini) * (i + 1) / n
            a0 = angulo_katana(self.atq_step, pa)
            a1 = angulo_katana(self.atq_step, pb)
            pts = []
            for ang, rad in ((a0, comp), (a1, comp), (a1, comp * 0.45), (a0, comp * 0.45)):
                d = pygame.Vector2(1, 0).rotate(ang)
                d.x *= f
                pts.append(centro + d * rad)
            pygame.draw.polygon(s, (210, 230, 255, int(30 + 150 * (i + 1) / n)), pts)
        tela.blit(s, area.topleft)

    def _lamina(self, tela, mao, f, ang, comp):
        d = pygame.Vector2(1, 0).rotate(ang)
        d.x *= f
        n = pygame.Vector2(-d.y, d.x)
        base = mao + d * 6
        ponta = mao + d * comp
        pygame.draw.line(tela, (40, 28, 30), mao - d * 10, mao + d * 4, 5)          # cabo
        pygame.draw.polygon(tela, (225, 235, 255), [base + n * 2.5, ponta, base - n * 2.5])  # lâmina
        pygame.draw.line(tela, (255, 255, 255), base, ponta, 1)                      # fio
        g = mao + d * 4
        pygame.draw.line(tela, DOURADO, g + n * 5, g - n * 5, 3)                     # tsuba


# Animação da katana: (progresso, ângulo, suavização). 0° = para frente, -90° = para cima.
# Cada golpe tem preparação (puxa para trás), corte rápido e acompanhamento.
KATANA_QUADROS = {
    1: [(0.00, -50, None), (0.22, -115, "io"), (0.62, 65, "out"), (1.00, 85, "io")],
    2: [(0.00, 90, None), (0.22, 128, "io"), (0.62, -70, "out"), (1.00, -88, "io")],
    3: [(0.00, -70, None), (0.38, -145, "io"), (0.66, 82, "out"), (1.00, 98, "io")],
}


def _suavizar(nome, u):
    if nome == "out":
        return 1 - (1 - u) ** 3
    return u * u * (3 - 2 * u)


def angulo_katana(step, p):
    quadros = KATANA_QUADROS[step]
    p = max(0.0, min(1.0, p))
    for (p0, a0, _), (p1, a1, ease) in zip(quadros, quadros[1:]):
        if p <= p1:
            u = (p - p0) / (p1 - p0)
            return a0 + (a1 - a0) * _suavizar(ease, u)
    return quadros[-1][1]
