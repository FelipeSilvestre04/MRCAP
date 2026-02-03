import sys
import os
import ast
from collections import Counter
import time
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import math
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
_UTILS_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, '..', '..', 'utils'))
_INSTANCES_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, '..', 'instances'))
_OUTPUT_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, '..', 'output'))
_NFP_DIR = os.path.abspath(os.path.join(_SCRIPT_DIR, 'NFPs'))
sys.path.insert(0, _UTILS_DIR)
from botao import Botao
from nfp_teste import combinar_poligonos, triangulate_shapely, NoFitPolygon, interpolar_pontos_poligono
from RKO_v3 import RKO
from shapely import intersection_all
import shapely
from shapely import Polygon, MultiPolygon, unary_union, LineString, MultiLineString, MultiPoint, LinearRing, GeometryCollection, Point
from shapely.prepared import prep
import itertools
from scipy.spatial import ConvexHull
import copy
from matplotlib.patches import Polygon as MPolygon, Rectangle
import random
from typing import List, Tuple, Union
from shapely import affinity
from shapely.geometry import Polygon, MultiPolygon, Point, LineString
from shapely.ops import unary_union
from shapely.affinity import translate
import pstats


def tratar_lista(lista_poligonos, Escala):


    def remove_vertices_repetidos(polygon):
        seen = set()
        unique_polygon = []
        for vertex in polygon:

            if vertex not in seen:
                unique_polygon.append(vertex)
                seen.add(vertex)
        return unique_polygon
    nova_lista = []
    nova_lista_completa = []
    for pol in lista_poligonos:
        novo_pol = []
        for cor in pol:
            novo_pol.append((int(cor[0] * Escala), int(cor[1] * Escala)))
        novo_pol = remove_vertices_repetidos(novo_pol)
        nova_lista.append(novo_pol)
    return nova_lista


def draw_cutting_area(pieces, area_width, area_height, legenda=None, filename=None):
    fig, ax = plt.subplots()
    ax.add_patch(Rectangle((0, 0), area_width, area_height,
                           edgecolor='black', facecolor='none', linewidth=1.5))
    for verts in pieces:
        poly = MPolygon(verts, closed=True,
                        facecolor=(173/255, 216/255, 230/255), edgecolor='black')
        ax.add_patch(poly)
    ax.set_xlim(0, area_width)
    ax.set_ylim(0, area_height)
    ax.set_aspect('equal')

    if legenda:

        if isinstance(legenda, (list, tuple)):
            ax.legend(legenda)
        else:
            ax.set_title(legenda)
    plt.tight_layout()
    directory = os.path.dirname(filename)

    if legenda == '[]':
        plt.show()
    else:

        if directory:
            os.makedirs(directory, exist_ok=True)

        if filename:
            print(f"DEBUG: Saving image to {filename}")
            plt.savefig(filename, dpi=150)
            plt.close(fig)


def offset_polygon(vertices, offset):

    if offset > 0:
        poly = Polygon(vertices)

        if not poly.is_valid:
            return vertices
        buffered = poly.buffer(offset, join_style=1, mitre_limit=2.0)

        if buffered.is_empty or not buffered.is_valid:
            return vertices

        if buffered.geom_type == 'Polygon':
            new_vertices = list(buffered.exterior.coords)[:-1]
        else:
            largest = max(buffered.geoms, key=lambda x: x.area)
            new_vertices = list(largest.exterior.coords)[:-1]
        return new_vertices
    else:
        return vertices


def multiplicar_tudo(d, multiplicador):
    novo_dicionario = {}
    for chave, valor in d.items():
        nova_chave = tuple(
            multiplicar_elemento(e, multiplicador) for e in chave
        )
        novo_valor = [
            tuple(x * multiplicador for x in ponto) for ponto in valor
        ]
        novo_dicionario[nova_chave] = novo_valor
    return novo_dicionario


def ler_poligonos(arquivo, escala=1):
    instance_path = os.path.join(_INSTANCES_DIR, arquivo + '.dat')
    with open(instance_path, 'r') as f:
        conteudo = f.read().strip()
    linhas = conteudo.split('\n')
    num_poligonos = int(linhas[0].strip())
    poligonos = []
    i = 1
    while i < len(linhas):

        if linhas[i].strip():
            try:
                num_vertices = int(linhas[i].strip())
                i += 1
                vertices = []
                for _ in range(num_vertices):
                    while i < len(linhas) and not linhas[i].strip():
                        i += 1

                    if i < len(linhas):
                        coords = linhas[i].strip().split()

                        if len(coords) != 2:
                            raise ValueError(f"Esperado 2 valores por linha, mas obteve {len(coords)}: '{linhas[i].strip()}'")
                        x, y = map(float, coords)
                        vertices.append((x * escala, y * escala))
                        i += 1
                    else:
                        raise ValueError(f"Esperado {num_vertices} vértices, mas o arquivo terminou prematuramente.")
                poligonos.append(vertices)
            except ValueError as ve:
                print(f"Erro ao processar a linha {i}: {linhas[i].strip()} - {ve}")
                i += 1
        else:
            i += 1

    if num_poligonos == len(poligonos):
        pass
        print(f'Todos os {num_poligonos} poligonos foram lidos com sucesso!')
    return poligonos


def multiplicar_elemento(e, multiplicador):

    if isinstance(e, (int, float)):
        return e * multiplicador
    elif isinstance(e, tuple):
        return tuple(multiplicar_elemento(x, multiplicador) for x in e)
    else:
        return e


