import sys
import os
import sys
import os
import builtins
# Em Python 3, adiciona alias para xrange
builtins.xrange = range
from poly_decomp.poly_decomp import polygonQuickDecomp







import numpy as np
from shapely.geometry import Polygon, MultiPoint
from shapely.ops import unary_union, triangulate
import turtle

# Ajuste o caminho de importação para o módulo CSP_GCG


import math
from shapely.geometry import MultiPoint, Polygon, MultiPolygon
from shapely.ops import triangulate

import numpy as np
from shapely.geometry import MultiPoint, Polygon
import numpy as np
from scipy.spatial import ConvexHull
from shapely.geometry import Polygon, MultiPoint

from shapely.geometry import MultiPoint, Polygon
from scipy.spatial import Delaunay
import numpy as np
import copy

def rotate_point(x, y, angle):
    rad = math.radians(angle)
    x_new = x * math.cos(rad) - y * math.sin(rad)
    y_new = x * math.sin(rad) + y * math.cos(rad)
    return x_new, y_new

def NoFitPolygon(poligono_fixo, poligono_orbital):
    global inter
    polyA = Polygon(poligono_fixo)
    polyB = Polygon(poligono_orbital)

    return interpolar_pontos_poligono(no_fit_polygon(polyA, polyB), 0)

def NFP(PecaA,grauA,PecaB,grauB):
    graus = [0,90,180,270]
    grauA = graus[grauA]
    grauB = graus[grauB]
    pontos_pol_A = [(int(rotate_point(cor[0], cor[1], grauA)[0]), int(rotate_point(cor[0], cor[1], grauA)[1])) for cor in PecaA]
    pontos_pol_B = [(int(rotate_point(cor[0], cor[1], grauB)[0]), int(rotate_point(cor[0], cor[1], grauB)[1])) for cor in PecaB]
    nfps_CB_CA = []
    convex_partsB = triangulate_shapely(pontos_pol_B)
    
    convex_partsA = triangulate_shapely(pontos_pol_A)

    nfps_convx = []
    for CB in convex_partsB:
        for convex in convex_partsA:
            nfps_convx.append(Polygon(NoFitPolygon(convex, CB)))


    nfp_final = list(combinar_poligonos(nfps_convx).exterior.coords)
    #print(nfp_final)

    return nfp_final

def minkowski_sum(polygonA, polygonB, ref_point_B):
    """Calcula a soma de Minkowski entre dois polígonos usando um ponto de referência de B e retorna apenas os pontos da soma."""
    
    sum = []
    sum_conv = []
    for p1 in polygonA.exterior.coords:
        sum_points = []
        for p2 in polygonB.exterior.coords:
            # A soma é ajustada para que p2 seja relativo ao ponto de referência ref_point_B
            sum_points.append((p1[0] + p2[0] - ref_point_B[0], p1[1] + p2[1] - ref_point_B[1]))
            sum_conv.append((p1[0] + p2[0] - ref_point_B[0], p1[1] + p2[1] - ref_point_B[1]))
        sum.append(Polygon(sum_points))
        
    
    # Cria um polígono a partir dos pontos da soma
    #print(len(sum))
    #if polygonB.equals(polygonB.convex_hull) and polygonA.equals(polygonA.convex_hull):
        #print("convexo")
    if True:
        return MultiPoint(sum_conv).convex_hull
        
    else:
        return Polygon(combinar_poligonos(sum))

def no_fit_polygon(polyA, polyB):

    ref_point_B = polyB.exterior.coords[0]  # Usa o primeiro vértice de B como ponto de referência
    
    # Inverte as coordenadas de B para simular a diferença de Minkowski
    polyB_inverted = Polygon([(-x, -y) for x, y in polyB.exterior.coords])
    


    nfp = minkowski_sum(polyA, polyB_inverted, ref_point_B)

    
    # Retorna o contorno do NFP combinado
    return [(x + ref_point_B[0], y + ref_point_B[1]) for x,y in list(nfp.exterior.coords)]
