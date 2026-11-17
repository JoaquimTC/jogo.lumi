"""Configurações globais e utilitários de assets do LUMI."""
import math
import os
import pygame

LARGURA, ALTURA = 960, 540
FPS = 60

GRAVIDADE = 2200.0      # px/s²
VEL_QUEDA_MAX = 1100.0  # px/s
CHAO_Y = 460            # altura do chão nas fases

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PASTA_ASSETS = os.path.join(BASE_DIR, "assets")

BRANCO = (240, 240, 235)
PRETO = (10, 10, 16)
CINZA = (90, 90, 105)
DOURADO = (255, 214, 90)
VERMELHO = (220, 60, 70)
VERDE = (90, 200, 120)
AZUL_LUZ = (140, 220, 255)
ROXO = (120, 80, 170)

_cache_img = {}
_cache_som = {}


def carregar_imagem(nome, tamanho=None):
    """Procura em assets/sprites e assets/imagens.
    Se o arquivo não existir devolve None e a entidade desenha uma forma simples."""
    chave = (nome, tamanho)
    if chave in _cache_img:
        return _cache_img[chave]
    img = None
    for sub in ("sprites", "imagens"):
        caminho = os.path.join(PASTA_ASSETS, sub, nome)
        if os.path.exists(caminho):
            img = pygame.image.load(caminho).convert_alpha()
            if tamanho:
                img = pygame.transform.smoothscale(img, tamanho)
            break
    _cache_img[chave] = img
    return img


class _SomMudo:
    def play(self):
        pass


def carregar_som(nome):
    """Carrega assets/sons/<nome>. Sem o arquivo, devolve um som mudo."""
    if nome in _cache_som:
        return _cache_som[nome]
    som = _SomMudo()
    caminho = os.path.join(PASTA_ASSETS, "sons", nome)
    if pygame.mixer.get_init() and os.path.exists(caminho):
        som = pygame.mixer.Sound(caminho)
        som.set_volume(0.6)
    _cache_som[nome] = som
    return som


def tocar_musica(nome):
    caminho = os.path.join(PASTA_ASSETS, "musicas", nome)
    if nome and pygame.mixer.get_init() and os.path.exists(caminho):
        pygame.mixer.music.load(caminho)
        pygame.mixer.music.set_volume(0.4)
        pygame.mixer.music.play(-1)


def aproximar(valor, alvo, passo):
    """Move 'valor' em direção a 'alvo' no máximo 'passo'."""
    if valor < alvo:
        return min(valor + passo, alvo)
    return max(valor - passo, alvo)


def retangulo_alpha(tela, cor_rgba, rect):
    s = pygame.Surface(rect.size, pygame.SRCALPHA)
    s.fill(cor_rgba)
    tela.blit(s, rect.topleft)


def quebrar_texto(texto, fonte, largura):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = (atual + " " + palavra).strip()
        if fonte.size(teste)[0] <= largura:
            atual = teste
        else:
            linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


ESCALA_PIXEL = 2   # 2 = 480x270 | 3 = 320x180 (mais granulado)


def carregar_fonte(tamanho, negrito=False):
    """Usa assets/fontes/pixel.ttf se existir; senão uma fonte do sistema."""
    caminho = os.path.join(PASTA_ASSETS, "fontes", "pixel.ttf")
    if os.path.exists(caminho):
        return pygame.font.Font(caminho, tamanho)
    return pygame.font.SysFont("dejavusans,arial", tamanho, bold=negrito)


def criar_vinheta():
    """Cantos escuros da tela."""
    w, h = 96, 54
    peq = pygame.Surface((w, h), pygame.SRCALPHA)
    for y in range(h):
        for x in range(w):
            dx = (x + 0.5 - w / 2) / (w / 2)
            dy = (y + 0.5 - h / 2) / (h / 2)
            d = math.sqrt(dx * dx * 0.9 + dy * dy * 1.1) / 1.25
            a = int(max(0.0, (d - 0.45) / 0.55) ** 1.6 * 200)
            peq.set_at((x, y), (0, 0, 0, min(a, 210)))
    return pygame.transform.smoothscale(peq, (LARGURA, ALTURA))


def criar_brilho(raio=190, cor=(70, 105, 165)):
    """Luz suave que acompanha o Lumi (usada com BLEND_RGB_ADD)."""
    n = 48
    peq = pygame.Surface((n, n))
    for y in range(n):
        for x in range(n):
            d = min(1.0, math.hypot(x + 0.5 - n / 2, y + 0.5 - n / 2) / (n / 2))
            k = (1 - d) ** 2
            peq.set_at((x, y), tuple(int(c * k) for c in cor))
    return pygame.transform.smoothscale(peq, (raio * 2, raio * 2))


def criar_escuridao(alpha=95, cor=(4, 2, 14)):
    s = pygame.Surface((LARGURA, ALTURA), pygame.SRCALPHA)
    s.fill((*cor, alpha))
    return s