def projetar_vertices_em_poligono(poligono_principal, lista_poligonos):
    import math
    from functools import cmp_to_key

    if not poligono_principal or len(poligono_principal) < 3:
        return poligono_principal.copy() if poligono_principal else []
    poligono_resultado = poligono_principal.copy()
    todos_vertices = []
    for poligono in lista_poligonos:

        if poligono:
            todos_vertices.extend(poligono)
    for vertice in todos_vertices:
        x_vertice, y_vertice = vertice
        for i in range(len(poligono_principal)):
            p1 = poligono_principal[i]
            p2 = poligono_principal[(i + 1) % len(poligono_principal)]

            if not ((p1[1] <= y_vertice <= p2[1]) or (p2[1] <= y_vertice <= p1[1])):
                continue

            if abs(p1[1] - p2[1]) < 1e-10:

                if abs(p1[1] - y_vertice) < 1e-10:
                    x_min = min(p1[0], p2[0])
                    x_max = max(p1[0], p2[0])

                    if x_min <= x_vertice <= x_max:
                        ponto_intersecao = (x_vertice, y_vertice)

                        if ponto_intersecao not in poligono_resultado:
                            poligono_resultado.append(ponto_intersecao)
            else:
                t = (y_vertice - p1[1]) / (p2[1] - p1[1])

                if 0 <= t <= 1:
                    x_intersecao = p1[0] + t * (p2[0] - p1[0])
                    ponto_intersecao = (x_intersecao, y_vertice)

                    if ponto_intersecao not in poligono_resultado:
                        poligono_resultado.append(ponto_intersecao)
        for i in range(len(poligono_principal)):
            p1 = poligono_principal[i]
            p2 = poligono_principal[(i + 1) % len(poligono_principal)]

            if not ((p1[0] <= x_vertice <= p2[0]) or (p2[0] <= x_vertice <= p1[0])):
                continue

            if abs(p1[0] - p2[0]) < 1e-10:

                if abs(p1[0] - x_vertice) < 1e-10:
                    y_min = min(p1[1], p2[1])
                    y_max = max(p1[1], p2[1])

                    if y_min <= y_vertice <= y_max:
                        ponto_intersecao = (x_vertice, y_vertice)

                        if ponto_intersecao not in poligono_resultado:
                            poligono_resultado.append(ponto_intersecao)
            else:
                t = (x_vertice - p1[0]) / (p2[0] - p1[0])

                if 0 <= t <= 1:
                    y_intersecao = p1[1] + t * (p2[1] - p1[1])
                    ponto_intersecao = (x_vertice, y_intersecao)

                    if ponto_intersecao not in poligono_resultado:
                        poligono_resultado.append(ponto_intersecao)

    if len(poligono_resultado) < 3:
        return poligono_resultado
    cx = sum(x for x, _ in poligono_resultado) / len(poligono_resultado)
    cy = sum(y for _, y in poligono_resultado) / len(poligono_resultado)


    def comparar_pontos(p1, p2):
        angulo1 = math.atan2(p1[1] - cy, p1[0] - cx)
        angulo2 = math.atan2(p2[1] - cy, p2[0] - cx)
        return -1 if angulo1 < angulo2 else (1 if angulo1 > angulo2 else 0)
    poligono_resultado.sort(key=cmp_to_key(comparar_pontos))
    i = 0
    while i < len(poligono_resultado):
        j = (i + 1) % len(poligono_resultado)
        p1 = poligono_resultado[i]
        p2 = poligono_resultado[j]
        distancia = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)

        if distancia < 1e-6:
            poligono_resultado.pop(j if j < i else i)
        else:
            i += 1
    return poligono_resultado


def dimensions(dataset: str):
    specs = {
        'fu':          (34.0,     38.0,     1, [0,1,2,3]),
        'jackobs1':    (13.0,     40.0,     1, [0,1,2,3]),
        'jackobs2':    (28.2,     70.0,     1, [0,1,2,3]),
        'shapes0':     (73.0,     40.0,     1, [0]),
        'shapes1':     (75.0,     40.0,     1, [0,2]),
        'shapes2':     (37.3,     15.0,     1, [0,2]),
        'dighe1':      (112.14,   100.0,    1, [0]),
        'dighe2':      (134.05,   100.0,    1, [0]),
        'albano':      (11122.63, 4900.0,   1, [0,2]),
        'dagli':       (80.6,     60.0,     1, [0,2]),
        'mao':         (1958.6,   2550.0,   1, [0,1,2,3]),
        'marques':     (90.6,     104.0,    1, [0,1,2,3]),
        'shirts':      (73.13,    40.0,     1, [0,2]),
        'swim':        (6868.0,   5752.0,   1, [0,2]),
        'trousers':    (295.75,   79.0,     1, [0,2]),
    }
    return specs.get(dataset, (None, None, None, None))


def pre_processar_NFP(rotacoes, lista_pecas, offset, env):
    tabela_nfps = {}
    lista_unica = []
    for peca in lista_pecas:

        if peca not in lista_unica:
            lista_unica.append(peca)
    total = len(lista_unica) * len(rotacoes) * len(lista_unica) * len(rotacoes)
    atual = 0
    for pecaA in lista_unica:
        for grauA in rotacoes:
            for pecaB in lista_unica:
                for grauB in rotacoes:
                    atual += 1
                    porcentagem = (atual / total) * 100
                    print(f"\rPré-processando NFPs: {porcentagem:.1f}% concluído", end="")
                    chave = (tuple(pecaA), grauA, tuple(pecaB), grauB)
                    nfp, intersec = NFP(pecaA, grauA, pecaB, grauB, env)
                    tabela_nfps[chave] = [list(nfp.exterior.coords),intersec]
    return tabela_nfps
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path


def plot_shapely_geometry(ax, geom, facecolor='lightblue', edgecolor='black', alpha=0.5, linewidth=1.0):
    geom = Polygon(geom) if isinstance(geom, list) else geom

    if geom is None or geom.is_empty:
        return
    geoms_to_plot = getattr(geom, 'geoms', [geom])
    for g in geoms_to_plot:

        if not isinstance(g, Polygon):
            continue
        path_verts = list(g.exterior.coords)
        path_codes = [Path.MOVETO] + [Path.LINETO] * (len(path_verts) - 2) + [Path.CLOSEPOLY]
        for interior in g.interiors:
            interior_verts = list(interior.coords)
            path_verts.extend(interior_verts)
            path_codes.extend([Path.MOVETO] + [Path.LINETO] * (len(interior_verts) - 2) + [Path.CLOSEPOLY])
        path = Path(path_verts, path_codes)
        patch = PathPatch(path, facecolor=facecolor, edgecolor=edgecolor, alpha=alpha, linewidth=linewidth)
        ax.add_patch(patch)


