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
from botao import Botao
from nfp_teste import combinar_poligonos, triangulate_shapely,NoFitPolygon, interpolar_pontos_poligono
import shapely
from shapely import Polygon, MultiPolygon, unary_union, LineString, MultiLineString, MultiPoint, LinearRing, GeometryCollection, Point

from scipy.spatial import ConvexHull
import numpy as np
import cv2
import copy
import pyautogui
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPolygon, Rectangle
import random
import math
from typing import List, Tuple, Union
import sys
sys.path.append(os.path.abspath("c:\\Users\\felip\\Documents\\GitHub\\RKO\\Python"))

from RKO_v3 import RKO


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

def extrair_vertices(encaixes):
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
    with open( 'C:\\Users\\felip\\Documents\\GitHub\\RKO\\Python\\Problems\\2DIKP\\' + arquivo + '.dat', 'r') as f:
        conteudo = f.read().strip()

    # Divide o conteúdo em linhas
    linhas = conteudo.split('\n')

    # Lê o número total de polígonos
    num_poligonos = int(linhas[0].strip())
    #print(f"Número total de polígonos: {num_poligonos}")

    poligonos = []
    i = 1  # Começa a leitura a partir da segunda linha

    while i < len(linhas):
        # Verifica se a linha não está vazia
        if linhas[i].strip():
            try:
                # Lê o número de vértices
                num_vertices = int(linhas[i].strip())
                #print(f"Lendo polígono com {num_vertices} vértices")  # Depuração
                i += 1

                # Lê os vértices
                vertices = []
                for _ in range(num_vertices):
                    # Verifica se a linha não está vazia
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
        #print(f'Todos os {num_poligonos} poligonos foram lidos com sucesso!')
    return poligonos

def pre_processar_NFP(rotacoes, lista_pecas,offset,env):
    tabela_nfps = {}
    lista_unica = []
    for peca in lista_pecas:
        if peca not in lista_unica:
            lista_unica.append(peca)
    
    # Calcula o total de iterações
    total = len(lista_unica) * len(rotacoes) * len(lista_unica) * len(rotacoes)
    atual = 0


    
    for pecaA in lista_unica:
        for grauA in rotacoes:
            for pecaB in lista_unica:
                for grauB in rotacoes:
                    # Atualiza e mostra o progresso
                    atual += 1
                    porcentagem = (atual / total) * 100
                    print(f"\rPré-processando NFPs: {porcentagem:.1f}% concluído", end="")
                    
                   
                    chave = (tuple(pecaA), grauA, tuple(pecaB), grauB)
                    nfp = NFP(pecaA, grauA, pecaB, grauB,env)
                 
                    tabela_nfps[chave] = offset_polygon(nfp,offset)


    
   
    return tabela_nfps


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
        'fu':          (30.841,     38.0,     1, [0,1,2,3]),
        'jackobs1':    (11.000,   40.0,     1, [0,1,2,3]),
        'jackobs2':    (21.996,   70.0,     1, [0,1,2,3]),
        'shapes0':     (58.002,   40.0,     1, [0]),
        'shapes1':     (51.969,   40.0,     1, [0,2]),
        'shapes2':     (25.457,   15.0,     1, [0,2]),
        'dighe1':      (100.023,  100.0,    1, [0]),
        'dighe2':      (100.003,  100.0,    1, [0]),
        'albano':      (9724.490, 4900.0,   1, [0,2]),
        'dagli':       (56.658,   60.0,     1, [0,2]),
        'mao':         (1725.490, 2550.0,   1, [0,1,2,3]),
        'marques':     (76.369,   104.0,    1, [0,1,2,3]),
        'shirts':      (60.676,   40.0,     1, [0,2]),
        'swim':        (5823.905, 5752.0,   1, [0,2]),
        'trousers':    (239.241,  79.0,     1, [0,2]),
    }

    return specs.get(dataset, (None, None, None, None))

