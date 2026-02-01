import sys
import os
import ast
from collections import Counter
import time
import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt
import turtle
import math
import reprlib

# Get the directory of this script for relative imports
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
import cv2
import copy
import pyautogui
from matplotlib.patches import Polygon as MPolygon, Rectangle
import random
from typing import List, Tuple, Union
from shapely import affinity
from shapely.geometry import Polygon, MultiPolygon, Point, LineString
from shapely.ops import unary_union
from shapely.affinity import translate
import cProfile
import pstats


def calcular_area_continua_nao_utilizada(pecas_posicionadas,area_corte_vertices,plot=False, buffer_distance=100, name_image="layout_salvo", save=False):
    """
    Calcula a maior área contínua não utilizada, com opções para plotar e salvar.

    Args:
        pecas_posicionadas (list): Lista de polígonos (listas de vértices).
        area_corte_vertices (list): Vértices do polígono da área de corte.
        plot (bool): Se True, gera um gráfico do resultado.
        buffer_distance (float): Parâmetro para a operação de abertura morfológica.
        name_image (str): Nome base para os arquivos salvos (sem extensão).
        save (bool): Se True, salva o gráfico e os dados em arquivos em vez de exibir o gráfico.

    Returns:
        tuple: (area_continua_ponderada, porcentagem_continua, poligono_continuo)
               Retorna (0.0, 0.0, None) se não houver área livre.
    """
    # --- 1. Preparação das Geometrias ---
    area_corte_poly = Polygon(area_corte_vertices)
    polygons_shapely = [Polygon(p) for p in pecas_posicionadas]
    all_polygons_union = unary_union(polygons_shapely)

    # --- 2. Cálculo da Área Livre Total ---
    free_space = area_corte_poly.difference(all_polygons_union)

    if free_space.is_empty:
        if plot: print("Não há área livre para analisar.")
        return 0.0, 0.0, None

    # --- 3. ABERTURA MORFOLÓGICA para isolar a maior área contínua ---
    largest_continuous_polygon = None
    ch_factor = 0
    
    eroded_space = free_space.buffer(-buffer_distance)
    
    if not eroded_space.is_empty:
        if eroded_space.geom_type == 'Polygon':
            largest_eroded_polygon = eroded_space
        elif eroded_space.geom_type == 'MultiPolygon':
            largest_eroded_polygon = max(eroded_space.geoms, key=lambda p: p.area)
        else:
            largest_eroded_polygon = None
        
        if largest_eroded_polygon:
            largest_continuous_polygon = largest_eroded_polygon.buffer(buffer_distance)
            ch = largest_continuous_polygon.convex_hull
            ch_factor = largest_continuous_polygon.area / ch.area if ch.area > 0 else 0
            # ch_factor = 1

    # --- 4. Cálculo das Métricas ---
    area_continua_original = 0.0
    area_continua_ponderada = 0.0
    if largest_continuous_polygon and not largest_continuous_polygon.is_empty:
        area_continua_original = largest_continuous_polygon.area
        area_continua_ponderada = area_continua_original 
        area_continua_ponderada = area_continua_original * ch_factor

    
    area_total_nao_utilizada = free_space.area
    porcentagem_continua_orig = (area_continua_original / area_total_nao_utilizada) * 100 if area_total_nao_utilizada > 0 else 0.0

    porcentagem_continua = (area_continua_ponderada / area_total_nao_utilizada) * 100 if area_total_nao_utilizada > 0 else 0.0

    # --- 5. Plotagem e Salvamento Condicional ---
    if plot or save :
        fig, ax = plt.subplots(figsize=(10, 10))
        ax.set_title(f'Maior Área Livre Contínua (MCA Ponderado: {porcentagem_continua:.2f}%) e (Original: {porcentagem_continua_orig:.2f}%)', fontsize=10)
        
        x_c, y_c = area_corte_poly.exterior.xy
        ax.plot(x_c, y_c, color='black', label='Área de Corte')

        for poly in polygons_shapely:
            x, y = poly.exterior.xy
            ax.fill(x, y, alpha=0.5, color='gray', ec='black')

        if largest_continuous_polygon and not largest_continuous_polygon.is_empty:
            x_l, y_l = largest_continuous_polygon.exterior.xy
            label_text = (
                f'Área Contínua Original: {area_continua_original:.2f}\n'
                f'Área Ponderada (MCA): {area_continua_ponderada:.2f}'
            )
            ax.fill(x_l, y_l, color='green', alpha=0.6, label=label_text)
        
        ax.set_aspect('equal', adjustable='box')
        ax.legend(fontsize='small')
        plt.grid(True)
        
        if save:
            if ch_factor == 1:
                image_filename = os.path.join(_OUTPUT_DIR, f"{name_image}.png")
                data_filename = os.path.join(_OUTPUT_DIR, f"{name_image}.txt")
            else:
                image_filename = os.path.join(_OUTPUT_DIR, f"{name_image}.png")
                data_filename = os.path.join(_OUTPUT_DIR, f"{name_image}.txt")
            plt.savefig(image_filename, dpi=300, bbox_inches='tight')
            plt.close(fig)

            
            with open(data_filename, "w") as f:
                r = reprlib.Repr()
                r.maxlist = 10000  # Limite para listas grandes
                f.write(f"pecas_posicionadas = {r.repr(pecas_posicionadas)}\n\n")
                f.write(f"area_corte_vertices = {r.repr(area_corte_vertices)}\n")
            
            print(f"Layout e dados salvos em '{image_filename}' e '{data_filename}'")
        elif plot:
            plt.show()

    return area_continua_ponderada, porcentagem_continua, largest_continuous_polygon


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
        
        # Escalando os vértices
        for cor in pol:
            novo_pol.append((int(cor[0] * Escala), int(cor[1] * Escala)))
        
        # Removendo qualquer vértice repetido
        novo_pol = remove_vertices_repetidos(novo_pol)
        
        
        # Gerando pontos intermediários

        nova_lista.append(novo_pol)
    
    return nova_lista
def draw_cutting_area(pieces, area_width, area_height, legenda=None, filename=None):
    """
    Desenha a área de corte e as peças na escala correta, sem flip nem espelhamento.

    pieces: lista de peças (cada peça é lista de tuplas (x, y)), já posicionadas no espaço de corte
    area_width, area_height: dimensões do retângulo da área de corte
    legenda: texto da legenda (string ou lista de strings)
    filename: caminho para salvar a figura (string), opcional
    """
    # cria figura e eixo
    fig, ax = plt.subplots()

    # desenha retângulo da área de corte (contorno apenas)
    ax.add_patch(Rectangle((0, 0), area_width, area_height,
                           edgecolor='black', facecolor='none', linewidth=1.5))

    # desenha cada peça usando suas coordenadas absolutas
    for verts in pieces:
        poly = MPolygon(verts, closed=True,
                        facecolor=(173/255, 216/255, 230/255), edgecolor='black')
        ax.add_patch(poly)

    # configura limites do eixo para mostrar toda a área de corte
    ax.set_xlim(0, area_width)
    ax.set_ylim(0, area_height)
    ax.set_aspect('equal')

    # configura legenda ou título
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
            plt.savefig(filename, dpi=150)
    
def offset_polygon(vertices, offset):
    """
    Cria um novo polígono com offset a partir de um polígono original usando Shapely
    
    Args:
        vertices: Lista de tuplas (x, y) representando os vértices do polígono
        offset: Valor do offset (positivo para expandir, negativo para contrair)
    
    Returns:
        Lista de tuplas (x, y) representando os vértices do novo polígono
    """
    if offset > 0:
        # Cria um polígono Shapely
        poly = Polygon(vertices)
        
        # Verifica se o polígono é válido
        if not poly.is_valid:
            return vertices
        
        # Aplica o buffer (offset)
        # join_style=1 (round) para suavizar cantos
        # mitre_limit controla quanto os cantos podem se estender
        buffered = poly.buffer(offset, join_style=1, mitre_limit=2.0)
        
        # Se o resultado for vazio ou inválido, retorna o original
        if buffered.is_empty or not buffered.is_valid:
            return vertices
        
        # Extrai os vértices do polígono resultante
        if buffered.geom_type == 'Polygon':
            # Pega apenas o exterior do polígono
            new_vertices = list(buffered.exterior.coords)[:-1]  # Remove o último ponto (duplicado)
        else:
            # Se o resultado for um MultiPolygon, pega o maior polígono
            largest = max(buffered.geoms, key=lambda x: x.area)
            new_vertices = list(largest.exterior.coords)[:-1]
        
        return new_vertices
    
    else:
        return vertices


def multiplicar_tudo(d, multiplicador):
    novo_dicionario = {}

    for chave, valor in d.items():
        # Multiplicar a chave
        nova_chave = tuple(
            multiplicar_elemento(e, multiplicador) for e in chave
        )

        # Multiplicar os valores (listas de tuplas)
        novo_valor = [
            tuple(x * multiplicador for x in ponto) for ponto in valor
        ]

        novo_dicionario[nova_chave] = novo_valor

    return novo_dicionario

def ler_poligonos(arquivo, escala=1):
    """Lê polígonos de um arquivo .dat."""
    filepath = os.path.join(_INSTANCES_DIR, arquivo + '.dat')
    with open(filepath, 'r') as f:
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
                            raise ValueError(f"Esperado 2 valores: '{linhas[i].strip()}'")
                        x, y = map(float, coords)
                        vertices.append((x * escala, y * escala))
                        i += 1
                    else:
                        raise ValueError("Arquivo terminou prematuramente.")
                poligonos.append(vertices)
            except ValueError:
                i += 1
        else:
            i += 1
    return poligonos




def multiplicar_elemento(e, multiplicador):
    if isinstance(e, (int, float)):
        return e * multiplicador
    elif isinstance(e, tuple):
        return tuple(multiplicar_elemento(x, multiplicador) for x in e)
    else:
        return e  # se aparecer algo que não seja número/tupla, mantém igual