def NFP(PecaA, grauA, PecaB, grauB, env):
    pontos_pol_A = env.rot_pol(env.lista.index(PecaA), grauA)
    pontos_pol_B = env.rot_pol(env.lista.index(PecaB), grauB)

    if Polygon(pontos_pol_B).equals(Polygon(pontos_pol_B).convex_hull):
        convex_partsB = [pontos_pol_B]
    else:
        convex_partsB = triangulate_shapely(pontos_pol_B)

    if Polygon(pontos_pol_A).equals(Polygon(pontos_pol_A).convex_hull):
        convex_partsA = [pontos_pol_A]
    else:
        convex_partsA = triangulate_shapely(pontos_pol_A)
    nfps_convx = []
    intersec_parts = []
    for cb_poly in convex_partsB:
        intersec_B = []
        for ca_poly in convex_partsA:
            nfp_part = NoFitPolygon(ca_poly, cb_poly)

            if nfp_part and not nfp_part.is_empty:
                nfps_convx.append(nfp_part)
                intersec_B.append(nfp_part)

        if intersec_B:
            intersec_parts.append(intersec_B)

    if not nfps_convx:
        print("Nenhum NFP parcial foi gerado.")
        while True:
            print("Nenhum NFP parcial foi gerado.")
            print(PecaA)
        return Polygon(), None
    nfp_unido = unary_union(nfps_convx)
    pontos_candidatos = set()
    for subgrupo in intersec_parts:
        for ponto in pontos_pol_A:
            pontos_candidatos.add(Point(ponto))
        for ponto in pontos_pol_B:
            pontos_candidatos.add(Point(ponto))
        for nfp in subgrupo:
            for ponto in nfp.exterior.coords:
                pontos_candidatos.add(ponto)

        if len(subgrupo) > 1:
            for p1, p2 in itertools.combinations(subgrupo, 2):
                intersec = p1.boundary.intersection(p2.boundary)

                if not intersec.is_empty:
                    for ponto in extrair_vertices(intersec):
                        pontos_candidatos.add(ponto)

    if len(nfps_convx) > 1:
        intersec_total = intersection_all([nfp.boundary for nfp in nfps_convx])

        if not intersec_total.is_empty:
            for ponto in extrair_vertices(intersec_total):
                pontos_candidatos.add(ponto)
        for p1, p2 in itertools.combinations(nfps_convx, 2):
                intersec = p1.boundary.intersection(p2.boundary)

                if not intersec.is_empty:
                    for ponto in extrair_vertices(intersec):
                        pontos_candidatos.add(ponto)
    min_x, min_y, max_x, max_y = nfp_unido.bounds
    padding = 100.0
    pontos_pol_nor_A = [(x - pontos_pol_B[0][0], y - pontos_pol_B[0][1]) for x, y in pontos_pol_A]
    pontos_candidatos = set()
    for ponto in pontos_pol_nor_A:
        x_vertice, y_vertice = ponto
        linha_cima = LineString([ponto, (x_vertice, max_y + padding)])
        intersecao_cima = nfp_unido.boundary.intersection(linha_cima)
        pontos_candidatos.update(extrair_vertices(intersecao_cima))
        linha_baixo = LineString([ponto, (x_vertice, min_y - padding)])
        intersecao_baixo = nfp_unido.boundary.intersection(linha_baixo)
        pontos_candidatos.update(extrair_vertices(intersecao_baixo))
        linha_direita = LineString([ponto, (max_x + padding, y_vertice)])
        intersecao_direita = nfp_unido.boundary.intersection(linha_direita)
        pontos_candidatos.update(extrair_vertices(intersecao_direita))
        linha_esquerda = LineString([ponto, (min_x - padding, y_vertice)])
        intersecao_esquerda = nfp_unido.boundary.intersection(linha_esquerda)
        pontos_candidatos.update(extrair_vertices(intersecao_esquerda))
    for ponto in pontos_pol_nor_A:
        pontos_candidatos.add(Point(ponto))
    intersec = MultiPoint(list(pontos_candidatos))
    nfp_f = []
    inter = set()
    for ponto in extrair_vertices(intersec):

        if nfp_unido.touches(Point(ponto)):
            nfp_f.append(ponto)
        else:
            inter.add(ponto)
    intersec = MultiPoint(inter)
    nfp_unido = unary_union([nfp_unido, MultiPoint(nfp_f).buffer(0.000000001)])
    coords_externas = [(round(x, 1), round(y, 1)) for x, y in nfp_unido.exterior.coords]
    pontos_unicos_ext = []
    for ponto in coords_externas:

        if not pontos_unicos_ext or ponto != pontos_unicos_ext[-1]:
            pontos_unicos_ext.append(ponto)
    nfp_unido = Polygon(pontos_unicos_ext)
    polyA = Polygon(pontos_pol_A)
    polyB = Polygon(pontos_pol_B)
    pontos_de_encontro_validos = []
    for ponto in extrair_vertices(intersec):
        polyB_na_posicao = affinity.translate(polyB, xoff=ponto[0], yoff=ponto[1])

        if not polyA.overlaps(polyB_na_posicao) and polyA.touches(polyB_na_posicao):
                pontos_de_encontro_validos.append(ponto)
    intersec = MultiPoint(pontos_de_encontro_validos)
    return nfp_unido, extrair_vertices(intersec)


def extrair_vertices(encaixes):

    if encaixes is None or encaixes.is_empty:
        return []
    vertices = []

    if isinstance(encaixes, MultiPolygon):
        for poly in encaixes.geoms:
            vertices.extend(list(poly.exterior.coords))
            for hole in poly.interiors:
                vertices.extend(list(hole.coords))
    elif isinstance(encaixes, Polygon):
        vertices.extend(list(encaixes.exterior.coords))
        for hole in encaixes.interiors:
            vertices.extend(list(hole.coords))
    elif isinstance(encaixes, MultiLineString):
        for line in encaixes.geoms:
            vertices.extend(list(line.coords))
    elif isinstance(encaixes, LineString):
        vertices.extend(list(encaixes.coords))
    elif isinstance(encaixes, Point):
        vertices.append((encaixes.x, encaixes.y))
    elif isinstance(encaixes, MultiPoint):
        for pt in encaixes.geoms:
            vertices.append((pt.x, pt.y))
    elif isinstance(encaixes, LinearRing):
        vertices.extend(list(encaixes.coords))
    elif isinstance(encaixes, GeometryCollection):
        encaixe = encaixes
        for encaixes in encaixe.geoms:

            if isinstance(encaixes, MultiPolygon):
                for poly in encaixes.geoms:
                    vertices.extend(list(poly.exterior.coords))
                    for hole in poly.interiors:
                        vertices.extend(list(hole.coords))
            elif isinstance(encaixes, Polygon):
                vertices.extend(list(encaixes.exterior.coords))
                for hole in encaixes.interiors:
                    vertices.extend(list(hole.coords))
            elif isinstance(encaixes, MultiLineString):
                for line in encaixes.geoms:
                    vertices.extend(list(line.coords))
            elif isinstance(encaixes, LineString):
                vertices.extend(list(encaixes.coords))
            elif isinstance(encaixes, Point):
                vertices.append((encaixes.x, encaixes.y))
            elif isinstance(encaixes, MultiPoint):
                for pt in encaixes.geoms:
                    vertices.append((pt.x, pt.y))
            elif isinstance(encaixes, LinearRing):
                vertices.extend(list(encaixes.coords))
    return vertices


def rotate_point(x: float, y: float, angle_deg: float) -> Tuple[float, float]:
    rad = math.radians(angle_deg % 360)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)
    x_rot = x * cos_a - y * sin_a
    y_rot = x * sin_a + y * cos_a
    return x_rot, y_rot


def calcular_shrink_factor(x):

    if x < 0.1:
        return 0.9 - x
    else:
        return 1 + 0.1 * math.log10(x)


def calcular_dimensoes(lista):
    area = 0
    for pol in lista:
        area += Polygon(pol).area
    base = math.sqrt(area * 2)
    altura = base
    escala = 1
    graus = [0, 1, 2, 3]
    return base, altura, escala, graus