def NFP(PecaA,grauA,PecaB,grauB,env):
    graus = [0,90,180,270]
  
    pontos_pol_A = env.rot_pol(env.lista.index(PecaA),grauA)
    pontos_pol_B = env.rot_pol(env.lista.index(PecaB),grauB)
    nfps_CB_CA = []

    if Polygon(pontos_pol_B).equals(Polygon(pontos_pol_B).convex_hull):
        convex_partsB = [pontos_pol_B] 
    else:
        convex_partsB = triangulate_shapely(pontos_pol_B)
    
    if Polygon(pontos_pol_A).equals(Polygon(pontos_pol_A).convex_hull):
        convex_partsA = [pontos_pol_A]
    else:
        convex_partsA = triangulate_shapely(pontos_pol_A)

    nfps_convx = []
    for CB in convex_partsB:
        for convex in convex_partsA:
            nfps_convx.append(Polygon(NoFitPolygon(convex, CB)))


    nfp = unary_union(nfps_convx)
    nfp_final = extrair_vertices(nfp)
    #print(nfp_final)

    return nfp_final


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


class Knapsack2D():
    def __init__(self,dataset='fu',Base=None,Altura=None,Escala=None, Graus = None, tabela = None, margem = 0, tempo=200, decoder = 'D1'):
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
            'alphaSA': [0.5, 0.7],   # Fator de resfriamento
            'betaMin': [0.01, 0.03],   # Intensidade mínima da perturbação (shaking)
            'betaMax': [0.05, 0.1],   # Intensidade máxima da perturbação (shaking)
            'T0': [10]      # Temperatura inicial
        }

        # Parâmetros para Iterated Local Search (ILS)
        self.ILS_parameters = {
            'betaMin': [0.10,0.5],   # Intensidade mínima da perturbação (shaking)
            'betaMax': [0.20,0.15]    # Intensidade máxima da perturbação (shaking)
        }
        # Exemplo Online: self.ILS_parameters = {'betaMin': [0.05, 0.10, 0.15], 'betaMax': [0.15, 0.20, 0.25]}

        # Parâmetros para Variable Neighborhood Search (VNS)
        self.VNS_parameters = {
            'kMax': [5,3],         # Número máximo de estruturas de vizinhança
            'betaMin': [0.05, 0.1]    # Fator base para a intensidade da perturbação
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
        if Base == None and Altura == None and Escala == None:
            self.base, self.altura, self.escala, self.graus = dimensions(dataset)
        else:
            self.base = Base
            self.altura = Altura
            self.escala = Escala
            self.graus = Graus
            
        self.area = self.base * self.altura
        
        lista = ler_poligonos(self.dataset)
        lista.sort(
                key=lambda coords: Polygon(coords).area,
                reverse=True
            )
  
        
        self.lista_original = lista
        
        
        self.lista = copy.deepcopy(self.lista_original)
        self.max_pecas = len(self.lista_original)
        


            
        if tabela is not None:
            self.tabela_nfps = tabela
        elif os.path.exists(f"nfp_{self.dataset}.txt"):
            with open(f"nfp_{self.dataset}.txt", "r") as f:
                conteudo = f.read()
            self.tabela_nfps = ast.literal_eval(conteudo)
            
        else:
            self.tabela_nfps = pre_processar_NFP(self.graus, self.lista, margem, self)
            with open(f"nfp_{self.dataset}.txt", "w") as f:
                f.write(repr(self.tabela_nfps))
            
            
      
            
        self.cordenadas_area = ( [0,0] , [self.base,0] , [self.base,self.altura] , [0,self.altura] )
        
        self.pecas_posicionadas = []
        self.indices_pecas_posicionadas = []
        self.dict_nfps = {}
        
        # self.regras = {
        #     0: self.LU,
        #     1: self.LB,
        # }
        
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
        self.dict_sol = {}
        if self.decoder_type == 'D1_A' or self.decoder_type == 'D2_A':
            self.tam_solution = 2 * self.max_pecas
        elif self.decoder_type == 'D1_B' or self.decoder_type == 'D2_B':
            self.tam_solution = 3 * self.max_pecas
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
                    "trousers": -91.00
                }
        
        
    
        self.dict_feasible = {}
        






    
        
    def acao(self,peca,x,y,grau_idx):
        peca_posicionar = self.rot_pol(peca, grau_idx)

  
        pontos_posicionar = [(x + cor[0], y + cor[1]) for cor in peca_posicionar]
        
        self.pecas_posicionadas.append(pontos_posicionar)
        
        self.indices_pecas_posicionadas.append([x,y,grau_idx,self.lista_original.index(self.lista[peca])])
        
        self.lista.pop(peca)
        

        
    def reset(self):
        self.lista = copy.deepcopy(self.lista_original)
        self.pecas_posicionadas = []
        self.indices_pecas_posicionadas = []
    
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

        v0 = (cords[0][0]- minx , cords[0][1] - miny)
        v1 = (cords[1][0]- maxx , cords[1][1] - miny)
        v2 = (cords[2][0]- maxx , cords[2][1] - maxy)
        v3 = (cords[3][0]- minx , cords[3][1] - maxy)
        
        ifp = [v0,v1,v2,v3]
        # print(ifp)
        # print('\n')
        return ifp
    
    def nfp(self, peca, grau_indice):
        ocupado = None
        chaves = []
        nfps = []   

        for x2, y2, grau1, pol in self.indices_pecas_posicionadas:
            chave = (
                tuple(self.lista_original[pol]), grau1,
                tuple(self.lista[peca]), grau_indice
            )
            
            chaves.append((chave,x2,y2))
            prefixo_t = tuple(chaves)

            if prefixo_t in self.dict_nfps:
                ocupado = self.dict_nfps[prefixo_t]
            else:
            
                base_nfp = self.tabela_nfps[chave]
                p = Polygon([(x + x2, y + y2) for x, y in base_nfp])
                nfps.append(p)
                
                if ocupado is None:
                    ocupado = p                    
                else:
                    ocupado = unary_union([ocupado,p])    

                self.dict_nfps[prefixo_t] = ocupado
        return ocupado    
    
    def feasible(self, peca, grau_indice, area=False):
        
        chave = tuple([peca, grau_indice, tuple([tuple(peca) for peca in self.pecas_posicionadas])])
        # print(chave)
        
        if chave in self.dict_feasible:
            # self.plot(chave)
            return self.dict_feasible[chave]
        else:
            ifp_coords = self.ifp(peca,grau_indice)
            if not ifp_coords:
                return []
            
            if len(self.pecas_posicionadas) == 0:
                return ifp_coords
            
            nfp_coords = self.nfp(peca, grau_indice)
            
            intersec = Polygon(ifp_coords).boundary.intersection(nfp_coords.boundary)
            pts = []
            if intersec.geom_type == 'Point':
                pts = [(intersec.x, intersec.y)]
            else:
                for part in getattr(intersec, 'geoms', [intersec]):
                    if hasattr(part, 'coords'):
                        for x, y in part.coords:
                            pts.append((x, y))
        
            encaixes = Polygon(ifp_coords).difference(nfp_coords)
        
            vertices = extrair_vertices(encaixes)
            for cor in pts:
                vertices.append(cor)

            self.dict_feasible[chave] = vertices
            if area:
                return vertices, encaixes.area
            else:
                return vertices   
        
        
    def BL(self, peca, grau_indice):
        positions = self.feasible(peca,grau_indice)
        if not positions:
            return []      
        positions_bl = sorted(positions, key=lambda ponto: (ponto[0], ponto[1]))        
        bl = positions_bl[0]        
        return bl
        
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
                # self.plot()
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
                
        if self.decoder_type == 'D1_A':
            rot = keys[:self.max_pecas]
            nfp_key = keys[self.max_pecas:]
            
            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
  
                
           
            return rot_idx + list(nfp_key)
          
        elif self.decoder_type == 'D1_B':
            pieces = keys[:self.max_pecas]            
            rot = keys[self.max_pecas:2*self.max_pecas]
            nfp_key = keys[2*self.max_pecas:]
            
            pieces_idx = np.argsort(pieces)

            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
     
                
            return list(pieces_idx) + rot_idx + list(nfp_key)
       
        elif self.decoder_type == 'D2_A':
            rot = keys[:self.max_pecas]
            regras = keys[self.max_pecas:]
            
            rot_idx = []
            tipos_rot = len(self.graus)
            for key in rot:
                rot_idx.append(self.graus[int(key * tipos_rot)])
                
            regras_idx = []
            tipos_regras = 8
            for key in regras:
                regras_idx.append(int(key * tipos_regras))
                
            # print(rot_idx + regras_idx)
            return rot_idx + regras_idx
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

            

    def cost(self, sol, tag = 0, save  =True):
        
        if self.decoder_type == 'D1_A':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                rot = sol[:self.max_pecas]
                nfp_key = sol[self.max_pecas:]
                
                i = 0
                for peca in self.lista_original:
                    # print(i)
                    self.pack(self.lista.index(peca),rot[i], nfp_key[i], regra=False)
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
        elif self.decoder_type == 'D1_B':
            if tuple(sol) in self.dict_sol:
                return self.dict_sol[tuple(sol)]
            else:
                pieces = sol[:self.max_pecas]
                rot = sol[self.max_pecas:2*self.max_pecas]
                nfp_key = sol[self.max_pecas*2:]
              
                
                i = 0
            for idx in pieces:
                # print(i)
                self.pack(self.lista.index(self.lista_original[idx]),rot[i], nfp_key[i], regra=False)
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
        
        elif self.decoder_type == 'D2_A':
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
        draw_cutting_area(self.pecas_posicionadas, self.base, self.altura,legenda=legenda, filename=f'C:\\Users\\felip\\Documents\\GitHub\\RKO\\Python\\Images\\KP\\{self.instance_name}\\{self.instance_name}_{time.time()}.png')
    
        
    def area_usada(self):
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
        
        larg = max(coords) - min(coords)
        # area_bin = (larg / self.Escala) * (self.altura / self.Escala)
        area_bin = (self.base / self.escala) * (self.altura / self.escala)

        return round((area_total / area_bin) * 100, 2) 