def projetar_vertices_em_poligono(poligono_principal, lista_poligonos):
    """
    Projeta os vértices de uma lista de polígonos em um polígono principal.
    
    Para cada vértice dos polígonos na lista, cria duas retas:
    - Uma paralela ao eixo X
    - Uma paralela ao eixo Y
    E adiciona ao polígono principal os pontos de interseção dessas retas com o polígono.
    
    Args:
        poligono_principal: Lista de tuplas (x, y) representando os vértices do polígono principal.
        lista_poligonos: Lista de polígonos, onde cada polígono é uma lista de tuplas (x, y).
        
    Returns:
        Lista de tuplas (x, y) representando o polígono principal com as projeções adicionadas.
    """
    import math
    from functools import cmp_to_key
    
    # Verificação de entrada
    if not poligono_principal or len(poligono_principal) < 3:
        return poligono_principal.copy() if poligono_principal else []
    
    # Cria uma cópia do polígono principal para não modificar o original
    poligono_resultado = poligono_principal.copy()
    
    # Coletar todos os vértices dos polígonos da lista
    todos_vertices = []
    for poligono in lista_poligonos:
        if poligono:  # Verificar se o polígono não está vazio
            todos_vertices.extend(poligono)
    
    # Para cada vértice, encontrar as interseções das retas paralelas aos eixos com o polígono principal
    for vertice in todos_vertices:
        x_vertice, y_vertice = vertice
        
        # Encontrar interseções da reta horizontal (paralela ao eixo X) com o polígono principal
        for i in range(len(poligono_principal)):
            p1 = poligono_principal[i]
            p2 = poligono_principal[(i + 1) % len(poligono_principal)]
            
            # Verificar se o segmento cruza a linha horizontal y = y_vertice
            if not ((p1[1] <= y_vertice <= p2[1]) or (p2[1] <= y_vertice <= p1[1])):
                continue
                
            # Se os pontos têm a mesma coordenada y (segmento horizontal)
            if abs(p1[1] - p2[1]) < 1e-10:  # Usar uma pequena tolerância para comparação
                # Se o y do vértice coincide com o y do segmento horizontal
                if abs(p1[1] - y_vertice) < 1e-10:
                    # Adicionar os pontos do segmento horizontal que estão entre xmin e xmax
                    x_min = min(p1[0], p2[0])
                    x_max = max(p1[0], p2[0])
                    if x_min <= x_vertice <= x_max:
                        ponto_intersecao = (x_vertice, y_vertice)
                        if ponto_intersecao not in poligono_resultado:
                            poligono_resultado.append(ponto_intersecao)
            else:
                # Segmento não horizontal - calcular interseção
                t = (y_vertice - p1[1]) / (p2[1] - p1[1])
                if 0 <= t <= 1:  # Verificar se a interseção está dentro do segmento
                    x_intersecao = p1[0] + t * (p2[0] - p1[0])
                    ponto_intersecao = (x_intersecao, y_vertice)
                    if ponto_intersecao not in poligono_resultado:
                        poligono_resultado.append(ponto_intersecao)
        
        # Encontrar interseções da reta vertical (paralela ao eixo Y) com o polígono principal
        for i in range(len(poligono_principal)):
            p1 = poligono_principal[i]
            p2 = poligono_principal[(i + 1) % len(poligono_principal)]
            
            # Verificar se o segmento cruza a linha vertical x = x_vertice
            if not ((p1[0] <= x_vertice <= p2[0]) or (p2[0] <= x_vertice <= p1[0])):
                continue
                
            # Se os pontos têm a mesma coordenada x (segmento vertical)
            if abs(p1[0] - p2[0]) < 1e-10:  # Usar uma pequena tolerância para comparação
                # Se o x do vértice coincide com o x do segmento vertical
                if abs(p1[0] - x_vertice) < 1e-10:
                    # Adicionar os pontos do segmento vertical que estão entre ymin e ymax
                    y_min = min(p1[1], p2[1])
                    y_max = max(p1[1], p2[1])
                    if y_min <= y_vertice <= y_max:
                        ponto_intersecao = (x_vertice, y_vertice)
                        if ponto_intersecao not in poligono_resultado:
                            poligono_resultado.append(ponto_intersecao)
            else:
                # Segmento não vertical - calcular interseção
                t = (x_vertice - p1[0]) / (p2[0] - p1[0])
                if 0 <= t <= 1:  # Verificar se a interseção está dentro do segmento
                    y_intersecao = p1[1] + t * (p2[1] - p1[1])
                    ponto_intersecao = (x_vertice, y_intersecao)
                    if ponto_intersecao not in poligono_resultado:
                        poligono_resultado.append(ponto_intersecao)
    
    # Se temos menos de 3 pontos, não podemos formar um polígono
    if len(poligono_resultado) < 3:
        return poligono_resultado
    
    # Reordenar os pontos no sentido anti-horário
    # Calcular o centroide
    cx = sum(x for x, _ in poligono_resultado) / len(poligono_resultado)
    cy = sum(y for _, y in poligono_resultado) / len(poligono_resultado)
    
    # Função para comparar pontos baseada no ângulo com respeito ao centroide
    def comparar_pontos(p1, p2):
        angulo1 = math.atan2(p1[1] - cy, p1[0] - cx)
        angulo2 = math.atan2(p2[1] - cy, p2[0] - cx)
        return -1 if angulo1 < angulo2 else (1 if angulo1 > angulo2 else 0)
    
    # Reordenar os pontos
    poligono_resultado.sort(key=cmp_to_key(comparar_pontos))
    
    # Remover pontos duplicados ou muito próximos
    i = 0
    while i < len(poligono_resultado):
        j = (i + 1) % len(poligono_resultado)
        p1 = poligono_resultado[i]
        p2 = poligono_resultado[j]
        
        # Verificar se os pontos são muito próximos
        distancia = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
        if distancia < 1e-6:  # Tolerância para pontos próximos
            # Remover o ponto j
            poligono_resultado.pop(j if j < i else i)
        else:
            i += 1
    
    return poligono_resultado