class SPP2D():


    def __init__(self,dataset='fu',Base=None,Altura=None,Escala=None, Graus = None, tabela = None, margem = 0, tempo=200, pairwise_IN = False):
        self.save_q_learning_report = True
        self.counter = 0
        self.BRKGA_parameters = {
            'p': [100, 50],
            'pe': [0.20, 0.15],
            'pm': [0.05],
            'rhoe': [0.70]
        }
        self.SA_parameters = {
            'SAmax': [10, 5],
            'alphaSA': [0.9, 0.99],
            'betaMin': [0.01, 0.03, 0.05, 0.1],
            'betaMax': [0.25, 0.2],
            'T0': [1000]
        }
        self.ILS_parameters = {
            'betaMin': [0.10,0.15],
            'betaMax': [0.30,0.25]
        }
        self.VNS_parameters = {
            'kMax': [5,3],
            'betaMin': [0.05, 0.1, 0.15]
        }
        self.PSO_parameters = {
            'PSize': [100,50],
            'c1': [2.05],
            'c2': [2.05],
            'w': [0.73]
        }
        self.GA_parameters = {
            'sizePop': [100,50],
            'probCros': [0.98],
            'probMut': [0.005, 0.01]
        }
        self.LNS_parameters = {
            'betaMin': [0.10],
            'betaMax': [0.30],
            'TO': [100],
            'alphaLNS': [0.95,0.9]
        }
        self.max_time = tempo
        self.start_time = time.time()
        self.dataset = dataset
        self.instance_name = dataset
        lista = ler_poligonos(self.dataset)

        if Base == None and Altura == None and Escala == None:
            self.base, self.altura, self.escala, self.graus = dimensions(dataset)

            if self.base is None or self.altura is None or self.escala is None or self.graus is None:
                self.base, self.altura, self.escala, self.graus = calcular_dimensoes(lista)
        else:
            self.base = Base
            self.altura = Altura
            self.escala = Escala
            self.graus = Graus
        self.area = self.base * self.altura
        self.base_inicial = self.base
        self.inicial = False
        lista = ler_poligonos(self.dataset)
        lista.sort(
                key=lambda coords: Polygon(coords).area,
                reverse=True
            )
        self.lista_original = lista
        self.lista = copy.deepcopy(self.lista_original)
        porcentagens_por_dataset = {
            'albano': 0.0,
            'dagli': 0.0,
            'dighe1': 0.0,
            'dighe2': 0.0,
            'fu': 0.0,
            'jackobs1': 0.0,
            'jackobs2': 0.40,
            'mao': 0.0,
            'marques': 0.0,
            'shapes0': 0.0,
            'shapes1': 0.0,
            'shapes2': 0.25,
            'shirts': 0.0,
            'swim': 0.15,
            'trousers': 0.0
        }
        porcentagem = porcentagens_por_dataset.get(self.dataset.lower(), 0.0)
        pairwise = pairwise_IN and (porcentagem > 0)
        self.cordenadas_area = ( [0,0] , [self.base,0] , [self.base,self.altura] , [0,self.altura] )
        self.pecas_posicionadas = []
        self.indices_pecas_posicionadas = []
        self.dict_nfps = {}
        self.dict_sol = {}
        self.LS_type = 'Best'
        self.greedy = []
        self.dict_best = {
                    "fu": -92.41,
                    "jackobs1": -89.10,
                    "jackobs2": -87.73,
                    "shapes0": -68.79,
                    "shapes1": -76.73,
                    "shapes2": -84.84,
                    "dighe1": -100.00,
                    "dighe2": -100.00,
                    "albano": -89.58,
                    "dagli": -89.51,
                    "mao": -85.44,
                    "marques": -90.59,
                    "shirts": -88.96,
                    "swim": -75.94,
                    "trousers": -91.00,
                    "ED-10": -85.00,
                }
        self.dict_feasible = {}
        self.lista_anterior = []
        self.best_fit = 100000
        print("aaaaaaaaaaaaaaaaaaaaaaa")

        if tabela is not None:
            self.tabela_nfps = tabela
        else:
            pairwise_mode = pairwise_IN and (porcentagem > 0)

            if pairwise_mode:
                nfp_file = f"C:\\Users\\felip\\Documents\\GitHub\\RKO\\nfp_{self.dataset}.txt"

                if os.path.exists(nfp_file):
                    with open(nfp_file, "r") as f:
                        conteudo = f.read()
                    self.tabela_nfps = ast.literal_eval(conteudo)
                else:
                    self.tabela_nfps = pre_processar_NFP(self.graus, self.lista, margem, self)
                    with open(nfp_file, "w") as f:
                        f.write(repr(self.tabela_nfps))
                pares_selecionados = self.pairwise(porcentagem_cluster=porcentagem)
                self.lista = self.criar_lista_clusterizada(pares_selecionados)
                self.lista_original = copy.deepcopy(self.lista)
                nfp_file = f"nfp_{self.dataset}_novo_pairwise_2.txt"

                if os.path.exists(nfp_file):
                    with open(nfp_file, "r") as f:
                        conteudo = f.read()
                    self.tabela_nfps = ast.literal_eval(conteudo)
                else:
                    self.tabela_nfps = pre_processar_NFP(self.graus, self.lista, margem, self)
                    with open(nfp_file, "w") as f:
                        f.write(repr(self.tabela_nfps))
            else:
                nfp_file = f"C:\\Users\\felip\\Documents\\GitHub\\RKO\\nfp_{self.dataset}.txt"

                if os.path.exists(nfp_file):
                    with open(nfp_file, "r") as f:
                        conteudo = f.read()
                    self.tabela_nfps = ast.literal_eval(conteudo)
                else:
                    self.tabela_nfps = pre_processar_NFP(self.graus, self.lista, margem, self)
                    with open(nfp_file, "w") as f:
                        f.write(repr(self.tabela_nfps))
        self.lista.sort(
                key=lambda coords: Polygon(coords).area,
                reverse=True
            )
        self.lista_original.sort(
                key=lambda coords: Polygon(coords).area,
                reverse=True
            )
        self.max_pecas = len(self.lista_original)
        self.tam_solution = 2 * self.max_pecas + 1
        self.regras = {
            0: self.BL,
            1: self.LB,
            2: self.BR,
            3: self.RB,
            4: self.UL,
            5: self.LU,
            6: self.UR,
            7: self.RU,
            8: self.NC,
            9: self.NCG,
            10: self.NCNFP
        }


    def plot_pairwise_geometries(self, peca1_poly, peca2_poly, nfp_poly, titulo="", filepath="."):
        fig, ax = plt.subplots(figsize=(10, 8))
        x, y = peca1_poly.exterior.xy
        ax.fill(x, y, alpha=0.6, fc='blue', ec='black', label='Peça 1 (Fixa)')
        x, y = peca2_poly.exterior.xy
        ax.fill(x, y, alpha=0.6, fc='green', ec='black', label='Peça 2 (Móvel)')

        if nfp_poly and not nfp_poly.is_empty:
            x, y = nfp_poly.exterior.xy
            ax.plot(x, y, color='red', linestyle='--', linewidth=2, label='NFP')
        ax.set_aspect('equal', adjustable='box')
        ax.legend()
        safe_filename = titulo.split('\n')[0].replace(' | ', '_').replace(':', '').replace('.', 'p') + ".png"
        ax.set_title(titulo)
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        os.makedirs(filepath, exist_ok=True)
        full_path = os.path.join(filepath, safe_filename)
        plt.savefig(full_path, bbox_inches='tight')
        plt.close(fig)


    def find_dominant_point(self, nfp_poly):

        if nfp_poly is None or nfp_poly.is_empty or not hasattr(nfp_poly, 'exterior'):
            return None
        ch = nfp_poly.convex_hull

        if nfp_poly.area >= ch.area - 1e-9:
            return None
        vacancies = ch.difference(nfp_poly)

        if vacancies.is_empty:
            return None

        if isinstance(vacancies, Polygon):
            vacancies = [vacancies]
        else:
            vacancies = list(vacancies.geoms)
        max_dist = -1
        dominant_point = None
        for vacancy in vacancies:
            opponent_side = vacancy.boundary.intersection(ch.boundary)

            if opponent_side.is_empty or not isinstance(opponent_side, (LineString, Point)):
                continue
            points_to_check_geom = nfp_poly.boundary.intersection(vacancy)
            all_coords = []

            if hasattr(points_to_check_geom, 'geoms'):
                for geom in points_to_check_geom.geoms:
                    all_coords.extend(list(geom.coords))
            elif hasattr(points_to_check_geom, 'coords'):
                all_coords = list(points_to_check_geom.coords)
            for p_coords in all_coords:
                p = Point(p_coords)
                dist = p.distance(opponent_side)

                if dist > max_dist:
                    max_dist = dist
                    dominant_point = p_coords
        return dominant_point


    def pairwise(self, porcentagem_cluster=0.2):

        if porcentagem_cluster == 0:
            return
        avaliacoes = []
        pairwise_cache = {}
        pecas_a_analisar = range(len(self.lista_original))
        rotacoes_a_analisar = self.graus
        tipos_unicos = []
        for peca in self.lista_original:

            if peca not in tipos_unicos:
                tipos_unicos.append(peca)
        num_tipos = len(tipos_unicos)
        num_pares_tipos = (num_tipos * (num_tipos - 1)) / 2 + num_tipos
        total_steps = int(num_pares_tipos * (len(rotacoes_a_analisar)**2))
        step = 0
        print(f"Iniciando análise de pairwise... Total de combinações de TIPOS de peça/rotações: ~{total_steps}")
        for i in pecas_a_analisar:
            for j in range(i + 1, len(pecas_a_analisar)):
                for grau1_idx in rotacoes_a_analisar:
                    for grau2_idx in rotacoes_a_analisar:
                        shape1_coords = tuple(map(tuple, self.lista_original[i]))
                        shape2_coords = tuple(map(tuple, self.lista_original[j]))
                        key_shapes = tuple(sorted((shape1_coords, shape2_coords)))
                        cache_key = (key_shapes[0], grau1_idx, key_shapes[1], grau2_idx)

                        if cache_key in pairwise_cache:
                            cached_result = pairwise_cache[cache_key]

                            if cached_result:
                                avaliacoes.append({**cached_result, 'i': i, 'j': j, 'grau1': grau1_idx, 'grau2': grau2_idx})
                            continue
                        step += 1
                        print(f"Progresso (cálculo novo): {step}/{total_steps}", end='\r')
                        self.reset()
                        self.acao(i, 0, 0, grau1_idx)
                        nfp_result, intersec_result = self.nfp(self.lista.index(self.lista_original[j]), grau2_idx)
                        self.remover_ultima_acao()

                        if not nfp_result or nfp_result.is_empty:
                            pairwise_cache[cache_key] = None
                            continue
                        pontos_candidatos = []
                        dominant_point = self.find_dominant_point(nfp_result)

                        if dominant_point: pontos_candidatos.append(dominant_point)

                        if intersec_result and not intersec_result.is_empty:
                            pontos_candidatos.extend(extrair_vertices(intersec_result))

                        if not pontos_candidatos:
                            pairwise_cache[cache_key] = None
                            continue
                        pontos_candidatos = list(dict.fromkeys(pontos_candidatos))
                        best_value_for_key = -1
                        best_config_for_key = None
                        for ponto_encaixe in pontos_candidatos:
                            poly1 = Polygon(self.rot_pol(i, grau1_idx))
                            poly2_coords = self.rot_pol(j, grau2_idx)
                            poly2 = Polygon([(p[0] + ponto_encaixe[0], p[1] + ponto_encaixe[1]) for p in poly2_coords])
                            ch_poly1 = poly1.convex_hull
                            ch_poly2 = poly2.convex_hull
                            ch_uniao = unary_union([poly1, poly2]).convex_hull
                            ratio1_alt = ch_poly1.intersection(poly2).area / ch_poly1.area if ch_poly1.area > 1e-9 else 0
                            ratio2_alt = ch_poly2.intersection(poly1).area / ch_poly2.area if ch_poly2.area > 1e-9 else 0
                            cr1 = max(ratio1_alt, ratio2_alt)
                            cr2 = (poly1.area + poly2.area) / ch_uniao.area if ch_uniao.area > 1e-9 else 0
                            cluster_value = cr1 * cr2

                            if cluster_value > best_value_for_key:
                                best_value_for_key = cluster_value
                                best_config_for_key = {
                                    'value': cluster_value, 'ponto_encaixe': ponto_encaixe,
                                    'cr1': cr1, 'cr2': cr2
                                }
                        pairwise_cache[cache_key] = best_config_for_key

                        if best_config_for_key:
                            avaliacoes.append({**best_config_for_key, 'i': i, 'j': j, 'grau1': grau1_idx, 'grau2': grau2_idx})
        print("\nAnálise concluída. Selecionando e salvando imagens dos melhores resultados...")

        if not avaliacoes:
            print("Nenhuma configuração válida foi encontrada.")
            return
        avaliacoes.sort(key=lambda x: x['value'], reverse=True)
        num_total_pecas = len(self.lista_original)
        num_pares_desejado = int((num_total_pecas * porcentagem_cluster) / 2)
        pares_finais_para_plotar = []
        pecas_ja_agrupadas = set()
        for aval in avaliacoes:

            if len(pares_finais_para_plotar) >= num_pares_desejado:
                break
            peca1_idx = aval['i']
            peca2_idx = aval['j']

            if peca1_idx not in pecas_ja_agrupadas and peca2_idx not in pecas_ja_agrupadas:
                pares_finais_para_plotar.append(aval)
                pecas_ja_agrupadas.add(peca1_idx)
                pecas_ja_agrupadas.add(peca2_idx)
        print(f"\n--- Salvando imagens para {len(pares_finais_para_plotar)}/{num_pares_desejado} pares encontrados ({porcentagem_cluster:.0%}) ---")
        save_path = f"C:\\Users\\felip\\OneDrive\\Documentos\\GitHub\\RKO\\Python\\pairwise_results_20\\{self.dataset}"
        for rank, aval in enumerate(pares_finais_para_plotar):
            self.reset()
            poly1 = Polygon(self.rot_pol(aval['i'], aval['grau1']))
            ponto = aval['ponto_encaixe']
            poly2_coords = self.rot_pol(aval['j'], aval['grau2'])
            poly2 = Polygon([(p[0] + ponto[0], p[1] + ponto[1]) for p in poly2_coords])
            self.acao(aval['i'], 0, 0, aval['grau1'])
            nfp_plot, _ = self.nfp(self.lista.index(self.lista_original[aval['j']]), aval['grau2'])
            self.remover_ultima_acao()
            titulo = (f"Rank #{rank + 1} | CV {aval['value']:.3f}\n"
                    f"P ({aval['i']},{aval['j']}) G ({aval['grau1']},{aval['grau2']})\n"
                    f"Cr1 {aval['cr1']:.3f}, Cr2 {aval['cr2']:.3f}")
            self.plot_pairwise_geometries(poly1, poly2, nfp_plot, titulo, filepath=save_path)
        return pares_finais_para_plotar


    def criar_lista_clusterizada(self, pares_selecionados):

        if not pares_selecionados:
            print("INFO: Nenhum par selecionado. Retornando a lista original.")
            return self.lista_original
        print(f"INFO: Criando nova lista de peças com {len(pares_selecionados)} clusters...")
        pecas_agrupadas_indices = set()
        nova_lista_de_pecas = []
        for par in pares_selecionados:
            i, j = par['i'], par['j']
            g1, g2 = par['grau1'], par['grau2']
            ponto_encaixe = par['ponto_encaixe']
            pecas_agrupadas_indices.add(i)
            pecas_agrupadas_indices.add(j)
            poly1 = Polygon(self.rot_pol(i, g1))
            poly2_coords = self.rot_pol(j, g2)
            poly2_translated = Polygon([(p[0] + ponto_encaixe[0], p[1] + ponto_encaixe[1]) for p in poly2_coords])
            uniao = unary_union([poly1, poly2_translated]).buffer(0)

            if hasattr(uniao, 'geoms'):
                uniao = max(uniao.geoms, key=lambda p: p.area)
            meta_peca = [(round(x,2), round(y,2)) for x,y in uniao.exterior.coords]
            meta_peca_poly = []
            for cor in meta_peca:

                if cor not in meta_peca_poly:
                    meta_peca_poly.append(cor)
            ring = LinearRing(meta_peca_poly)

            if ring.is_ccw:
                coords_ccw = list(ring.coords)
            else:
                coords_ccw = list(ring.coords)[::-1]

            if coords_ccw and coords_ccw[0] == coords_ccw[-1]:
                coords_finais_para_lib = coords_ccw[:-1]
            else:
                coords_finais_para_lib = coords_ccw
            meta_peca_poly = coords_finais_para_lib
            print(meta_peca_poly)
            nova_lista_de_pecas.append(meta_peca_poly)
        for i, peca_coords in enumerate(self.lista_original):

            if i not in pecas_agrupadas_indices:
                nova_lista_de_pecas.append(peca_coords)
        print(f"INFO: Nova lista de peças criada com {len(nova_lista_de_pecas)} itens.")
        return nova_lista_de_pecas


    def acao(self,peca,x,y,grau_idx):
        peca_posicionar = self.rot_pol(peca, grau_idx)
        pontos_posicionar = [(x + cor[0], y + cor[1]) for cor in peca_posicionar]
        self.pecas_posicionadas.append(pontos_posicionar)
        self.indices_pecas_posicionadas.append([x,y,grau_idx,self.lista_original.index(self.lista[peca])])
        self.lista_anterior.append(copy.deepcopy(self.lista))
        self.lista.pop(peca)


    def reset(self):
        self.lista = copy.deepcopy(self.lista_original)
        self.pecas_posicionadas = []
        self.indices_pecas_posicionadas = []


    def remover_ultima_acao(self):

        if self.pecas_posicionadas:
            self.lista = copy.deepcopy(self.lista_anterior[-1])
            self.lista_anterior.pop()
            self.pecas_posicionadas.pop()
            self.indices_pecas_posicionadas.pop()


    def rot_pol(self,pol, grau_indice):
        pontos = self.lista[pol]
        px, py = pontos[0]
        resultado = []
        for x, y in pontos:
            dx, dy = x - px, y - py

            if grau_indice == 0:
                nx, ny = dx, dy
            elif grau_indice == 1:
                nx, ny = -dy, dx
            elif grau_indice == 2:
                nx, ny = -dx, -dy
            elif grau_indice == 3:
                nx, ny = dy, -dx
            resultado.append([px + nx, py + ny])
        min_x = min(p[0] for p in resultado)
        min_y = min(p[1] for p in resultado)

        if min_x < 0 or min_y < 0:
            resultado = [(x - min_x if min_x < 0 else x,
                        y - min_y if min_y < 0 else y) for x, y in resultado]
        return resultado


    def ifp(self, peca_idx,grau_indice):
        peca = self.rot_pol(peca_idx,grau_indice)
        maxx = max([x for x,y in peca])
        maxy = max([y for x,y in peca])
        minx = min([x for x,y in peca])
        miny = min([y for x,y in peca])

        if (maxx - minx) > (self.base) or (maxy - miny) > (self.altura):
            return []
        cords = self.cordenadas_area
        v0 = (0 - minx, 0 - miny)
        v1 = (self.base - maxx, 0 - miny)
        v2 = (self.base - maxx, self.altura - maxy)
        v3 = (0 - minx, self.altura - maxy)
        ifp = [v0,v1,v2,v3]
        return ifp


    def nfp(self, peca, grau_indice):
        nfps = []
        todos_pontos_de_encontro = []
        chaves = []
        maior_nfp = (Polygon(), MultiPoint())
        start_nfp = 0
        i = 0
        for x2, y2, grau1, pol_idx in self.indices_pecas_posicionadas:
            chave = (
                tuple(self.lista_original[pol_idx]), grau1,
                tuple(self.lista[peca]), grau_indice
            )
            chaves.append((chave, x2, y2))
            i+=1

            if tuple(chaves) in self.dict_nfps:
                maior_nfp = self.dict_nfps[tuple(chaves)]
                start_nfp = i
        prefixo_t = tuple(chaves)

        if prefixo_t in self.dict_nfps:
            return self.dict_nfps[prefixo_t]
        for (chave, x2, y2) in chaves[start_nfp:]:
            nfp_salvo = self.tabela_nfps.get(chave)

            if not nfp_salvo:
                continue
            coords_base_nfp = nfp_salvo[0]
            pontos_intersec_base = nfp_salvo[1]
            base_nfp = Polygon(coords_base_nfp)

            if base_nfp.is_empty:
                continue
            p = affinity.translate(base_nfp, xoff=x2, yoff=y2)
            nfps.append(p)

            if pontos_intersec_base:
                pontos_transladados = [(pt[0] + x2, pt[1] + y2) for pt in pontos_intersec_base]
                todos_pontos_de_encontro.append((pontos_transladados, p))

        if not nfps:
            return None, None

        if maior_nfp[1] is not None and maior_nfp[0] is not None:
            todos_pontos_de_encontro.append((list(maior_nfp[1].geoms), maior_nfp[0]))
        ocupado = unary_union([maior_nfp[0].buffer(-0.000001)] + [nfp.buffer(-0.000001) for nfp in nfps])
        pontos_validos = []

        if todos_pontos_de_encontro:
            for pontos, nfp_origem in todos_pontos_de_encontro :
                for ponto in pontos:
                    valido = True
                    pt = Point(ponto)
                    for nfp in nfps + [maior_nfp[0]]:

                        if nfp == nfp_origem:
                            continue

                        if nfp.contains(pt):
                            valido = False
                            break

                    if valido:
                        pontos_validos.append(ponto)
        intersec_final = MultiPoint(pontos_validos ) if pontos_validos else None
        self.dict_nfps[prefixo_t] = (ocupado, intersec_final)
        return ocupado, intersec_final


    def feasible(self, peca, grau_indice, area=False):
        chave = tuple([peca, grau_indice, tuple(map(tuple, self.pecas_posicionadas)), self.base, self.altura])

        if chave in self.dict_feasible:
            cached_result = self.dict_feasible[chave]

            if area:
                return cached_result['vertices'], cached_result['area']
            return cached_result['vertices']
        ifp_coords = self.ifp(peca, grau_indice)

        if not ifp_coords:
            return ([], 0) if area else []
        ifp_polygon = Polygon(ifp_coords)

        if not self.pecas_posicionadas:
            vertices = list(ifp_polygon.exterior.coords)

            if area:
                return vertices, ifp_polygon.area
            return vertices
        nfp_polygon, nfp_intersec = self.nfp(peca, grau_indice)
        intersec = ifp_polygon.boundary.intersection(nfp_polygon.boundary) if nfp_polygon else None
        pts = []

        if intersec and not intersec.is_empty:

            if intersec.geom_type == 'Point':
                pts = [(intersec.x, intersec.y)]
            else:
                for part in getattr(intersec, 'geoms', [intersec]):

                    if hasattr(part, 'coords'):
                        pts.extend(list(part.coords))

        if nfp_polygon and not nfp_polygon.is_empty:
            encaixes = ifp_polygon.difference(nfp_polygon)
        else:
            encaixes = ifp_polygon
        vertices = extrair_vertices(encaixes)
        vertices.extend(pts)

        if nfp_intersec:
            intersecao = extrair_vertices(nfp_intersec.intersection(ifp_polygon))
            for ponto in intersecao:

                if ponto not in vertices:
                    vertices.append(ponto)
        coords_externas = [(round(x, 1), round(y, 1)) for x, y in vertices]
        pontos_unicos_ext = []
        for ponto in coords_externas:

            if not pontos_unicos_ext or ponto != pontos_unicos_ext[-1]:
                pontos_unicos_ext.append(ponto)
        vertices_validos = coords_externas
        encaixes_area = encaixes.area if encaixes else 0
        self.dict_feasible[chave] = {'vertices': vertices_validos, 'area': encaixes_area}

        if area:
            return vertices_validos, encaixes_area
        else:
            return vertices_validos


    def BL(self, peca, grau_indice):
        positions = self.feasible(peca,grau_indice)

        if not positions:
            return []
        positions_bl = sorted(positions, key=lambda ponto: (ponto[0], ponto[1]))
        bl = positions_bl[0]
        return bl


    def BL_NFP(self, peca, grau_indice):
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]

        if not nfp_positions:
            positions_to_use = all_positions
        else:
            positions_to_use = nfp_positions

        if not positions_to_use:
            return []
        sorted_positions = sorted(positions_to_use, key=lambda ponto: (ponto[0], ponto[1]))
        bl_position = sorted_positions[0]
        return bl_position


    def LB_NFP(self, peca, grau_indice):
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        positions_to_use = nfp_positions if nfp_positions else all_positions

        if not positions_to_use:
            return []
        sorted_positions = sorted(positions_to_use, key=lambda ponto: (ponto[1], ponto[0]))
        return sorted_positions[0]


    def BR_NFP(self, peca, grau_indice):
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        positions_to_use = nfp_positions if nfp_positions else all_positions

        if not positions_to_use:
            return []
        sorted_positions = sorted(positions_to_use, key=lambda ponto: (-ponto[0], ponto[1]))
        return sorted_positions[0]


    def RB_NFP(self, peca, grau_indice):
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        positions_to_use = nfp_positions if nfp_positions else all_positions

        if not positions_to_use:
            return []
        sorted_positions = sorted(positions_to_use, key=lambda ponto: (ponto[1], -ponto[0]))
        return sorted_positions[0]


    def UL_NFP(self, peca, grau_indice):
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        positions_to_use = nfp_positions if nfp_positions else all_positions

        if not positions_to_use:
            return []
        sorted_positions = sorted(positions_to_use, key=lambda ponto: (ponto[0], -ponto[1]))
        return sorted_positions[0]


    def LU_NFP(self, peca, grau_indice):
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        positions_to_use = nfp_positions if nfp_positions else all_positions

        if not positions_to_use:
            return []
        sorted_positions = sorted(positions_to_use, key=lambda ponto: (-ponto[1], ponto[0]))
        return sorted_positions[0]


    def UR_NFP(self, peca, grau_indice):
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        positions_to_use = nfp_positions if nfp_positions else all_positions

        if not positions_to_use:
            return []
        sorted_positions = sorted(positions_to_use, key=lambda ponto: (-ponto[0], -ponto[1]))
        return sorted_positions[0]


    def RU_NFP(self, peca, grau_indice):
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        positions_to_use = nfp_positions if nfp_positions else all_positions

        if not positions_to_use:
            return []
        sorted_positions = sorted(positions_to_use, key=lambda ponto: (-ponto[1], -ponto[0]))
        return sorted_positions[0]


    def NC(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        centro_bin = (self.base / 2, self.altura / 2)
        sorted_positions = sorted(positions,
                                key=lambda ponto: math.dist(ponto, centro_bin))
        return sorted_positions[0]


    def NCNFP(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        sum_x = 0
        sum_y = 0
        len_vertices = len(positions)
        for pos in positions:
            sum_x+=pos[0]
            sum_y+=pos[1]
        centro_nfp = (sum_x/len_vertices , sum_y/len_vertices)
        sorted_positions = sorted(positions,
                                key=lambda ponto: math.dist(ponto, centro_nfp))
        return sorted_positions[0]


    def NCG(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []

        if not self.pecas_posicionadas:
            centro_bin = (self.base / 2, self.altura / 2)
            sorted_positions = sorted(positions,
                                    key=lambda ponto: math.dist(ponto, centro_bin))
            return sorted_positions[0]
        num_vertices = 0
        soma_x = 0
        soma_y = 0
        centros = []
        for peca in self.pecas_posicionadas:
            soma_x_peca = sum([x for x,y in peca])
            soma_y_peca = sum([y for x,y in peca])
            centros.append((soma_x_peca/len(peca) , soma_y_peca/len(peca)))
        soma_x = sum([x for x,y in centros])
        soma_y = sum([y for x,y in centros])
        num_vertices = len(self.pecas_posicionadas)
        centro_layout = (soma_x / num_vertices, soma_y / num_vertices)
        sorted_positions = sorted(positions,
                                key=lambda ponto: math.dist(ponto, centro_layout))
        return sorted_positions[0]


    def NBL(self, peca, grau_indice):
        positions = self.feasible(peca,grau_indice)

        if not positions:
            return []
        positions_bl = sorted(positions, key=lambda ponto: (ponto[0]**2 + ponto[1]**2))
        nbl = positions_bl[0]
        return nbl


    def NUL(self, peca, grau_indice):
        positions = self.feasible(peca,grau_indice)

        if not positions:
            return []
        positions_bl = sorted(positions, key=lambda ponto: (ponto[0]**2 + (self.base - ponto[1])**2))
        nul = positions_bl[0]
        return nul


    def LB(self, peca, grau_indice):
        positions = self.feasible(peca,grau_indice)

        if not positions:
            return []
        positions_lb = sorted(positions, key=lambda ponto: (ponto[1], ponto[0]))
        lb = positions_lb[0]
        return lb


    def BR(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        positions_br = sorted(positions, key=lambda ponto: (-ponto[0], ponto[1]))
        br = positions_br[0]
        return br


    def RB(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        positions_rb = sorted(positions, key=lambda ponto: (ponto[1], -ponto[0]))
        rb = positions_rb[0]
        return rb


    def UL(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        positions_ul = sorted(positions, key=lambda ponto: (ponto[0], -ponto[1]))
        ul = positions_ul[0]
        return ul


    def LU(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        positions_lu = sorted(positions, key=lambda ponto: (-ponto[1], ponto[0]))
        lu = positions_lu[0]
        return lu


    def UR(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        positions_ur = sorted(positions, key=lambda ponto: (-ponto[0], -ponto[1]))
        ur = positions_ur[0]
        return ur


    def RU(self, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        positions_ru = sorted(positions, key=lambda ponto: (-ponto[1], -ponto[0]))
        ru = positions_ru[0]
        return ru


    def avaliar_posicoes_onepass(self, pos, peca_idx, grau_indice):
        fits = []
        seen_pecas = []
        self.acao(peca_idx, pos[0], pos[1], grau_indice)
        for peca in self.lista:

            if peca in seen_pecas:
                continue
            seen_pecas.append(peca)
            for grau in self.graus:
                _, area = self.feasible(self.lista.index(peca), grau, True)
                fit = Polygon(peca).area/ area if area > 0 else 0
                fits.append(fit)

        if fits == []:
            fit = pos[0]
        else:
            fit = pos[0] * (sum(fits) / len(fits))
        self.remover_ultima_acao()
        return fit


    def OnePass(self, peca, grau_indice):
        positions = []
        for regra in range(len(self.regras) -  1):
            pos = self.regras[regra](peca, grau_indice)

            if pos and pos not in positions:
                positions.append(pos)
        best_pos = None
        best_fit = float('inf')
        for pos in positions:
            fit = self.avaliar_posicoes_onepass(pos, peca, grau_indice)

            if fit < best_fit:
                best_fit = fit
                best_pos = pos
        return best_pos


    def key_nfp(self, key, peca, grau_indice):
        positions = self.feasible(peca, grau_indice)

        if not positions:
            return []
        return positions[int(key * len(positions))]


    def pack(self, peca, grau_indice, regra_idx, regra = True):

        if regra:
            pos = self.regras[regra_idx](peca, grau_indice)

            if pos:
                self.acao(peca, pos[0], pos[1], grau_indice)
                return True
            return False
        else:
            pos = self.key_nfp(regra_idx, peca, grau_indice)

            if pos:
                self.acao(peca, pos[0], pos[1], grau_indice)
                return True
            return False


    def decoder(self, keys):
        N = self.max_pecas
        tipos_rot = len(self.graus)
        tipos_regras = len(self.regras)
        rot_keys = keys[:N]
        rot_idx = [self.graus[int(k * tipos_rot)] for k in rot_keys]
        regras_keys = keys[N:2*N]
        regras_idx = [int(k * tipos_regras) for k in regras_keys]
        shrink_factor = keys[-1]
        return rot_idx + regras_idx + [shrink_factor]


    def cost(self, sol, tag=0, save=True):
        sol_tuple = tuple(sol)

        if sol_tuple in self.dict_sol:
            return self.dict_sol[sol_tuple]
        N = self.max_pecas
        rot = sol[:N]
        regras = sol[N:2*N]
        shrink_factor = sol[-1]
        base_antigo = self.base

        if not (self.inicial == False and self.base == self.base_inicial):
            self.base = ((self.base - 0.99*self.base) * shrink_factor) + 0.99*self.base
        nao_posicionadas = []
        for i, peca in enumerate(self.lista_original):
            try:
                peca_idx_lista = self.lista.index(peca)
                packed = self.pack(peca_idx_lista, rot[i], regras[i])

                if not packed:
                    nao_posicionadas.append((peca, i))
            except ValueError:
                continue

        if len(self.pecas_posicionadas) == self.max_pecas:
            self.inicial = True
            fit = -1 * self.area_usada()
            self.dict_sol[sol_tuple] = fit

            if fit < self.best_fit:
                self.best_fit = fit
            self.reset()
            return fit
        else:
            self.base = base_antigo
            for peca, idx in nao_posicionadas:
                try:
                    peca_idx_lista = self.lista.index(peca)
                    self.pack(peca_idx_lista, rot[idx], regras[idx])
                except ValueError:
                    continue
            fit = -1 * self.area_usada()

            if len(self.pecas_posicionadas) != self.max_pecas:
                fit = sum([Polygon(pol).area for pol in self.lista]) * 100 / (self.base * self.altura)
                self.reset()
                self.dict_sol[sol_tuple] = fit
                return fit
            self.inicial = True
            self.reset()
            return fit


    def plot(self, legenda):
        draw_cutting_area(self.pecas_posicionadas, self.base, self.altura ,legenda=legenda, filename=f'C:\\Users\\felip\\Documents\\GitHub\\RKO\\Python\\Images\\SPP\\{self.instance_name}\\{self.instance_name}_{time.time()}.png')


    def get_used_width(self):
        original_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista_original)
        nao_usado_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista)
        usados_counter = original_counter - nao_usado_counter
        usados = []
        for pol, count in usados_counter.items():
            usados.extend([list(pol) for _ in range(count)])
        area_total = sum(Polygon(pol).area for pol in usados)
        coords = []
        for pol in self.pecas_posicionadas:
            for x,y in pol:
                coords.append(x)

        if coords == []:
            return 0
        larg = max(coords) - min(coords)
        area_bin = (larg / self.escala) * (self.altura / self.escala)
        return larg


    def get_efficiency(self):
        original_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista_original)
        nao_usado_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista)
        usados_counter = original_counter - nao_usado_counter
        usados = []
        for pol, count in usados_counter.items():
            usados.extend([list(pol) for _ in range(count)])
        area_total = sum(Polygon(pol).area for pol in usados)
        coords = []
        for pol in self.pecas_posicionadas:
            for x,y in pol:
                coords.append(x)

        if coords == []:
            return 0
        larg = max(coords) - min(coords)
        area_bin = (larg / self.escala) * (self.altura / self.escala)
        return round((area_total / area_bin) * 100, 2)


    def area_usada(self):
        original_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista_original)
        nao_usado_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista)
        usados_counter = original_counter - nao_usado_counter
        usados = []
        for pol, count in usados_counter.items():
            usados.extend([list(pol) for _ in range(count)])
        area_total = sum(Polygon(pol).area for pol in usados)
        coords = []
        for pol in self.pecas_posicionadas:
            for x,y in pol:
                coords.append(x)
        larg = max(coords) - min(coords)
        area_bin = (larg / self.escala) * (self.altura / self.escala)
        return round((area_total / area_bin) * 100, 2)

if __name__ == '__main__':
    INSTANCES = ["fu", "jackobs1", "jackobs2"]
    TIME_LIMIT = 60
    RESTART_RATIO = 0.5
    NUM_RUNS = 1
    USE_PAIRWISE = True
    SAVE_DIR = os.path.join(_OUTPUT_DIR, "results_SPP")
    os.makedirs(SAVE_DIR, exist_ok=True)
    for instance in INSTANCES:
        print(f"\n{'='*60}")
        print(f"Solving: {instance} | Time: {TIME_LIMIT}s")
        print(f"{'='*60}")
        env = SPP2D(
            dataset=instance,
            tempo=TIME_LIMIT * RESTART_RATIO,
            pairwise_IN=USE_PAIRWISE
        )
        save_file = os.path.join(SAVE_DIR, f"{instance}.csv")
        solver = RKO(env, print_best=True, save_directory=save_file)
        cost, sol, temp = solver.solve(
            TIME_LIMIT,
            brkga=1, ms=1, sa=1, vns=1, ils=1, lns=1, pso=1, ga=1,
            restart=RESTART_RATIO,
            runs=NUM_RUNS
        )
        env.cost(env.decoder(sol), save=True)
        print(f"Best cost: {cost}")