# while True:
#     env = Knapsack2D(dataset='shapes1')
    
#     keys = np.random.random(2 * env.max_pecas)
#     sol = env.decoder(keys)
#     env.cost(sol)
#     # print(env.pecas_posicionadas)
#     print(env.area_usada())   
        
    
    
#     env.plot()

if __name__ == '__main__':
    instancias = ["fu","jackobs1","jackobs2","shapes0","shapes1","shapes2","albano","shirts","trousers","dighe1","dighe2","dagli","mao","marques","swim"]    
    decoders = ['D2_A','D1_A', 'D1_B',  'D2_B']
    for tempo in [1200]:    
        for restart in [1]:
            for decoder in decoders:    
                for ins in instancias:
                    list_time = []
                    list_cost = []
                    
                    env = Knapsack2D(dataset=ins, tempo=tempo * restart, decoder=decoder)
                    print(len(env.lista), sum(Polygon(pol).area for pol in env.lista)/env.area)
                    solver = RKO(env, print_best=True, save_directory=f'c:\\Users\\felip\\Documents\\GitHub\\RKO\\Python\\testes_kp_SPP\\{decoder}_KP_SPP\\testes_RKO.csv')
                    cost,sol, temp = solver.solve(tempo,brkga=1,ms=1,sa=1,vns=1,ils=1, lns=1, pso=1, ga=1, restart= restart,  runs=1)