def combinar_poligonos(poligonos):
    """
    Recebe uma lista de polígonos e retorna um único polígono que representa
    a união sem sobreposições dos contornos dos polígonos.
    
    Parâmetros:
    - poligonos: lista de objetos Polygon representando cada polígono.

    Retorna:
    - Um polígono que representa a união dos contornos dos polígonos.
    """
    # Realiza a união geométrica dos polígonos para obter apenas a borda externa
    poligono_combinado = unary_union(poligonos)
   
    
    # Verifica se o resultado é um único polígono ou uma coleção
    if poligono_combinado.geom_type == 'Polygon':
        return poligono_combinado  # Retorna o polígono unido diretamente
    elif poligono_combinado.geom_type == 'MultiPolygon':
        # print("MP")
        vertices = []
        for p in poligono_combinado.geoms:
            for x, y in p.exterior.coords:
                vertices.append((x, y))
        
        return Polygon(vertices)

    else:
        print(poligonos)
        print(poligono_combinado)
        raise ValueError("Erro: a geometria resultante não é um polígono válido.")

from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import triangulate

import numpy as np
from shapely.geometry import Polygon, LineString

from shapely.geometry import Polygon, LineString
import numpy as np

from shapely.geometry import Polygon, LineString

def interpolar_pontos_poligono(vertices, pontos_entre_vertices=0):
    """
    Interpola pontos adicionais ao longo das arestas de um polígono.
    
    Args:
        vertices: Lista de vértices do polígono no formato [[x1,y1], [x2,y2], ...]
        pontos_entre_vertices: Número de pontos a serem adicionados entre cada par de vértices
    
    Returns:
        Lista com todos os pontos (originais + interpolados) que formam o polígono
    """
    def interpolar_pontos(p1, p2, num_pontos):
        """
        Interpola num_pontos entre p1 e p2.
        """
        x1, y1 = p1
        x2, y2 = p2
        pontos = []
        
        # Adiciona o ponto inicial
        pontos.append([float(x1), float(y1)])
        
        # Se não precisa adicionar pontos, retorna só o ponto inicial
        if num_pontos <= 0:
            return pontos
            
        # Adiciona os pontos intermediários
        for i in range(1, num_pontos + 1):
            t = i / (num_pontos + 1)
            x = x1 + t * (x2 - x1)
            y = y1 + t * (y2 - y1)
            pontos.append([float(x), float(y)])
            
        return pontos
    
    # Verifica se o polígono tem vértices suficientes
    if not vertices or len(vertices) < 3:
        return vertices

    pontos_finais = []
    num_vertices = len(vertices)
    
    # Para cada aresta do polígono
    for i in range(num_vertices):
        p1 = vertices[i]
        p2 = vertices[(i + 1) % num_vertices]
        
        # Interpola pontos entre p1 e p2
        pontos_aresta = interpolar_pontos(p1, p2, pontos_entre_vertices)
        pontos_finais.extend(pontos_aresta)
    
    return pontos_finais


def desenhar(cords, x_offset, y_offset,color, fill = False, draw = False):
        if not draw:
            p = turtle.Turtle()
            p.penup()
            if color is not None:
                p.color(color)
            if fill:
                p.begin_fill()
            p.goto(cords[0][0] + x_offset, cords[0][1]  + y_offset)
            p.pendown()
            for x, y in cords:
                p.goto(x  + x_offset, y  + y_offset)
            p.goto(cords[0][0] + x_offset, cords[0][1] + y_offset)
            if fill:
                p.end_fill()
            p.hideturtle()
        elif draw:
            fill = True
            
            p = turtle.Turtle()
            p.penup()
            if color is not None:
                p.color(color)
            if fill:
                p.begin_fill()
            p.goto(cords[0][0] + x_offset, cords[0][1] + y_offset)
            p.pendown()
            for x, y in cords:
                p.goto(x + x_offset, y + y_offset)
            p.goto(cords[0][0]  + x_offset, cords[0][1]  + y_offset)
            if fill:
                p.end_fill()
            p.hideturtle()
            for i in range(200000):
                pass
            p.clear()
            
import math
def ajustar_poligono(poligono):
    # Encontrar o primeiro vértice
    x_min = poligono[0][0]
    y_min = poligono[0][1]
    
    # Transladar todos os vértices para garantir que o primeiro ponto seja (0,0)
    poligono_ajustado = [(x - x_min, y - y_min) for (x, y) in poligono]
    
    return poligono_ajustado


from shapely.geometry import Polygon
from shapely.ops import triangulate
from shapely.validation import explain_validity

from shapely.geometry import Polygon
from shapely.ops import triangulate

def can_merge_polygons(poly1, poly2):
    """
    Verifica se dois polígonos podem ser mesclados em um polígono convexo.
    """
    # Tenta mesclar os dois polígonos
    merged = poly1.union(poly2)
    # Verifica se o resultado é convexo
    return merged.equals(merged.convex_hull)

