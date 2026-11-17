"""LUMI - A Última Luz (pygame). Inicia o jogo e conecta todos os sistemas.

Rode com:  python3 main.py
Controles: A/D ou setas mover | W/Espaço/↑ pular | J katana (combo x3) | K esquiva
           E interagir | Tab habilidades | P/Esc pausa | F1 mostra hitboxes
"""
import sys
import pygame
from settings import (LARGURA, ALTURA, FPS, CHAO_Y, BRANCO, DOURADO, VERMELHO,
                      CINZA, AZUL_LUZ, ESCALA_PIXEL, tocar_musica, carregar_som,
                      retangulo_alpha, carregar_fonte, criar_vinheta, criar_brilho,
                      criar_escuridao)
from player import Jogador
from combat import Efeitos, golpe_do_jogador, perigos_no_jogador
from world import criar_fase, NUM_FASES
from npcs import Dialogo, Loja
from skills import ArvoreHabilidades
from bosses import Ogro

TECLAS_PULO = (pygame.K_w, pygame.K_UP, pygame.K_SPACE)


class Jogo:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("LUMI - A Última Luz")
        self.tela = pygame.display.set_mode((LARGURA, ALTURA))
        self.relogio = pygame.time.Clock()
        self.fonte_g = carregar_fonte(44, True)
        self.fonte = carregar_fonte(24, True)
        self.fonte_p = carregar_fonte(18)
        # visual: o mundo é desenhado numa superfície e depois pixelado
        self.mundo = pygame.Surface((LARGURA, ALTURA))
        self.vinheta = criar_vinheta()
        self.brilho = criar_brilho()
        self.escuridao = criar_escuridao()
        self.cx_atual = 0
        self.som_centelha = carregar_som("centelha.wav")
        self.estado = "menu"
        self.debug = False
        self.rodando = True
        self.novo_jogo()

    # ---------- setup ----------
    def novo_jogo(self):
        self.efeitos = Efeitos()
        self.skills = ArvoreHabilidades()
        self.jogador = Jogador(0, 0)
        self.centelhas = 0
        self.dialogo = None
        self.loja = Loja()
        self.banner = ""
        self.banner_t = 0.0
        self.carregar_fase(0)

    def carregar_fase(self, i):
        self.indice_fase = i
        self.fase = criar_fase(i)
        self.checkpoint = self.fase.spawn
        self.jogador.reaparecer(*self.fase.spawn, vida_cheia=False)
        self.ogro = Ogro(1000, (0, self.fase.largura)) if self.fase.boss else None
        self.boss_recompensado = False
        self.cx = 0.0
        self.mostrar_banner(self.fase.nome)
        tocar_musica(self.fase.musica)

    def mostrar_banner(self, txt, dur=2.5):
        self.banner, self.banner_t = txt, dur

    def ganhar_centelhas(self, n, x, y):
        self.centelhas += n
        self.som_centelha.play()
        pts = self.skills.registrar_centelhas(n)
        if pts:
            self.efeitos.texto(x, y - 20, "+1 ponto de habilidade! (Tab)", DOURADO)

    # ---------- eventos ----------
    def tratar_evento(self, e):
        if e.type == pygame.QUIT:
            self.rodando = False
            return
        if e.type == pygame.KEYUP:
            if self.estado == "jogando" and e.key in TECLAS_PULO:
                self.jogador.soltar_pulo()
            return
        if e.type != pygame.KEYDOWN:
            return
        k = e.key
        if k == pygame.K_F1:
            self.debug = not self.debug
            return
        if self.estado == "menu":
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self.novo_jogo()
                self.estado = "jogando"
            elif k == pygame.K_ESCAPE:
                self.rodando = False
        elif self.estado == "jogando":
            self.evento_jogando(k)
        elif self.estado == "pausa":
            if k in (pygame.K_p, pygame.K_ESCAPE):
                self.estado = "jogando"
            elif k == pygame.K_q:
                self.estado = "menu"
        elif self.estado == "habilidades":
            if k in (pygame.K_TAB, pygame.K_ESCAPE):
                self.estado = "jogando"
            else:
                self.skills.tecla(k, self.jogador)
        elif self.estado == "dialogo":
            if k in (pygame.K_e, pygame.K_RETURN, pygame.K_SPACE):
                if self.dialogo.avancar():
                    if self.dialogo.mercador:
                        self.loja = Loja()
                        self.estado = "loja"
                    else:
                        self.estado = "jogando"
        elif self.estado == "loja":
            self.centelhas, fechar = self.loja.tecla(k, self.jogador, self.centelhas)
            if fechar:
                self.estado = "jogando"
        elif self.estado == "morte":
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self.renascer()
        elif self.estado == "vitoria":
            if k in (pygame.K_RETURN, pygame.K_SPACE):
                self.estado = "menu"

    def evento_jogando(self, k):
        j = self.jogador
        if k in TECLAS_PULO:
            j.pular()
        elif k == pygame.K_j:
            j.atacar()
        elif k == pygame.K_k:
            j.esquivar()
        elif k == pygame.K_e:
            for npc in self.fase.npcs:
                if npc.perto(j):
                    self.dialogo = Dialogo(npc.nome, npc.falas, npc.mercador)
                    self.estado = "dialogo"
                    break
        elif k == pygame.K_TAB:
            self.skills.msg = ""
            self.estado = "habilidades"
        elif k in (pygame.K_p, pygame.K_ESCAPE):
            self.estado = "pausa"

    # ---------- lógica ----------
    def renascer(self):
        self.jogador.reaparecer(*self.checkpoint, vida_cheia=True)
        if self.ogro and not self.ogro.derrotado:
            self.ogro = Ogro(1000, (0, self.fase.largura))
        self.estado = "jogando"

    def update_jogando(self, dt_real):
        dt = self.efeitos.ajustar_dt(dt_real)
        j, fase = self.jogador, self.fase
        keys = pygame.key.get_pressed()

        j.update(dt, keys, fase.plataformas)
        fase.update(dt)
        for s in fase.sombras:
            s.update(dt, fase.plataformas)

        # boss
        og = self.ogro
        if og:
            if og.estado == "dormindo" and j.rect.centerx > 420:
                og.acordar()
            og.update(dt, j, fase.solidos_grandes, self.efeitos)
            while og.eventos:
                ev = og.eventos.pop()
                if ev == "acordou":
                    self.mostrar_banner("OGRO GUARDIÃO")
                elif ev == "fase2":
                    self.mostrar_banner("ELE SE LEVANTOU!", 2.5)
                    self.efeitos.tremor = 0.4
            if og.derrotado and not self.boss_recompensado:
                self.boss_recompensado = True
                self.skills.pontos += 3
                fase.portal_ativo = True
                self.mostrar_banner("OGRO DERROTADO!  +3 pontos de habilidade")

        # combate
        alvos = list(fase.sombras) + ([og] if og else [])
        golpe_do_jogador(j, alvos, self.efeitos)
        for s in fase.sombras:
            if s.morreu_agora:
                s.morreu_agora = False
                self.ganhar_centelhas(2, s.rect.centerx, s.rect.top)
        fase.sombras = [s for s in fase.sombras if s.vivo]
        perigos = list(fase.espinhos) + list(fase.sombras) + (og.perigos() if og else [])
        perigos_no_jogador(j, perigos, self.efeitos)

        # coleta e checkpoints
        n = fase.coletar(j)
        if n:
            self.ganhar_centelhas(n, j.rect.centerx, j.rect.top)
        novo_cp = fase.checar_checkpoints(j)
        if novo_cp:
            self.checkpoint = novo_cp
            self.efeitos.texto(j.rect.centerx, j.rect.top - 20, "Checkpoint!", DOURADO)

        # queda no abismo
        if j.rect.top > ALTURA + 120:
            j.hp -= 1
            if j.hp > 0:
                j.reaparecer(*self.checkpoint, vida_cheia=False)

        if j.hp <= 0:
            self.estado = "morte"
            return
        if fase.no_portal(j):
            if self.indice_fase + 1 >= NUM_FASES:
                self.estado = "vitoria"
            else:
                self.carregar_fase(self.indice_fase + 1)
            return

        alvo = j.rect.centerx - LARGURA // 2
        alvo = max(0, min(fase.largura - LARGURA, alvo))
        self.cx += (alvo - self.cx) * min(1.0, 8 * dt_real)

    def update(self, dt_real):
        if self.estado == "jogando":
            self.update_jogando(dt_real)
        elif self.estado == "dialogo":
            self.dialogo.update(dt_real)
        self.efeitos.update(dt_real)
        self.banner_t = max(0.0, self.banner_t - dt_real)

    # ---------- desenho ----------
    CORACAO = [" XX XX ",
               "XXXXXXX",
               "XXXXXXX",
               " XXXXX ",
               "  XXX  ",
               "   X   "]

    def desenhar_coracao(self, x, y, cheio):
        """Coração em pixel art (cada pixel = 3x3)."""
        cor = (200, 40, 60) if cheio else (50, 30, 40)
        brilho = (255, 130, 140) if cheio else cor
        for j, linha in enumerate(self.CORACAO):
            for i, c in enumerate(linha):
                if c == "X":
                    pygame.draw.rect(self.tela, (10, 5, 10), (x + i * 3 + 1, y + j * 3 + 1, 3, 3))
        for j, linha in enumerate(self.CORACAO):
            for i, c in enumerate(linha):
                if c == "X":
                    pygame.draw.rect(self.tela, brilho if (i, j) == (1, 1) else cor,
                                     (x + i * 3, y + j * 3, 3, 3))

    def texto_centro(self, txt, fonte, cor, y):
        img = fonte.render(txt, True, cor)
        self.tela.blit(img, (LARGURA // 2 - img.get_width() // 2, y))

    def desenhar_mundo(self):
        cx = int(self.cx) + self.efeitos.deslocamento_tremor()
        self.cx_atual = cx
        self.fase.desenhar(self.tela, cx)
        for npc in self.fase.npcs:
            npc.desenhar(self.tela, cx, False, self.fonte_p)
        for s in self.fase.sombras:
            s.desenhar(self.tela, cx)
        # clima sombrio: escuridão + vinheta, com a luz do Lumi por cima
        self.tela.blit(self.escuridao, (0, 0))
        self.tela.blit(self.vinheta, (0, 0))
        c = self.jogador.rect.center
        self.tela.blit(self.brilho, self.brilho.get_rect(center=(c[0] - cx, c[1])),
                       special_flags=pygame.BLEND_RGB_ADD)
        if self.ogro:
            self.ogro.desenhar(self.tela, cx)
            for o in self.ogro.ondas:
                o.desenhar(self.tela, cx)
            for p in self.ogro.pedras:
                p.desenhar(self.tela, cx)
        self.jogador.desenhar(self.tela, cx)
        self.efeitos.desenhar_particulas(self.tela, cx)

    def pixelar(self):
        """Reduz o mundo e amplia sem suavizar: efeito pixel art."""
        e = ESCALA_PIXEL
        pequeno = pygame.transform.smoothscale(self.mundo, (LARGURA // e, ALTURA // e))
        pygame.transform.scale(pequeno, (LARGURA, ALTURA), self.tela)

    def desenhar_textos_mundo(self):
        """Textos ficam nítidos: são desenhados depois da pixelação."""
        cx = self.cx_atual
        if self.estado == "jogando":
            for npc in self.fase.npcs:
                if npc.perto(self.jogador):
                    img = self.fonte_p.render("[E] falar", True, DOURADO)
                    self.tela.blit(img, (npc.rect.centerx - cx - img.get_width() // 2, npc.rect.top - 28))
        if self.ogro:
            self.ogro.desenhar_aviso(self.tela, cx, self.fonte_p)
        self.efeitos.desenhar_textos(self.tela, cx, self.fonte_p)

    def desenhar_debug(self, cx):
        def caixa(r, cor):
            pygame.draw.rect(self.tela, cor, r.move(-cx, 0), 1)
        caixa(self.jogador.rect, (0, 255, 0))
        hb = self.jogador.hitbox_ataque()
        if hb:
            caixa(hb, (255, 255, 0))
        for s in self.fase.sombras:
            caixa(s.rect, (0, 255, 0))
        for p in list(self.fase.espinhos) + (self.ogro.perigos() if self.ogro else []):
            for r in p.caixas_dano():
                caixa(r, (255, 0, 0))
        if self.ogro:
            caixa(self.ogro.rect, (0, 255, 0))

    def desenhar_hud(self):
        j = self.jogador
        for i in range(j.hp_max):
            self.desenhar_coracao(16 + i * 28, 14, i < j.hp)
        self.tela.blit(self.fonte_p.render(f"Centelhas: {self.centelhas}", True, DOURADO), (16, 44))
        if self.skills.pontos:
            self.tela.blit(self.fonte_p.render(f"Pontos de habilidade: {self.skills.pontos}  [Tab]",
                                               True, AZUL_LUZ), (16, 68))
        og = self.ogro
        if og and og.estado != "dormindo":
            barra = pygame.Rect(LARGURA // 2 - 250, ALTURA - 40, 500, 16)
            pygame.draw.rect(self.tela, (40, 20, 25), barra)
            frac = og.hp / og.hp_max
            pygame.draw.rect(self.tela, VERMELHO, (barra.x, barra.y, int(barra.w * frac), barra.h))
            pygame.draw.rect(self.tela, BRANCO, barra, 2)
            self.texto_centro(og.nome, self.fonte_p, BRANCO, barra.y - 24)
            dica = og.dica()
            if dica:
                self.texto_centro(dica, self.fonte, DOURADO, ALTURA - 110)
        if self.banner_t > 0:
            self.texto_centro(self.banner, self.fonte_g, BRANCO, 90)

    def desenhar(self):
        self.tela.fill((0, 0, 0))
        if self.estado == "menu":
            self.tela.fill((10, 10, 25))
            self.texto_centro("LUMI", self.fonte_g, DOURADO, 110)
            self.texto_centro("A Última Luz", self.fonte, BRANCO, 170)
            linhas = ["A/D ou setas: mover     W/Espaço: pular", "J: katana (combo de 3 golpes)     K: esquiva",
                      "E: falar     Tab: habilidades     P: pausa     F1: hitboxes"]
            for k, l in enumerate(linhas):
                self.texto_centro(l, self.fonte_p, CINZA, 270 + k * 28)
            self.texto_centro("Pressione ENTER para começar", self.fonte, AZUL_LUZ, 410)
            return
        tela_real = self.tela
        self.tela = self.mundo
        self.desenhar_mundo()
        self.tela = tela_real
        self.pixelar()
        self.desenhar_textos_mundo()
        if self.debug:
            self.desenhar_debug(self.cx_atual)
        self.desenhar_hud()
        if self.estado == "pausa":
            retangulo_alpha(self.tela, (0, 0, 0, 170), pygame.Rect(0, 0, LARGURA, ALTURA))
            self.texto_centro("PAUSADO", self.fonte_g, BRANCO, 200)
            self.texto_centro("P/Esc: continuar     Q: menu", self.fonte_p, CINZA, 270)
        elif self.estado == "habilidades":
            self.skills.desenhar(self.tela, self.fonte, self.fonte_p)
        elif self.estado == "dialogo":
            self.dialogo.desenhar(self.tela, self.fonte, self.fonte_p)
        elif self.estado == "loja":
            self.loja.desenhar(self.tela, self.fonte, self.fonte_p, self.centelhas)
        elif self.estado == "morte":
            retangulo_alpha(self.tela, (40, 0, 0, 190), pygame.Rect(0, 0, LARGURA, ALTURA))
            self.texto_centro("A luz se apagou...", self.fonte_g, VERMELHO, 190)
            self.texto_centro("ENTER para voltar ao último checkpoint", self.fonte_p, BRANCO, 270)
        elif self.estado == "vitoria":
            retangulo_alpha(self.tela, (0, 0, 20, 220), pygame.Rect(0, 0, LARGURA, ALTURA))
            self.texto_centro("A LUZ VOLTOU!", self.fonte_g, DOURADO, 180)
            self.texto_centro("Obrigado por jogar. ENTER para voltar ao menu.", self.fonte_p, BRANCO, 260)

    # ---------- loop ----------
    def rodar(self):
        while self.rodando:
            dt = min(self.relogio.tick(FPS) / 1000.0, 1 / 30)
            for e in pygame.event.get():
                self.tratar_evento(e)
            self.update(dt)
            self.desenhar()
            pygame.display.flip()
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    Jogo().rodar()
