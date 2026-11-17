"""Pontos, árvore de habilidades e poderes."""
import pygame
from settings import LARGURA, ALTURA, BRANCO, DOURADO, CINZA, AZUL_LUZ, retangulo_alpha

HABILIDADES = [
    dict(chave="lamina", nome="Lâmina Afiada", desc="+1 de dano em todos os golpes", custo=1, max=3),
    dict(chave="alcance", nome="Alcance da Katana", desc="+14 px de alcance por nível", custo=1, max=3),
    dict(chave="passo", nome="Passo de Luz", desc="A esquiva recarrega mais rápido", custo=1, max=3),
    dict(chave="coracao", nome="Coração de Luz", desc="+1 coração máximo", custo=2, max=2),
    dict(chave="salto", nome="Salto Duplo", desc="Pule mais uma vez no ar", custo=3, max=1),
]

CENTELHAS_POR_PONTO = 5


class ArvoreHabilidades:
    def __init__(self):
        self.niveis = {h["chave"]: 0 for h in HABILIDADES}
        self.pontos = 0
        self.progresso = 0
        self.sel = 0
        self.msg = ""

    def registrar_centelhas(self, n):
        """Cada 5 centelhas coletadas rendem 1 ponto. Retorna pontos ganhos."""
        self.progresso += n
        ganhos = 0
        while self.progresso >= CENTELHAS_POR_PONTO:
            self.progresso -= CENTELHAS_POR_PONTO
            self.pontos += 1
            ganhos += 1
        return ganhos

    def aplicar(self, jogador):
        n = self.niveis
        jogador.bonus_dano = n["lamina"]
        jogador.bonus_alcance = 14 * n["alcance"]
        jogador.cd_esquiva = 0.75 - 0.12 * n["passo"]
        jogador.hp_max = 5 + n["coracao"] + jogador.extra_vida_loja
        jogador.pulos_max = 1 + n["salto"]

    def comprar(self, jogador):
        h = HABILIDADES[self.sel]
        nivel = self.niveis[h["chave"]]
        if nivel >= h["max"]:
            self.msg = "Nível máximo."
        elif self.pontos < h["custo"]:
            self.msg = "Pontos insuficientes."
        else:
            self.pontos -= h["custo"]
            self.niveis[h["chave"]] += 1
            self.aplicar(jogador)
            if h["chave"] == "coracao":
                jogador.hp += 1
            self.msg = f"{h['nome']} evoluiu!"

    def tecla(self, key, jogador):
        if key in (pygame.K_UP, pygame.K_w):
            self.sel = (self.sel - 1) % len(HABILIDADES)
        elif key in (pygame.K_DOWN, pygame.K_s):
            self.sel = (self.sel + 1) % len(HABILIDADES)
        elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_e):
            self.comprar(jogador)

    def desenhar(self, tela, fonte, fonte_p):
        retangulo_alpha(tela, (5, 5, 15, 215), pygame.Rect(0, 0, LARGURA, ALTURA))
        t = fonte.render("Árvore de Habilidades", True, DOURADO)
        tela.blit(t, (LARGURA // 2 - t.get_width() // 2, 40))
        info = fonte_p.render(
            f"Pontos: {self.pontos}   |   próximo ponto: {self.progresso}/{CENTELHAS_POR_PONTO} centelhas",
            True, BRANCO)
        tela.blit(info, (LARGURA // 2 - info.get_width() // 2, 80))
        y = 130
        for i, h in enumerate(HABILIDADES):
            nivel = self.niveis[h["chave"]]
            ativo = i == self.sel
            caixa = pygame.Rect(140, y, LARGURA - 280, 56)
            retangulo_alpha(tela, (60, 70, 120, 200) if ativo else (30, 30, 50, 160), caixa)
            if ativo:
                pygame.draw.rect(tela, DOURADO, caixa, 2)
            tela.blit(fonte_p.render(h["nome"], True, BRANCO), (caixa.x + 14, caixa.y + 6))
            tela.blit(fonte_p.render(h["desc"], True, CINZA if not ativo else AZUL_LUZ),
                      (caixa.x + 14, caixa.y + 30))
            for k in range(h["max"]):
                cor = DOURADO if k < nivel else (70, 70, 90)
                pygame.draw.circle(tela, cor, (caixa.right - 120 + k * 22, caixa.y + 18), 7)
            custo = fonte_p.render(f"custo {h['custo']}", True, BRANCO)
            tela.blit(custo, (caixa.right - custo.get_width() - 14, caixa.y + 30))
            y += 66
        rodape = fonte_p.render("Setas ou W/S: escolher   Enter: comprar   Tab ou Esc: fechar", True, CINZA)
        tela.blit(rodape, (LARGURA // 2 - rodape.get_width() // 2, ALTURA - 50))
        if self.msg:
            m = fonte_p.render(self.msg, True, DOURADO)
            tela.blit(m, (LARGURA // 2 - m.get_width() // 2, ALTURA - 80))