from shapely.geometry import Polygon
import triangle as tr
import numpy as np

def triangulate_shapely(points):
    """
    Decompõe um polígono possivelmente côncavo em partes convexas usando a biblioteca poly_decomp.

    Parâmetros:
    points (list of tuples): Lista de coordenadas (x, y) dos vértices do polígono, em ordem.

    Retorna:
    list of list of tuples: Cada sublista representa um polígono convexo, como lista de tuplas (x, y).
    """
    # Converte tuplas em listas (formato exigido pela poly_decomp)
    points_list = [list(p) for p in points]

    # Executa a decomposição convexa
    convex_parts = polygonQuickDecomp(points_list)

    # Converte cada parte de volta em tuplas para consistência
    result = []
    for part in convex_parts:
        convex_poly = [tuple(pt) for pt in part]
        result.append(convex_poly)

    return result
import random
from shapely.geometry import Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely.geometry import Polygon, LineString, MultiPolygon
from shapely.ops import unary_union, linemerge
def ponto_dentro_poligono(x, y, poligono):
    n = len(poligono)
    dentro = False

    p1x, p1y = poligono[0]
    for i in range(n+1):
        p2x, p2y = poligono[i % n]
        if y > min(p1y, p2y):
            if y <= max(p1y, p2y):
                if x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y-p1y)*(p2x-p1x)/(p2y-p1y)+p1x
                    if p1x == p2x or x <= xints:
                        dentro = not dentro
        p1x, p1y = p2x, p2y

    return dentro
def concat(nfps):
    vertices = []
    for nfp in nfps:
        for x,y in nfp.exterior.coords:
            ponto_invalido = False
            for nfp_p in nfps:
            
                if ponto_dentro_poligono(x,y,nfp_p.exterior.coords, False):
                    ponto_invalido = True
        
            if not ponto_invalido:
                vertices.append((x,y))

    return Polygon(vertices)


def concatenate_nfps(nfps):
    """
    Concatena uma lista de NFPs preservando linhas compartilhadas adjacentes.
    
    Args:
        nfps (list): Lista de NFPs como objetos Polygon do Shapely.
        
    Returns:
        MultiPolygon: União dos NFPs com linhas adjacentes preservadas.
    """
    # Combine todos os NFPs em uma única geometria
    combined = unary_union(nfps)
    
    # Verificar se a união gerou múltiplos polígonos
    if isinstance(combined, MultiPolygon):
        # Lista para armazenar polígonos válidos
        result_polys = []
        
        for poly in combined.geoms:
            # Comparar este polígono com os outros
            for other in combined.geoms:
                if poly != other:
                    # Verificar se compartilham linha (adjacência)
                    shared_edges = poly.intersection(other)
                    if isinstance(shared_edges, LineString):
                        # Adiciona a linha compartilhada de volta ao polígono original
                        merged = linemerge([poly, shared_edges])
                        result_polys.append(Polygon(merged))
                    elif not poly.overlaps(other):  # Permitir apenas adjacência
                        result_polys.append(poly)
                        break
        # Retornar a união dos polígonos ajustados
        return unary_union(result_polys)
    
    # Caso a união seja um único polígono
    return combined


from shapely.geometry import Polygon

def combine_polygons_by_intersection(polygons):
    """
    Combina uma lista de polígonos usando a interseção, retornando o polígono resultante
    da interseção de todos os polígonos da lista.

    Args:
        polygons (list): Lista de objetos Polygon para calcular a interseção.

    Returns:
        Polygon: O polígono resultante da interseção de todos os polígonos fornecidos.
    """
    if not polygons:
        return None  # Retorna None se a lista de polígonos estiver vazia
    
    # Começa com o primeiro polígono
    result = polygons[0]
    
    # Realiza a interseção com os demais polígonos
    for polygon in polygons[1:]:
        result = result.intersection(polygon)
        if result.is_empty:
            return None  # Se a interseção for vazia, não há resultado válido
    
    return result