def dimensions(dataset: str): 

    specs = {
        'fu':          (34.0,     38.0,     1, [0,1,2,3]),
        'jackobs1':    (11.5,     40.0,     1, [0,1,2,3]),
        'jackobs2':    (28.2,     70.0,     1, [0,1,2,3]),
        'shapes0':     (65.0,     40.0,     1, [0]),
        'shapes1':     (65.0,     40.0,     1, [0,2]),
        'shapes2':     (27.3,     15.0,     1, [0,2]),
        'dighe1':      (138.14,   100.0,    1, [0]),
        'dighe2':      (134.05,   100.0,    1, [0]),
        'albano':      (10122.63, 4900.0,   1, [0,2]),
        'dagli':       (65.6,     60.0,     1, [0,2]),
        'mao':         (2058.6,   2550.0,   1, [0,1,2,3]),
        'marques':     (83.6,     104.0,    1, [0,1,2,3]),
        'shirts':      (63.13,    40.0,     1, [0,2]),
        'swim':        (6568.0,   5752.0,   1, [0,2]),
        'trousers':    (245.75,   79.0,     1, [0,2]),
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
                    
                    # nfp agora é um objeto Polygon
                    nfp, intersec = NFP(pecaA, grauA, pecaB, grauB, env)
            
                    # --- ALTERAÇÃO PRINCIPAL AQUI ---
                    # Armazenamos o objeto Polygon diretamente.
                    # Como offset_polygon não faz nada, podemos simplesmente atribuir.
                    tabela_nfps[chave] = [list(nfp.exterior.coords),intersec]

    return tabela_nfps
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch
from matplotlib.path import Path
# (mantenha suas outras importações como Polygon, unary_union, etc.)

# --- FUNÇÃO AUXILIAR PARA DESENHAR POLÍGONOS DO SHAPELY ---
def plot_shapely_geometry(ax, geom, facecolor='lightblue', edgecolor='black', alpha=0.5, linewidth=1.0):
    geom = Polygon(geom) if isinstance(geom, list) else geom
    """
    Desenha uma geometria do Shapely (Polygon, MultiPolygon, etc.) em um eixo Matplotlib.
    Esta função sabe como lidar com buracos.
    """
    if geom is None or geom.is_empty:
        return

    # Trata coleções de geometrias (como MultiPolygon)
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
    """
    Executa a lógica da sua função NFP e plota os resultados intermediários,
    incluindo ambas as peças para referência.
    """
    # --- ETAPA 1: Cálculos (idêntico à sua função NFP) ---
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
        return Polygon(), None

    nfp_unido = unary_union(nfps_convx)
    pontos_candidatos = set()
    for subgrupo in intersec_parts:
        for ponto in pontos_pol_A:
            pontos_candidatos.add(Point(ponto))
            
        for ponto in pontos_pol_B:
            pontos_candidatos.add(Point(ponto))
        # 1. Adiciona TODOS os vértices originais de cada NFP parcial no subgrupo
        for nfp in subgrupo:
            for ponto in nfp.exterior.coords:
                pontos_candidatos.add(ponto)
        
        # 2. Adiciona os NOVOS vértices criados na interseção par a par
        if len(subgrupo) > 1:
            for p1, p2 in itertools.combinations(subgrupo, 2):
                intersec = p1.boundary.intersection(p2.boundary)
                if not intersec.is_empty:
                    # Usa sua função extrair_vertices para pegar os pontos da interseção
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
                    # Usa sua função extrair_vertices para pegar os pontos da interseção
                    for ponto in extrair_vertices(intersec):
                        pontos_candidatos.add(ponto)
                
    # # Une todas as geometrias de interseção encontradas
    min_x, min_y, max_x, max_y = nfp_unido.bounds
    padding = 100.0 
    
    # max_x_p = min(v[0] for v in pontos_pol_A)
    # max_y_p = min(v[1] for v in pontos_pol_A)

        # Retorna a lista de vértices transladados
    # print(pontos_pol_A)
    pontos_pol_nor_A = [(x - pontos_pol_B[0][0], y - pontos_pol_B[0][1]) for x, y in pontos_pol_A]
    
    pontos_candidatos = set()
    # print(pontos_pol_nor_A)
    # Itere sobre os vértices da Peça A
    for ponto in pontos_pol_nor_A:
        x_vertice, y_vertice = ponto

        # --- Raio Vertical para Cima ---
        linha_cima = LineString([ponto, (x_vertice, max_y + padding)])
        intersecao_cima = nfp_unido.boundary.intersection(linha_cima)
        pontos_candidatos.update(extrair_vertices(intersecao_cima))

        # --- Raio Vertical para Baixo ---
        linha_baixo = LineString([ponto, (x_vertice, min_y - padding)])
        intersecao_baixo = nfp_unido.boundary.intersection(linha_baixo)
        pontos_candidatos.update(extrair_vertices(intersecao_baixo))

        # --- Raio Horizontal para Direita ---
        linha_direita = LineString([ponto, (max_x + padding, y_vertice)])
        intersecao_direita = nfp_unido.boundary.intersection(linha_direita)
        pontos_candidatos.update(extrair_vertices(intersecao_direita))

        # --- Raio Horizontal para Esquerda ---
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
    # print(nfp_unido)
    nfp_unido = unary_union([nfp_unido, MultiPoint(nfp_f).buffer(0.000000001)])
    coords_externas = [(round(x, 1), round(y, 1)) for x, y in nfp_unido.exterior.coords]
    pontos_unicos_ext = []
    for ponto in coords_externas:
        if not pontos_unicos_ext or ponto != pontos_unicos_ext[-1]:
            pontos_unicos_ext.append(ponto)
            
    nfp_unido = Polygon(pontos_unicos_ext)
    # print(nfp_unido)
    # # print(intersec)
    polyA = Polygon(pontos_pol_A)
    polyB = Polygon(pontos_pol_B)
    
    pontos_de_encontro_validos = []
    for ponto in extrair_vertices(intersec):
    
        # Move a Peça B original (rotacionada) para a posição do ponto candidato
        polyB_na_posicao = affinity.translate(polyB, xoff=ponto[0], yoff=ponto[1])
        
        # O método .overlaps verifica se os interiores se cruzam.
        # .touches seria verdadeiro, .overlaps deve ser falso.
        if not polyA.overlaps(polyB_na_posicao) and polyA.touches(polyB_na_posicao):
            # # Adicionalmente, verificamos se não está muito longe (evita pontos inválidos)
            # if polyA.distance(polyB_na_posicao) < 1e-6:
                pontos_de_encontro_validos.append(ponto)
    intersec = MultiPoint(pontos_de_encontro_validos)

    
    # # --- ETAPA 2: Visualização ---

    # # # --- ETAPA 2: Visualização em Layout 2x2 ---
    # fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(16, 16))
    # fig.suptitle(f"Análise do NFP entre Peça A (rot {grauA}°) e Peça B (rot {grauB}°)", fontsize=16)

    # # Gráfico 1: Decomposição da Peça A
    # ax1.set_title("1. Decomposição Convexa da Peça A (Fixa)")
    # plot_shapely_geometry(ax1, polyA, facecolor='gray', alpha=0.3)
    # for i, part in enumerate(convex_partsA):
    #     plot_shapely_geometry(ax1, part, facecolor=f'C{i}', alpha=0.5)
        
    # # pontos_criticos = nfp_f

    # # # 2. Garante que há pontos para plotar
    # # if pontos_criticos:
    # #     # Separa as coordenadas X e Y para o Matplotlib
    # #     x_vertices = [ponto[0] for ponto in pontos_criticos]
    # #     y_vertices = [ponto[1] for ponto in pontos_criticos]
        
    # #     # 3. Plota os pontos em preto ('k') com marcadores de círculo ('o')
    # #     ax4.plot(x_vertices, y_vertices, 'ro', markersize=7, label='Vértices Críticos', )
    # #     ax1.plot(x_vertices, y_vertices, 'ko', markersize=7, label='Vértices Críticos', )
    
    # # Gráfico 2: Decomposição da Peça B
    # ax2.set_title("2. Decomposição Convexa da Peça B (Rotacional)")
    # plot_shapely_geometry(ax2, polyB, facecolor='gray', alpha=0.3)
    # for i, part in enumerate(convex_partsB):
    #     plot_shapely_geometry(ax2, part, facecolor=f'C{i+len(convex_partsA)}', alpha=0.5)

    # # Gráfico 3: NFPs Parciais
    # ax3.set_title("3. Peça A + NFPs Parciais")
    # plot_shapely_geometry(ax3, polyA, facecolor='gray', alpha=0.9)
    # for nfp_part in nfps_convx:
    #     plot_shapely_geometry(ax3, nfp_part, facecolor='cyan', alpha=0.2, edgecolor='blue')

    # # Gráfico 4: NFP Final Unido
    # ax4.set_title("4. Peça A + NFP Final (União)")
    # plot_shapely_geometry(ax4, polyA, facecolor='gray', alpha=0.9)
    # plot_shapely_geometry(ax4, nfp_unido, facecolor='red', alpha=0.4, edgecolor='red')
    
    # # --- NOVO BLOCO DE CÓDIGO AQUI ---
    # # Plota a geometria de interseção nos gráficos 3 e 4 para destaque
    # if intersec and not intersec.is_empty:
    #     geoms_to_plot = getattr(intersec, 'geoms', [intersec])
    #     for geom in geoms_to_plot:
    #         if isinstance(geom, (Point, MultiPoint)):
    #             # Se for um ponto, plota como um círculo preto grande
    #             ax3.plot(geom.x, geom.y, 'ko', markersize=10, label='Ponto de Interseção Total')
    #             ax4.plot(geom.x, geom.y, 'ko', markersize=10)
    #         elif isinstance(geom, (LineString, MultiLineString)):
    #              # Se for uma linha, plota como uma linha preta grossa
    #             ax3.plot(*geom.xy, color='black', linewidth=3, label='Linha de Interseção Total')
    #             ax4.plot(*geom.xy, color='black', linewidth=3)
    
    # ax3.legend(loc='upper right') # Adiciona a legenda ao gráfico 3
    
    # pontos_criticos = extrair_vertices(nfp_unido)

    # # 2. Garante que há pontos para plotar
    # if pontos_criticos:
    #     # Separa as coordenadas X e Y para o Matplotlib
    #     x_vertices = [ponto[0] for ponto in pontos_criticos]
    #     y_vertices = [ponto[1] for ponto in pontos_criticos]
        
    #     # 3. Plota os pontos em preto ('k') com marcadores de círculo ('o')
    #     ax4.plot(x_vertices, y_vertices, 'ko', markersize=7, label='Vértices Críticos')

    # # --- FIM DO NOVO BLOCO ---
    
    # # Ajusta os limites de todos os eixos
    # try:
    #     all_geoms = [polyA, polyB] + nfps_convx + [nfp_unido]
    #     min_x, min_y, max_x, max_y = unary_union(all_geoms).bounds
    #     padding = 5
    #     for ax in [ax1, ax2, ax3, ax4]:
    #         ax.set_aspect('equal', adjustable='box')
    #         ax.grid(True, linestyle='--', alpha=0.6)
    #         ax.set_xlim(min_x - padding, max_x + padding)
    #         ax.set_ylim(min_y - padding, max_y + padding)
    # except Exception as e:
    #     print(f"Erro ao ajustar eixos do gráfico: {e}")

    # plt.tight_layout(rect=[0, 0, 1, 0.96])
    # plt.show()
    
   
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
    """
    Rotaciona o ponto (x, y) em torno da origem por angle_deg graus (sentido anti-horário).
    Retorna a tupla (x_rot, y_rot).
    """
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
        # Para x=0.1, log10(0.1) = -1, resultando em 1 + 0.1*(-1) = 0.9.
        # Para x=1.0, log10(1.0) = 0, resultando em 1 + 0.1*(0) = 1.0.
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
    def __init__(self,dataset='fu',Base=None,Altura=None,Escala=None, Graus = None, tabela = None, margem = 0, tempo=200, decoder = 'D1', pairwise_IN = False):
        self.decoder_type = decoder
        
        self.save_q_learning_report = True
        self.counter = 0
        self.BRKGA_parameters = {
            'p': [100, 50],          # Tamanho da população
            'pe': [0.20, 0.15],        # Fração da população que compõe a elite
            'pm': [0.05],        # Fração da população de mutantes
            'rhoe': [0.70]       # Probabilidade de herança do alelo do pai de elite
        }
        # Exemplo Online: self.BRKGA_parameters = {'p': [300, 400, 500], 'pe': [0.10, 0.15, 0.20], ...}

        # Parâmetros para Simulated Annealing (SA)
        self.SA_parameters = {
            'SAmax': [10, 5],     # Número de iterações por temperatura
            'alphaSA': [0.9, 0.99],   # Fator de resfriamento
            'betaMin': [0.01, 0.03, 0.05, 0.1],   # Intensidade mínima da perturbação (shaking)
            'betaMax': [0.25, 0.2],   # Intensidade máxima da perturbação (shaking)
            'T0': [1000]      # Temperatura inicial
        }

        # Parâmetros para Iterated Local Search (ILS)
        self.ILS_parameters = {
            'betaMin': [0.10,0.15],   # Intensidade mínima da perturbação (shaking)
            'betaMax': [0.30,0.25]    # Intensidade máxima da perturbação (shaking)
        }
        # Exemplo Online: self.ILS_parameters = {'betaMin': [0.05, 0.10, 0.15], 'betaMax': [0.15, 0.20, 0.25]}

        # Parâmetros para Variable Neighborhood Search (VNS)
        self.VNS_parameters = {
            'kMax': [5,3],         # Número máximo de estruturas de vizinhança
            'betaMin': [0.05, 0.1, 0.15]    # Fator base para a intensidade da perturbação
        }

        # Parâmetros para Particle Swarm Optimization (PSO)
        self.PSO_parameters = {
            'PSize': [100,50],      # Tamanho do enxame (número de partículas)
            'c1': [2.05],        # Coeficiente cognitivo
            'c2': [2.05],        # Coeficiente social
            'w': [0.73]          # Fator de inércia
        }

        # Parâmetros para Genetic Algorithm (GA)
        self.GA_parameters = {
            'sizePop': [100,50],    # Tamanho da população
            'probCros': [0.98],  # Probabilidade de crossover
            'probMut': [0.005, 0.01]   # Probabilidade de mutação
        }

        # Parâmetros para Large Neighborhood Search (LNS)
        self.LNS_parameters = {
            'betaMin': [0.10],   # Intensidade mínima da destruição
            'betaMax': [0.30],   # Intensidade máxima da destruição
            'TO': [100],       # Temperatura inicial
            'alphaLNS': [0.95,0.9]   # Fator de resfriamento
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
            
        # self.base*= 2
        print(f"Base: {self.base}, Altura: {self.altura}, Escala: {self.escala}, Graus: {self.graus}")
        self.area = self.base * self.altura
        self.base_inicial = self.base
        self.inicial = False
        
        
        lista = ler_poligonos(self.dataset)
        
        lista.sort(
                key=lambda coords: Polygon(coords).area,
                reverse=True
            )
  
        # print(lista)
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
        # self.regras = {
        #     0: self.UL,
        #     1: self.BL,
        # }

        

        self.dict_sol = {}

        #     self.regras = {
        #     0: self.BL,
        #     1: self.UL,

        # } 
            
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
                    "EB-1": -805.00,
                    "EB-2": -800.00,
                    "EB-3": -800.00,
                    "EB-4": -800.00,
                    "EB-5": -800.00,
                    "EB-6": -800.00,
                    "EB-7": -800.00,
                    "EB-8": -800.00,
                    "EB-9": -800.00,
                    "EB-10": -800.00,
                    "EB-11": -800.00,
                    "EB-12": -800.00,
                    "EB-13": -800.00,
                    "EB-14": -800.00,
                    "EB-15": -800.00,
                    "EB-16": -800.00,
                    
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
                nfp_file = os.path.join(_NFP_DIR, f"nfp_{self.dataset}_novo2.txt")
                
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
                nfp_file = os.path.join(_NFP_DIR, f"nfp_{self.dataset}_novo2.txt")
                
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
        if self.decoder_type == 'D1_A' or self.decoder_type == 'D2':
            self.tam_solution = 2 * self.max_pecas + 1
        #     self.regras = {
        #     0: self.BL,
        #     1: self.LB,
        #     2: self.BR,
        #     3: self.RB,
        #     4: self.UL,
        #     5: self.LU,
        #     6: self.UR,
        #     7: self.RU,
        #     19: self.OnePass
        # }
                        
            self.regras = {
                # --- Bloco 1: Grupo Inferior-Esquerdo (Bottom-Left) ---
                0: self.BL,
                1: self.LB,
                # 2: self.BL_NFP,
                # 3: self.LB_NFP,

                # --- Bloco 2: Grupo Inferior-Direito (Bottom-Right) ---
                2: self.BR,
                3: self.RB,
                # 6: self.BR_NFP,
                # 7: self.RB_NFP,
                
                # --- Bloco 3: Grupo Superior-Esquerdo (Upper-Left) ---
                4: self.UL,
                5: self.LU,
                # 10: self.UL_NFP,
                # 11: self.LU_NFP,

                # --- Bloco 4: Grupo Superior-Direito (Upper-Right) ---
                6: self.UR,
                7: self.RU,
                # 14: self.UR_NFP,
                # 15: self.RU_NFP,
                
                # --- Bloco 5: Grupo de Centralidade ---
                8: self.NC,      # Centralidade do Bin
                9: self.NCG,     # Centralidade do Layout (Centro de Massa)
                10: self.NCNFP   # Centralidade da Região Factívelva
                # 19: self.OnePass
            }   
        elif self.decoder_type == 'D1_B' or self.decoder_type == 'D2_B':
            self.tam_solution = 3 * self.max_pecas + 1
            self.regras = {
            0: self.BL,
            1: self.LB,
            2: self.BR,
            3: self.RB,
            4: self.UL,
            5: self.LU,
            6: self.UR,
            7: self.RU,
        }
            
        elif self.decoder_type == 'D0_A' or self.decoder_type == 'D0':
            self.tam_solution = 2 * self.max_pecas 
            self.regras = {
            0: self.BL,
            1: self.LB,
            2: self.UL,
            3: self.LU,

        }   
            self.regras = {
            0: self.BL,
            1: self.UL,

        }   
        elif self.decoder_type == 'D0_B':
            self.tam_solution = 3 * self.max_pecas
            self.regras = {
            0: self.BL,
            1: self.LB,
            2: self.UL,
            3: self.LU,

        }   

        # 3. Obtenha a porcentagem correta para o dataset atual (ou 0% como padrão)
        # Em seu script main ou onde você está executando a lógica

        # As duas primeiras linhas estão corretas

        # print(nova_lista)



      
    def plot_pairwise_geometries(self, peca1_poly, peca2_poly, nfp_poly, titulo="", filepath="."):
        """
        Salva uma imagem com as geometrias envolvidas na análise de um par de peças.
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Plota a Peça 1 (fixa, na origem)
        x, y = peca1_poly.exterior.xy
        ax.fill(x, y, alpha=0.6, fc='blue', ec='black', label='Peça 1 (Fixa)')

        # Plota a Peça 2 (posicionada em um vértice do NFP)
        x, y = peca2_poly.exterior.xy
        ax.fill(x, y, alpha=0.6, fc='green', ec='black', label='Peça 2 (Móvel)')

        # Plota o NFP
        if nfp_poly and not nfp_poly.is_empty:
            x, y = nfp_poly.exterior.xy
            ax.plot(x, y, color='red', linestyle='--', linewidth=2, label='NFP')

        ax.set_aspect('equal', adjustable='box')
        ax.legend()
        # Usa apenas a primeira linha do título para o nome do arquivo, removendo caracteres inválidos
        safe_filename = titulo.split('\n')[0].replace(' | ', '_').replace(':', '').replace('.', 'p') + ".png"
        ax.set_title(titulo)
        ax.grid(True, which='both', linestyle='--', linewidth=0.5)
        
        # Garante que o diretório para salvar a imagem exista
        os.makedirs(filepath, exist_ok=True)
        full_path = os.path.join(filepath, safe_filename)
        
        plt.savefig(full_path, bbox_inches='tight')
        plt.close(fig) # Fecha a figura para liberar memória

    def find_dominant_point(self, nfp_poly):
        """
        Encontra o "Dominant Point" de um No-Fit Polygon côncavo.
        O Dp é o vértice do NFP mais distante da borda do seu fecho convexo.

        Args:
            nfp_poly (Polygon): O polígono NFP a ser analisado.

        Returns:
            tuple: As coordenadas (x, y) do ponto dominante, ou None se não for encontrado.
        """
        if nfp_poly is None or nfp_poly.is_empty or not hasattr(nfp_poly, 'exterior'):
            return None

        # O conceito de "Dominant Point" só se aplica a polígonos côncavos.
        ch = nfp_poly.convex_hull
        # Usamos uma pequena tolerância para problemas de ponto flutuante
        if nfp_poly.area >= ch.area - 1e-9:
            return None # Polígono é convexo, não há Dp.

        # As "vacancies" são as áreas de concavidade (diferença entre o fecho e o polígono)
        vacancies = ch.difference(nfp_poly)
        if vacancies.is_empty:
            return None

        # Garante que as vacancies sejam sempre uma lista de polígonos
        if isinstance(vacancies, Polygon):
            vacancies = [vacancies]
        else:
            vacancies = list(vacancies.geoms)

        max_dist = -1
        dominant_point = None

        # Para cada área de concavidade (vacancy)...
        for vacancy in vacancies:
            # A "opponent side" é a borda que a concavidade compartilha com o fecho convexo
            opponent_side = vacancy.boundary.intersection(ch.boundary)
            
            if opponent_side.is_empty or not isinstance(opponent_side, (LineString, Point)):
                continue
                
            # Os pontos a serem testados são os vértices do NFP que formam essa concavidade
            points_to_check_geom = nfp_poly.boundary.intersection(vacancy)
            
            all_coords = []
            if hasattr(points_to_check_geom, 'geoms'):
                for geom in points_to_check_geom.geoms:
                    all_coords.extend(list(geom.coords))
            elif hasattr(points_to_check_geom, 'coords'):
                all_coords = list(points_to_check_geom.coords)
            
            # Encontra o ponto (vértice) com a maior distância até a borda do fecho convexo
            for p_coords in all_coords:
                p = Point(p_coords)
                dist = p.distance(opponent_side)
                if dist > max_dist:
                    max_dist = dist
                    dominant_point = p_coords

        return dominant_point
    def pairwise(self, porcentagem_cluster=0.2):
        """
        Processa todas as combinações de pares, utilizando cache para evitar cálculos
        repetidos de formas. Calcula o ClusterValue para os pontos mais promissores
        e, ao final, salva imagens das N melhores configurações encontradas.
        """

        if porcentagem_cluster == 0:
            return
        avaliacoes = []
        pairwise_cache = {} # Dicionário para cache dos cálculos geométricos

        pecas_a_analisar = range(len(self.lista_original))
        rotacoes_a_analisar = self.graus

        # Calculando o total de combinações de TIPOS de peça para o progresso
        tipos_unicos = []
        for peca in self.lista_original:
            if peca not in tipos_unicos:
                tipos_unicos.append(peca)
        num_tipos = len(tipos_unicos)
        num_pares_tipos = (num_tipos * (num_tipos - 1)) / 2 + num_tipos # Pares (A,B) + Pares (A,A)
        total_steps = int(num_pares_tipos * (len(rotacoes_a_analisar)**2))
        step = 0
        print(f"Iniciando análise de pairwise... Total de combinações de TIPOS de peça/rotações: ~{total_steps}")

        for i in pecas_a_analisar:
            for j in range(i + 1, len(pecas_a_analisar)):
                for grau1_idx in rotacoes_a_analisar:
                    for grau2_idx in rotacoes_a_analisar:
                        
                        # --- Cria uma chave canônica para o cache baseada nas FORMAS ---
                        shape1_coords = tuple(map(tuple, self.lista_original[i]))
                        shape2_coords = tuple(map(tuple, self.lista_original[j]))
                        key_shapes = tuple(sorted((shape1_coords, shape2_coords)))
                        cache_key = (key_shapes[0], grau1_idx, key_shapes[1], grau2_idx)

                        # --- Verifica o cache ---
                        if cache_key in pairwise_cache:
                            cached_result = pairwise_cache[cache_key]
                            if cached_result:
                                avaliacoes.append({**cached_result, 'i': i, 'j': j, 'grau1': grau1_idx, 'grau2': grau2_idx})
                            continue # Pula para a próxima iteração, evitando recalcular

                        # --- Se não está no cache, faz o cálculo completo ---
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
                            
                            # --- VERSÃO 1: Cr1 Granular (Correta segundo a Figura 7 do artigo) ---
                            # chv1 = ch_poly1.difference(poly1)
                            # chv2 = ch_poly2.difference(poly2)
                            # score_p2_em_p1_list = []
                            # if not chv1.is_empty:
                            #     chv1_polys = list(chv1.geoms) if hasattr(chv1, 'geoms') else [chv1]
                            #     for vacancy in chv1_polys:
                            #         if vacancy.area > 1e-9:
                            #             score_p2_em_p1_list.append(poly2.intersection(vacancy).area / vacancy.area)
                            # score_p2_em_p1 = max(score_p2_em_p1_list) if score_p2_em_p1_list else 0
                            # score_p1_em_p2_list = []
                            # if not chv2.is_empty:
                            #     chv2_polys = list(chv2.geoms) if hasattr(chv2, 'geoms') else [chv2]
                            #     for vacancy in chv2_polys:
                            #         if vacancy.area > 1e-9:
                            #             score_p1_em_p2_list.append(poly1.intersection(vacancy).area / vacancy.area)
                            # score_p1_em_p2 = max(score_p1_em_p2_list)  if score_p1_em_p2_list else 0
                            # cr1 = max(score_p1_em_p2, score_p2_em_p1)

                            # --- VERSÃO 2: Cr1 Alternativa (Sua proposta para testes) ---
                            ratio1_alt = ch_poly1.intersection(poly2).area / ch_poly1.area if ch_poly1.area > 1e-9 else 0
                            ratio2_alt = ch_poly2.intersection(poly1).area / ch_poly2.area if ch_poly2.area > 1e-9 else 0
                            cr1 = max(ratio1_alt, ratio2_alt) # Descomente esta linha para usar a versão 2
                            
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

    # print("\nAnálise concluída. Selecionando pares únicos para plotagem...")

        # --- Ordena e Salva as Imagens dos Melhores Resultados SEM REPETIR PEÇAS ---
        if not avaliacoes:
            print("Nenhuma configuração válida foi encontrada.")
            return

        avaliacoes.sort(key=lambda x: x['value'], reverse=True)

        # MUDANÇA 2: Calculamos o número de pares desejado com base na porcentagem
        num_total_pecas = len(self.lista_original)
        num_pares_desejado = int((num_total_pecas * porcentagem_cluster) / 2)

        pares_finais_para_plotar = []
        pecas_ja_agrupadas = set()

        for aval in avaliacoes:
            # MUDANÇA 3: O critério de parada agora usa o número de pares calculado
            if len(pares_finais_para_plotar) >= num_pares_desejado:
                break

            peca1_idx = aval['i']
            peca2_idx = aval['j']

            if peca1_idx not in pecas_ja_agrupadas and peca2_idx not in pecas_ja_agrupadas:
                pares_finais_para_plotar.append(aval)
                pecas_ja_agrupadas.add(peca1_idx)
                pecas_ja_agrupadas.add(peca2_idx)

        # MUDANÇA 4: O print final reflete a nova lógica
        print(f"\n--- Salvando imagens para {len(pares_finais_para_plotar)}/{num_pares_desejado} pares encontrados ({porcentagem_cluster:.0%}) ---")
        

        # print(f"\n--- Salvando as imagens dos Top {len(pares_finais)} Melhores Encaixes ---")
        save_path = os.path.join(_OUTPUT_DIR, f"pairwise_{self.dataset}")
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
        """
        Recebe os pares selecionados pela função 'pairwise' e retorna uma nova
        lista de polígonos, com as peças dos pares substituídas por suas
        respectivas "meta-peças".

        Retorna:
            list: A nova lista de coordenadas de polígonos.
        """
        if not pares_selecionados:
            print("INFO: Nenhum par selecionado. Retornando a lista original.")
            return self.lista_original

        print(f"INFO: Criando nova lista de peças com {len(pares_selecionados)} clusters...")

        pecas_agrupadas_indices = set()
        nova_lista_de_pecas = []

        # --- Passo 1: Criar e adicionar as meta-peças à nova lista ---
        for par in pares_selecionados:
            i, j = par['i'], par['j']
            g1, g2 = par['grau1'], par['grau2']
            ponto_encaixe = par['ponto_encaixe']
            
            pecas_agrupadas_indices.add(i)
            pecas_agrupadas_indices.add(j)

            poly1 = Polygon(self.rot_pol(i, g1))
            poly2_coords = self.rot_pol(j, g2)
            poly2_translated = Polygon([(p[0] + ponto_encaixe[0], p[1] + ponto_encaixe[1]) for p in poly2_coords])
            
            # --- Escolha como a meta-peça será criada ---

            # Opção A (Recomendado e Robusto): Usa unary_union e garante um polígono simples
            uniao = unary_union([poly1, poly2_translated]).buffer(0)
            if hasattr(uniao, 'geoms'):  # Se for um MultiPolygon
                uniao = max(uniao.geoms, key=lambda p: p.area) # Pega apenas o maior componente
            # Pega apenas o contorno externo, ignorando buracos, o que simplifica o polígono
            meta_peca = [(round(x,2), round(y,2)) for x,y in uniao.exterior.coords]
            # print(meta_peca)
            meta_peca_poly = []
            for cor in meta_peca:
                if cor not in meta_peca_poly:
                    meta_peca_poly.append(cor)

            ring = LinearRing(meta_peca_poly)
            if ring.is_ccw:
                coords_ccw = list(ring.coords)
            else:
                # Se a ordem for horária (CW), simplesmente invertemos a lista
                coords_ccw = list(ring.coords)[::-1]

            # 4. Remove o último vértice se ele for uma repetição do primeiro
            #    A biblioteca de decomposição geralmente espera uma lista sem o ponto final repetido.
            if coords_ccw and coords_ccw[0] == coords_ccw[-1]:
                coords_finais_para_lib = coords_ccw[:-1]
            else:
                coords_finais_para_lib = coords_ccw

            meta_peca_poly = coords_finais_para_lib
            # meta_peca_poly 
            print(meta_peca_poly)

            # # Opção B (Experimental): "Costurando" os vértices a partir do ponto de encaixe
            # # AVISO: Risco de gerar polígonos inválidos (auto-interseção). Use com cautela.
            # p1_coords = list(poly1.exterior.coords)
            # p2_coords_translated = list(poly2_translated.exterior.coords)
            # ponto_em_p1 = min(p1_coords, key=lambda p: Point(p).distance(Point(ponto_encaixe)))
            # idx_insercao = p1_coords.index(ponto_em_p1)
            # nova_lista_coords = p1_coords[:idx_insercao + 1] + p2_coords_translated[:-1] + p1_coords[idx_insercao + 1:]
            # meta_peca_poly = Polygon(nova_lista_coords)
            
            nova_lista_de_pecas.append(meta_peca_poly)

        # --- Passo 2: Adicionar as peças que não foram agrupadas ---
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
        # print(pontos)


        px, py = pontos[0]  # pivô
        resultado = []

        for x, y in pontos:
            dx, dy = x - px, y - py
            if grau_indice == 0:      # 0° → sem mudança
                nx, ny = dx, dy
            elif grau_indice == 1:    # +90° → (x, y) → (-y, x)
                nx, ny = -dy, dx
            elif grau_indice == 2:    # 180° → (x, y) → (-x, -y)
                nx, ny = -dx, -dy
            elif grau_indice == 3:    # 270° → (x, y) → (y, -x)
                nx, ny = dy, -dx

            resultado.append([px + nx, py + ny])
        min_x = min(p[0] for p in resultado)
        min_y = min(p[1] for p in resultado)

        if min_x < 0 or min_y < 0:
            resultado = [(x - min_x if min_x < 0 else x,
                        y - min_y if min_y < 0 else y) for x, y in resultado]
        # print(resultado)
        
        return resultado
 
    
    def ifp(self, peca_idx,grau_indice):
        peca = self.rot_pol(peca_idx,grau_indice)
        # print(peca)
        maxx = max([x for x,y in peca])
        maxy = max([y for x,y in peca])

        minx = min([x for x,y in peca])
        miny = min([y for x,y in peca])
    
        if (maxx - minx) > (self.base) or (maxy - miny) > (self.altura):
            return []
        
        cords = self.cordenadas_area
        # print(cords)

        v0 = (0 - minx, 0 - miny)

        # Vértice inferior direito (base, 0)
        v1 = (self.base - maxx, 0 - miny)

        # Vértice superior direito (base, altura)
        v2 = (self.base - maxx, self.altura - maxy)

        # Vértice superior esquerdo (0, altura)
        v3 = (0 - minx, self.altura - maxy)
        
        ifp = [v0,v1,v2,v3]
 
        ifp = Polygon(ifp).buffer(-25)
        
        # print('\n')
        return list(ifp.exterior.coords)
    
    def nfp(self, peca, grau_indice):
        nfps = []
        todos_pontos_de_encontro = []

        # cria chave de prefixo (estado atual das peças posicionadas + peça nova)
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

        # se já calculou esse prefixo antes, retorna direto do cache
        if prefixo_t in self.dict_nfps:
            return self.dict_nfps[prefixo_t]

        
        # caso contrário, calcula normalmente
        for (chave, x2, y2) in chaves[start_nfp:]:
            nfp_salvo = self.tabela_nfps.get(chave)
            if not nfp_salvo:
                continue

            coords_base_nfp = nfp_salvo[0]
            pontos_intersec_base = nfp_salvo[1]

            base_nfp = Polygon(coords_base_nfp)
            if base_nfp.is_empty:
                continue

            # translada o NFP
            p = affinity.translate(base_nfp, xoff=x2, yoff=y2)


            nfps.append(p)

            # translada pontos de interseção
            if pontos_intersec_base:
                pontos_transladados = [(pt[0] + x2, pt[1] + y2) for pt in pontos_intersec_base]
                todos_pontos_de_encontro.append((pontos_transladados, p))

        if not nfps:
            return None, None

        if maior_nfp[1] is not None and maior_nfp[0] is not None:

            todos_pontos_de_encontro.append((list(maior_nfp[1].geoms), maior_nfp[0]))
        # ocupado = unary_union(nfps)
        ocupado = unary_union([maior_nfp[0]] + [nfp.buffer(-0.000001) for nfp in nfps])
        # print(ocupado)
        # self.prepared_nfps = [prep(nfp) for nfp in nfps]
        # self.boundaries = [nfp.boundary for nfp in nfps]
        

        # pontos_validos = []
        # print((pontos_validos))

        pontos_validos = []
        # print('TP', todos_pontos_de_encontro)
        # print('inter', list(maior_nfp[1].geoms))
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

        # salva no cache antes de retornar
        self.dict_nfps[prefixo_t] = (ocupado, intersec_final)

        # print(len(extrair_vertices(ocupado)), len(extrair_vertices(intersec_final)))
        # input()
        return ocupado, []
    
    def feasible(self, peca, grau_indice, area=False):
        chave = tuple([peca, grau_indice, tuple(map(tuple, self.pecas_posicionadas)), self.base, self.altura])

        # 1. Verifica cache do feasible
        if chave in self.dict_feasible:
            cached_result = self.dict_feasible[chave]
            if area:
                return cached_result['vertices'], cached_result['area']
            return cached_result['vertices']

        # 2. Calcula o Inner-Fit Polygon (área permitida dentro do bin)
        ifp_coords = self.ifp(peca, grau_indice)
        if not ifp_coords:
           
            return ([], 0) if area else []

        ifp_polygon = Polygon(ifp_coords)

        # 3. Caso não haja peças já posicionadas → retorno simples
        if not self.pecas_posicionadas:
            vertices = list(ifp_polygon.exterior.coords)
            # self.dict_feasible[chave] = {'vertices': vertices, 'area': ifp_polygon.area}
            if area:
                return vertices, ifp_polygon.area
            
            return vertices

        # 4. Calcula o No-Fit Polygon combinado (já com cache agressivo no nfp)
        nfp_polygon, nfp_intersec = self.nfp(peca, grau_indice)

        # 5. Interseção entre bordas IFP × NFP
        intersec = ifp_polygon.boundary.intersection(nfp_polygon.boundary) if nfp_polygon else None
        pts = []
        if intersec and not intersec.is_empty:
            if intersec.geom_type == 'Point':
                pts = [(intersec.x, intersec.y)]
            else:
                for part in getattr(intersec, 'geoms', [intersec]):
                    if hasattr(part, 'coords'):
                        pts.extend(list(part.coords))

        # 6. Diferença (área factível)
        if nfp_polygon and not nfp_polygon.is_empty:
            encaixes = ifp_polygon.difference(nfp_polygon)
        else:
            encaixes = ifp_polygon

        # 7. Extrai vértices da área
        vertices = extrair_vertices(encaixes)
        vertices.extend(pts)

        # 8. Considera interseções extras vindas do NFP
        # if nfp_intersec:
            
        #     for ponto in extrair_vertices(nfp_intersec):
        #         vertices.append(ponto)
                
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
        # for ponto in vertices:
        #     if ponto not in vertices_validos:
        #         vertices_validos.append(ponto)
        # 9. Salva no cache
        encaixes_area = encaixes.area if encaixes else 0
        self.dict_feasible[chave] = {'vertices': vertices, 'area': encaixes_area}


        # 10. Retorna
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
        """
        Heurística BL que considera APENAS os pontos de NFP, forçando o encaixe.
        Se não houver pontos de NFP, ela recorre (fallback) à regra BL padrão.
        """
        # 1. Obtém todos os pontos factíveis (IFP + NFP) e os pontos do IFP
        ifp_points = self.ifp(peca, grau_indice)  # Assumindo que ifp() retorna os vértices do IFP
        all_positions = self.feasible(peca, grau_indice)
        
        # 2. Filtra a lista para manter apenas os pontos que NÃO vêm do IFP
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
                
        # 3. Lógica de Fallback: Se não houver pontos de NFP, use a lista completa
        #    Isso é crucial para posicionar a primeira peça.
        if not nfp_positions:
            positions_to_use = all_positions
        else:
            positions_to_use = nfp_positions
            
        # 4. Aplica a ordenação BL na lista de posições escolhida
        if not positions_to_use:
            return []  # Retorna falha somente se não houver nenhuma posição factível

        sorted_positions = sorted(positions_to_use, key=lambda ponto: (ponto[0], ponto[1]))      
        bl_position = sorted_positions[0]       
        return bl_position
    
    def LB_NFP(self, peca, grau_indice):
        """Heurística LB que considera APENAS os pontos de NFP, com fallback."""
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        
        positions_to_use = nfp_positions if nfp_positions else all_positions
            
        if not positions_to_use:
            return []

        sorted_positions = sorted(positions_to_use, key=lambda ponto: (ponto[1], ponto[0]))
        return sorted_positions[0]

    def BR_NFP(self, peca, grau_indice):
        """Heurística BR que considera APENAS os pontos de NFP, com fallback."""
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        
        positions_to_use = nfp_positions if nfp_positions else all_positions
            
        if not positions_to_use:
            return []

        sorted_positions = sorted(positions_to_use, key=lambda ponto: (-ponto[0], ponto[1]))
        return sorted_positions[0]

    def RB_NFP(self, peca, grau_indice):
        """Heurística RB que considera APENAS os pontos de NFP, com fallback."""
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        
        positions_to_use = nfp_positions if nfp_positions else all_positions
            
        if not positions_to_use:
            return []

        sorted_positions = sorted(positions_to_use, key=lambda ponto: (ponto[1], -ponto[0]))
        return sorted_positions[0]

    def UL_NFP(self, peca, grau_indice):
        """Heurística UL que considera APENAS os pontos de NFP, com fallback."""
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        
        positions_to_use = nfp_positions if nfp_positions else all_positions
            
        if not positions_to_use:
            return []

        sorted_positions = sorted(positions_to_use, key=lambda ponto: (ponto[0], -ponto[1]))
        return sorted_positions[0]

    def LU_NFP(self, peca, grau_indice):
        """Heurística LU que considera APENAS os pontos de NFP, com fallback."""
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        
        positions_to_use = nfp_positions if nfp_positions else all_positions
            
        if not positions_to_use:
            return []

        sorted_positions = sorted(positions_to_use, key=lambda ponto: (-ponto[1], ponto[0]))
        return sorted_positions[0]

    def UR_NFP(self, peca, grau_indice):
        """Heurística UR que considera APENAS os pontos de NFP, com fallback."""
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        
        positions_to_use = nfp_positions if nfp_positions else all_positions
            
        if not positions_to_use:
            return []

        sorted_positions = sorted(positions_to_use, key=lambda ponto: (-ponto[0], -ponto[1]))
        return sorted_positions[0]

    def RU_NFP(self, peca, grau_indice):
        """Heurística RU que considera APENAS os pontos de NFP, com fallback."""
        ifp_points = self.ifp(peca, grau_indice)
        all_positions = self.feasible(peca, grau_indice)
        nfp_positions = [pos for pos in all_positions if pos not in ifp_points]
        
        positions_to_use = nfp_positions if nfp_positions else all_positions
            
        if not positions_to_use:
            return []

        sorted_positions = sorted(positions_to_use, key=lambda ponto: (-ponto[1], -ponto[0]))
        return sorted_positions[0]

    def NC(self, peca, grau_indice):
        """
        Heurística que seleciona a posição factível mais próxima ao centro
        geométrico do bin.
        """
        positions = self.feasible(peca, grau_indice)
        if not positions:
            return []

        # 1. Define o ponto de âncora: o centro do bin
        centro_bin = (self.base / 2, self.altura / 2)

        # 2. Ordena as posições factíveis pela distância Euclidiana até o centro do bin
        sorted_positions = sorted(positions, 
                                key=lambda ponto: math.dist(ponto, centro_bin))
        
        # 3. Retorna a posição mais próxima
        return sorted_positions[0]
    
    def NCNFP(self, peca, grau_indice):
        """
        Heurística que seleciona a posição factível mais próxima ao centro
        geométrico do bin.
        """
        positions = self.feasible(peca, grau_indice)
        if not positions:
            return []

        # 1. Define o ponto de âncora: o centro do bin
        sum_x = 0
        sum_y = 0
        len_vertices = len(positions)
        for pos in positions:
            sum_x+=pos[0]
            sum_y+=pos[1]

        centro_nfp = (sum_x/len_vertices , sum_y/len_vertices)
        # 2. Ordena as posições factíveis pela distância Euclidiana até o centro do bin
        sorted_positions = sorted(positions, 
                                key=lambda ponto: math.dist(ponto, centro_nfp))
        
        # 3. Retorna a posição mais próxima
        return sorted_positions[0]
    
    def NCG(self, peca, grau_indice):
        """
        Heurística que posiciona a nova peça no ponto factível mais próximo
        ao centro de massa (centroide) das peças já posicionadas.
        """
        positions = self.feasible(peca, grau_indice)
        if not positions:
            return []

        # Caso especial: se for a primeira peça, não há layout.
        # A regra se comporta como a 'Centro_Mais_Proximo' por padrão.
        if not self.pecas_posicionadas:
            centro_bin = (self.base / 2, self.altura / 2)
            sorted_positions = sorted(positions, 
                                    key=lambda ponto: math.dist(ponto, centro_bin))
            return sorted_positions[0]

        # 1. Calcula o centro de massa (média das coordenadas dos centroides) do layout atual
        num_vertices = 0
        soma_x = 0
        soma_y = 0
        centros = []

        for peca in self.pecas_posicionadas:
            # num_vertices+=len(peca)
            soma_x_peca = sum([x for x,y in peca])
            soma_y_peca = sum([y for x,y in peca])
            centros.append((soma_x_peca/len(peca) , soma_y_peca/len(peca)))
        
        soma_x = sum([x for x,y in centros])
        soma_y = sum([y for x,y in centros])
        
        num_vertices = len(self.pecas_posicionadas)
        centro_layout = (soma_x / num_vertices, soma_y / num_vertices)
        
        # 2. Ordena as posições factíveis pela distância do 'ponto' de referência
        #    da nova peça até o centro de massa do layout.
        sorted_positions = sorted(positions, 
                                key=lambda ponto: math.dist(ponto, centro_layout))
        
        # 3. Retorna a posição mais próxima, promovendo o agrupamento.
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
        # self.plot(legenda='[]')

        for peca in self.lista:
            if peca in seen_pecas:
                continue
            seen_pecas.append(peca)
            for grau in self.graus:
                _, area = self.feasible(self.lista.index(peca), grau, True)
                fit = Polygon(peca).area/ area if area > 0 else 0
                # print(medias)
                fits.append(fit)
                # self.remover_ultima_acao()
        
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
                # print(pos)
                self.acao(peca, pos[0], pos[1], grau_indice)
                # base = self.base
                # self.base
                # if time.time() - self.start_time > 50:
                # self.plot(legenda='[]')
                return True
            return False
        
        else:
            pos = self.key_nfp(regra_idx, peca, grau_indice)
            if pos:
                # print(pos)
                self.acao(peca, pos[0], pos[1], grau_indice)
                # self.plot(legenda='[]')
                return True
            return False
        
    def decoder(self, keys):
        
        if self.decoder_type == 'D0':
            # print('1')
            rot = keys[:self.max_pecas]
            pieces = keys[self.max_pecas:]
            
            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
            pieces_idx = np.argsort(pieces)
            
            return list(pieces_idx) + rot_idx
            
        elif self.decoder_type == 'D0_A':
            rot = keys[:self.max_pecas]
            regras = keys[self.max_pecas:]
            
            
            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
            regras_idx = []
            tipos_regras = 2
            for key in regras:
                regras_idx.append(int(key * tipos_regras))
                
            # print(rot_idx + regras_idx)
            return rot_idx + regras_idx 
        elif self.decoder_type == 'D0_B':
            pieces = keys[:self.max_pecas]            
            rot = keys[self.max_pecas:2*self.max_pecas]
            regras = keys[2*self.max_pecas:]
            
            pieces_idx = np.argsort(pieces)
            
            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
            regras_idx = []
            tipos_regras = 4
            for key in regras:
                regras_idx.append(int(key * tipos_regras))
                
            # print(rot_idx + regras_idx)
            return list(pieces_idx) + rot_idx + regras_idx 
            
                
        elif self.decoder_type == 'D1_A':
            rot = keys[:self.max_pecas]
            regras = keys[self.max_pecas:-1]
            shrink_key = keys[-1]
            
            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
            regras_idx = []
            tipos_regras = len(self.regras)
            for key in regras:
                regras_idx.append(int(key * tipos_regras))
                
            
            return rot_idx + regras_idx + [shrink_key]
        
        elif self.decoder_type == 'D1_B':
                       
            pieces = keys[:self.max_pecas]            
            rot = keys[self.max_pecas:2*self.max_pecas]
            regras = keys[2*self.max_pecas:-1]
            shrink_key = keys[-1]
            
            pieces_idx = np.argsort(pieces)

            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
            regras_idx = []
            tipos_regras = 8
            for key in regras:
                regras_idx.append(int(key * tipos_regras))
                
            return pieces_idx + rot_idx + regras_idx + [shrink_key]
          
        elif self.decoder_type == 'D2':
            pecas = keys[:self.max_pecas]
            rot = keys[self.max_pecas:-1]
            shrink_key = keys[-1]
            
            pecas_idx = np.argsort(pecas)
            
            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                

                
            
            return list(pecas_idx) + list(rot_idx) + [shrink_key]
       
        elif self.decoder_type == 'D2_A':
            rot = keys[:self.max_pecas]
            regras = keys[self.max_pecas:-1]
            shrink_key = (keys[-1]/5)+0.8
            
            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
            regras_idx = []
            tipos_regras = 8
            for key in regras:
                regras_idx.append(int(key * tipos_regras))
                
            # print(rot_idx + regras_idx)
            return rot_idx + regras_idx + [shrink_key]
        elif self.decoder_type == 'D2_B':
                       
            pieces = keys[:self.max_pecas]            
            rot = keys[self.max_pecas:2*self.max_pecas]
            regras = keys[2*self.max_pecas:]
            
            pieces_idx = np.argsort(pieces)

            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
            regras_idx = []
            tipos_regras = 8
            for key in regras:
                regras_idx.append(int(key * tipos_regras))
                
            return pieces_idx + rot_idx + regras_idx

            
    
    def cost(self, sol, tag = 0, save  =False):
        if self.decoder_type == 'D0':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                pieces = sol[:self.max_pecas]
                rot = sol[self.max_pecas:]                                
                
                
              
                i = 0
                for idx in pieces:
                    # print(i)
                    self.pack(self.lista.index(self.lista_original[idx]),rot[i], 0)
                    i+=1
                    # self.plot()
                
                
                # if self.lista == []:
                #     self.plot()
                pecas = len(self.pecas_posicionadas) 
                  
                
              
                fit = -1 * self.area_usada()
                # print(self.counter, fit)
                self.dict_sol[tuple(sol)] = fit
                if fit < self.best_fit:
                    self.best_fit = fit
                    # if fit == self.dict_best[self.instance_name]:
                    
                    self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    
                self.reset()
                # self.base = self.base / shrink_factor
                # print(self.base) 
                return fit
        
        
        
        elif self.decoder_type == 'D0_A':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                rot = sol[:self.max_pecas]
                regras = sol[self.max_pecas:]                                
                
                
              
                i = 0
                for peca in self.lista_original:
                    # print(i)
                    self.pack(self.lista.index(peca),rot[i], regras[i])
                    i+=1
                    # self.plot()
                
                
                # if self.lista == []:
                #     self.plot()
                pecas = len(self.pecas_posicionadas) 
                  
                
              
                fit = -1 * self.area_usada()
                # print(self.counter, fit)
                self.dict_sol[tuple(sol)] = fit
                if fit < self.best_fit:
                    self.best_fit = fit
                    # if fit == self.dict_best[self.instance_name]:
                    
                    self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    
                self.reset()
                # self.base = self.base / shrink_factor
                # print(self.base) 
                return fit
            
        elif self.decoder_type == 'D0_B':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                pieces = sol[:self.max_pecas]
                rot = sol[self.max_pecas:2*self.max_pecas]
                regras = sol[self.max_pecas*2:]                              
                
                
              
                i = 0
                for idx in pieces:
                    # print(i)
                    self.pack(self.lista.index(self.lista_original[idx]),rot[i], regras[i])
                    i+=1
                    # self.plot()
                
                
                # if self.lista == []:
                #     self.plot()
                pecas = len(self.pecas_posicionadas) 
                  
                
              
                fit = -1 * self.area_usada()
                # print(self.counter, fit)
                self.dict_sol[tuple(sol)] = fit
                if fit < self.best_fit:
                    self.best_fit = fit
                    # if fit == self.dict_best[self.instance_name]:
                    
                    self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    
                self.reset()
                # self.base = self.base / shrink_factor
                # print(self.base) 
                return fit
      
        
        elif self.decoder_type == 'D1_A':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                rot = sol[:self.max_pecas]
                regras = sol[self.max_pecas:-1]
                shrink_factor = sol[-1]
                

        
                
                i = 0
                nao_posicionadas = []
                for peca in self.lista_original:
                    # print(i)
                    packed = self.pack(self.lista.index(peca),rot[i], regras[i])
                    if not packed:
                        nao_posicionadas.append((peca,i))
                        
                    i+=1
                    # self.plot()
                
                
          
                pecas = len(self.pecas_posicionadas)
                
                
                if len(self.pecas_posicionadas) == self.max_pecas: 
                    self.inicial = True   
                    fit = -1 * self.area_usada(save=save)
                    # print(self.counter, fit)
                    self.dict_sol[tuple(sol)] = fit
                    # if save:
                    #     if fit == self.dict_best[self.instance_name]:
                    #         self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    # if round(fit,1) < round(self.best_fit,1) and fit < 0.98 * self.dict_best[self.instance_name]:
                    
                    #     self.best_fit = fit
                    #     # if fit == self.dict_best[self.instance_name]:
                        
                    #     self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    self.reset()
                    
                    return fit
                else:
                    self.reset()
                    return float('inf')
        elif self.decoder_type == 'D2':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                pieces = sol[:self.max_pecas]
                rot = sol[self.max_pecas:-1]
                shrink_factor = sol[-1]
                
                base_antigo = self.base
                if self.inicial == False and self.base == self.base_inicial:
                    pass
                else:
                    self.base = ((self.base - 0.99*self.base) * shrink_factor) + 0.99*self.base
                # print(base_antigo, self.base, shrink_factor)
                
                i = 0
                nao_posicionadas = []
                          
                for idx in pieces:
                    # print(i)
                    packed = self.pack(self.lista.index(self.lista_original[idx]),rot[i], 19)
                    if not packed:
                        nao_posicionadas.append((self.lista_original[idx],i))
                    i+=1
                
                
                # if self.lista == []:
                #     self.plot()
                pecas = len(self.pecas_posicionadas)
                
                
                if len(self.pecas_posicionadas) == self.max_pecas: 
                    self.inicial = True   
                    fit = -1 * self.area_usada()
                    # print(self.counter, fit)
                    self.dict_sol[tuple(sol)] = fit
                    # if save:
                    #     if fit == self.dict_best[self.instance_name]:
                    #         self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    # if round(fit,1) < round(self.best_fit,1) and fit < 0.98 * self.dict_best[self.instance_name]:
                    
                    #     self.best_fit = fit
                    #     # if fit == self.dict_best[self.instance_name]:
                        
                    #     self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    self.reset()
                    
                    return fit
                else:
                    d = random.randint(0,10000)
                   
                    # print(d,self.base, base_antigo)
                    self.base = base_antigo 
                    # print(d,self.base, base_antigo)
                    
                    
                    for peca,idx in nao_posicionadas:
     
                        self.pack(self.lista.index(peca),rot[idx], 19)
              
                        
                    fit = -1 * self.area_usada()                    
                    
                   
                    # # print(d,self.base, base_antigo)
                        
                    

                        
                    if len(self.pecas_posicionadas) != self.max_pecas:
                        # print(len(self.pecas_posicionadas), self.max_pecas, fit)
                        fit = sum([Polygon(pol).area for pol in self.lista]) * 100 / (self.base * self.altura)
                        self.reset()
                        self.dict_sol[tuple(sol)] = fit
                        
                        return fit
                    
                    # if round(fit,1) < round(self.best_fit,1) and fit < 0.98 * self.dict_best[self.instance_name]:
                    #     self.best_fit = fit
                    #     # if fit == self.dict_best[self.instance_name]:
                        
                    #     self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    
                    if len(self.pecas_posicionadas) != self.max_pecas:
                        print("EROOROROROROR")
                    self.inicial = True
                    self.reset()
                    # self.dict_sol[tuple(sol)] = fit
                    return fit
        
        elif self.decoder_type == 'D2_A':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                rot = sol[:self.max_pecas]
                regras = sol[self.max_pecas:-1]                                
                shrink_factor = sol[-1]
                
                self.base = self.base * shrink_factor
                i = 0
                for peca in self.lista_original:
                    # print(i)
                    self.pack(self.lista.index(peca),rot[i], regras[i])
                    i+=1
                    # self.plot()
                
                
                # if self.lista == []:
                #     self.plot()
                pecas = len(self.pecas_posicionadas) 
                  
                # print(self.base, shrink_factor) 
                if len(self.pecas_posicionadas) == self.max_pecas:    
                    fit = -1 * self.area_usada()
                    # print(self.counter, fit)
                    self.dict_sol[tuple(sol)] = fit
                    if save:
                        if fit == self.dict_best[self.instance_name]:
                            self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
                    self.reset()
                    self.base = self.base / shrink_factor
                    
                    return fit
                else:
                    
                    # fit = sum([Polygon(pol).area for pol in self.lista]) * 100 / (self.base * self.altura)
                    fit = -1 * self.area_usada()
                    self.reset()
                    self.base = self.base / shrink_factor
                    return fit
        
        elif self.decoder_type == 'D2_B':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                pieces = sol[:self.max_pecas]
                rot = sol[self.max_pecas:2*self.max_pecas]
                regras = sol[self.max_pecas*2:]
                
                i = 0
            for idx in pieces:
                # print(i)
                self.pack(self.lista.index(self.lista_original[idx]),rot[i], regras[i])
                i+=1
                    # self.plot()
                
            fit = -1 * self.area_usada()
            # if self.lista == []:
            #     self.plot()
            pecas = len(self.pecas_posicionadas)    
                
            # print(self.counter, fit)
            self.dict_sol[tuple(sol)] = fit
            if save:
                if fit == self.dict_best[self.instance_name]:
                    self.plot(f"{round(self.start_time - time.time(),2)} | {fit} | {len(self.pecas_posicionadas)}/{self.max_pecas}")
            self.reset()
            return fit

                    
            
                
        
            
    def plot(self, legenda):
        output_path = os.path.join(_OUTPUT_DIR, f"{self.instance_name}_{time.time()}.png")
        draw_cutting_area(self.pecas_posicionadas, self.base, self.altura, legenda=legenda, filename=output_path)
    
    def get_used_width(self):
        original_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista_original)
        nao_usado_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista)

        # Subtrai pra obter os usados
        usados_counter = original_counter - nao_usado_counter

        # Reconstrói a lista de polígonos usados
        usados = []
        for pol, count in usados_counter.items():
            usados.extend([list(pol) for _ in range(count)])

        # Soma as áreas
        area_total = sum(Polygon(pol).area for pol in usados)

        # Área total do bin
        coords = []
        for pol in self.pecas_posicionadas:
            for x,y in pol:
                coords.append(x)
        if coords == []:
            return 0
        larg = max(coords) - min(coords)
        area_bin = (larg / self.escala) * (self.altura / self.escala)
        # area_bin = (self.base / self.escala) * (self.altura / self.escala)

        return larg 
    
    def get_efficiency(self):
        original_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista_original)
        nao_usado_counter = Counter(tuple(map(tuple, pol)) for pol in self.lista)

        # Subtrai pra obter os usados
        usados_counter = original_counter - nao_usado_counter

        # Reconstrói a lista de polígonos usados
        usados = []
        for pol, count in usados_counter.items():
            usados.extend([list(pol) for _ in range(count)])

        # Soma as áreas
        area_total = sum(Polygon(pol).area for pol in usados)

        # Área total do bin
        coords = []
        for pol in self.pecas_posicionadas:
            for x,y in pol:
                coords.append(x)
        if coords == []:
            return 0
        larg = max(coords) - min(coords)
        area_bin = (larg / self.escala) * (self.altura / self.escala)
        # area_bin = (self.base / self.escala) * (self.altura / self.escala)

        return round((area_total / area_bin) * 100, 2) 
        
    def area_usada(self, save=False):
        """Calcula área contínua não utilizada (MCCA metric)."""
        area_continua, porcentagem_continua, _ = calcular_area_continua_nao_utilizada(
            self.pecas_posicionadas, 
            self.cordenadas_area, 
            plot=False, 
            buffer_distance=50,
            name_image=f"{self.instance_name}_{time.time()}", 
            save=save
        )
        return -1 * round(porcentagem_continua, 2)


if __name__ == '__main__':
    # ==========================================================================
    # MRCAP-MCCA Test Configuration
    # ==========================================================================
    
    # --- Dataset Selection ---
    # Available: fu, jackobs1, jackobs2, shapes0, shapes1, shapes2, dighe1, 
    #            dighe2, albano, dagli, mao, marques, shirts, swim, trousers
    #            EB-1 to EB-14 (Embraer instances)
    INSTANCES = ["fu", "jackobs1", "jackobs2"]
    # INSTANCES = ["EB-1", "EB-2", "EB-3", "EB-4", "EB-5", "EB-6", "EB-7"]
    
    # --- Decoder Selection ---
    # D0: basic (order + rotation)
    # D1_A: with placement rules
    # D2: with shrink factor
    DECODER = "D1_A"
    
    # --- Solver Parameters ---
    TIME_LIMIT = 60        # seconds per instance
    RESTART_RATIO = 1.0    # restart frequency (0.5 = restart at half time)
    NUM_RUNS = 1           # number of runs per instance
    USE_PAIRWISE = False   # enable pairwise clustering
    
    # --- Output ---
    SAVE_DIR = os.path.join(_OUTPUT_DIR, "results_MCCA")
    os.makedirs(SAVE_DIR, exist_ok=True)
    
    # ==========================================================================
    # Run Tests
    # ==========================================================================
    for instance in INSTANCES:
        print(f"\n{'='*60}")
        print(f"Solving: {instance} | Decoder: {DECODER} | Time: {TIME_LIMIT}s")
        print(f"{'='*60}")
        
        env = SPP2D(
            dataset=instance,
            tempo=TIME_LIMIT * RESTART_RATIO,
            decoder=DECODER,
            pairwise_IN=USE_PAIRWISE
        )
        
        save_file = os.path.join(SAVE_DIR, f"{instance}_{DECODER}.csv")
        solver = RKO(env, print_best=True, save_directory=save_file)
        
        cost, sol, temp = solver.solve(
            TIME_LIMIT,
            brkga=1, ms=1, sa=1, vns=1, ils=1, lns=1, pso=1, ga=1,
            restart=RESTART_RATIO,
            runs=NUM_RUNS
        )
        
        # Save best solution image
        env.cost(env.decoder(sol), save=True)
        print(f"Best cost: {cost}")