def nofitp(PolA,PolB):        
    convex_parts_A = triangulate_shapely(PolA)
    convex_parts_B = triangulate_shapely(PolB)
    nfps = []
    nfps2 = []
    for conv in convex_parts_B:
        i = 0
        for nfp in convex_parts_A:
            #desenhar(nfp,0,0,random.sample(cores,1),True)



            nfps.append(Polygon(no_fit_polygon(Polygon(nfp), Polygon(conv))))
            pontos = concat(nfps).exterior.coords
            #desenhar(pontos, 0,0,'green')
            #for x1, y1 in pontos:
                #desenhar(conv, x1, y1, "green", draw=True)
        i = 1
        nfps2.append(Polygon(pontos))
        nfps = []

    nfp3_final = interpolar_pontos_poligono(list(concat(nfps2).exterior.coords),0)
    return nfp3_final

from math import atan2
from math import atan2

def remove_and_sort_vertices(pontosR):
    print(pontosR)
    pontos = []
    for ponto in pontosR:
        if ponto not in pontos:
            pontos.append(ponto)

    print(pontos)
    """
    Ordena uma lista de pontos cartesianos (x,y) que formam um polígono,
    mantendo pontos com x ou y iguais adjacentes.
    
    Args:
        pontos: Lista de tuplas (x,y) representando os vértices do polígono
        
    Returns:
        Lista ordenada de pontos mantendo a estrutura do polígono
    """
    if len(pontos) <= 3:
        return pontos
        
    # Encontra o centroide do polígono
    cx = sum(x for x, _ in pontos) / len(pontos)
    cy = sum(y for _, y in pontos) / len(pontos)
    
    # Função para calcular o ângulo entre um ponto e o eixo x
    def calcular_angulo(ponto):
        x, y = ponto
        dx = x - cx
        dy = y - cy
        angulo = math.atan2(dy, dx)
        return angulo if angulo >= 0 else angulo + 2*math.pi
    
    # Ordena os pontos por ângulo
    pontos_ordenados = sorted(pontos, key=calcular_angulo)
    
    # Reorganiza pontos com coordenadas iguais para ficarem adjacentes
    i = 0
    while i < len(pontos_ordenados)-1:
        j = i + 1
        while j < len(pontos_ordenados):
            x1, y1 = pontos_ordenados[i]
            x2, y2 = pontos_ordenados[j]
            
            # Se encontrar ponto com x ou y igual, move para ficar adjacente
            if x1 == x2 or y1 == y2:
                if j != i + 1:
                    ponto = pontos_ordenados.pop(j)
                    pontos_ordenados.insert(i + 1, ponto)
                i += 1
                j = i + 1
            else:
                j += 1
        i += 1
    
    return pontos_ordenados

import math

def offset_polygon(vertices, offset):
    """
    Cria um novo polígono com offset a partir de um polígono original
    
    Args:
        vertices: Lista de tuplas (x, y) representando os vértices do polígono
        offset: Valor do offset (positivo para expandir, negativo para contrair)
    
    Returns:
        Lista de tuplas (x, y) representando os vértices do novo polígono
    """
    
    def get_normal(p1, p2):
        # Calcula o vetor normal normalizado de uma aresta
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        length = math.sqrt(dx*dx + dy*dy)
        if length == 0:
            return (0, 0)
        # Normal à esquerda (-dy, dx)
        return (-dy/length, dx/length)
    
    def add_vectors(v1, v2):
        # Soma dois vetores
        return (v1[0] + v2[0], v1[1] + v2[1])
    
    def scale_vector(v, scale):
        # Multiplica um vetor por um escalar
        return (v[0] * scale, v[1] * scale)
    
    n = len(vertices)
    if n < 3:
        return vertices
    
    # Lista para armazenar os novos vértices
    new_vertices = []
    
    for i in range(n):
        # Pega o vértice atual e os vértices adjacentes
        prev = vertices[(i-1) % n]
        curr = vertices[i]
        next = vertices[(i+1) % n]
        
        # Calcula as normais das arestas adjacentes
        n1 = get_normal(prev, curr)
        n2 = get_normal(curr, next)
        
        # Calcula a média das normais
        avg_normal = (
            (n1[0] + n2[0]) / 2,
            (n1[1] + n2[1]) / 2
        )
        
        # Normaliza o vetor médio
        length = math.sqrt(avg_normal[0]**2 + avg_normal[1]**2)
        if length > 0:
            avg_normal = (avg_normal[0]/length, avg_normal[1]/length)
            
        # Aplica o offset
        new_vertex = (
            curr[0] + avg_normal[0] * offset,
            curr[1] + avg_normal[1] * offset
        )
        
        new_vertices.append(new_vertex)
    
    return new_vertices






