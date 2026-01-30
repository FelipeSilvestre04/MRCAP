import sys
import os
from shapely.geometry import Polygon

# Adiciona o caminho para importar Knapsack2D e outros módulos
sys.path.append(os.path.join(os.getcwd(), 'Python', 'Problems', '2DIKP'))
sys.path.append(os.path.join(os.getcwd(), 'Python')) 

# Mock poly_decomp since we only need dimensions
import types
module = types.ModuleType('poly_decomp')
module.polygonQuickDecomp = lambda x: x
sys.modules['poly_decomp'] = module
sys.modules['poly_decomp.poly_decomp'] = module

from Knapsack2D import dimensions

def ler_poligonos(filepath):
    poligonos = []
    try:
        with open(filepath, 'r') as f:
            content = f.read().strip().split('\n')
            lines = [l.strip() for l in content if l.strip()]
        
        if not lines:
            return []

        num_polys = int(lines[0])
        idx = 1
        while idx < len(lines):
            try:
                num_vertices = int(lines[idx])
                idx += 1
                vertices = []
                for _ in range(num_vertices):
                    coords = list(map(float, lines[idx].split()))
                    vertices.append((coords[0], coords[1]))
                    idx += 1
                poligonos.append(Polygon(vertices))
            except (ValueError, IndexError):
                idx += 1
    except Exception as e:
        print(f"Erro ao ler arquivo {filepath}: {e}")
    return poligonos

import csv
from collections import Counter

def validar_instancia(nome_instancia):
    # 1. Tentar obter dimensões do bin para Knapsack (hard_kp)
    w_bin, h_bin, _, rotations = dimensions(nome_instancia, mode='hard_kp')
    
    # 2. Localizar o arquivo .dat (pode estar em 2DISPP ou 2DIKP)
    base_path = os.getcwd()
    paths_to_check = [
        os.path.join(base_path, 'Python', 'Problems', '2DISPP', f'{nome_instancia}.dat'),
        os.path.join(base_path, 'Python', 'Problems', '2DIKP', f'{nome_instancia}.dat')
    ]
    
    filepath = None
    for p in paths_to_check:
        if os.path.exists(p):
            filepath = p
            break
            
    if not filepath:
         print(f"ERRO: Arquivo de dados para '{nome_instancia}' não encontrado em 2DISPP nem 2DIKP.")
         return None

    poligonos = ler_poligonos(filepath)
    total_pecas = len(poligonos)
    
    # Contar peças diferentes (baseado na geometria/vertices)
    # Convertendo para string para usar no Counter, pois Polygon não é hashable diretamente de forma simples
    geometrias = [str(list(p.exterior.coords)) for p in poligonos]
    num_pecas_diferentes = len(Counter(geometrias))

    # Calcular dimensões sugeridas
    max_w = 0
    max_h = 0
    total_area = 0
    
    for p in poligonos:
        minx, miny, maxx, maxy = p.bounds
        w = maxx - minx
        h = maxy - miny
        max_w = max(max_w, w)
        max_h = max(max_h, h)
        total_area += p.area
        
    target_area = total_area * 1.10
    
    import math
    # Começa com o maior lado necessário
    suggested_w = max_w
    suggested_h = max_h
    
    # Se a área atual (max_w * max_h) for menor que a target_area, aumenta proporcionalmente
    current_area = suggested_w * suggested_h
    if current_area < target_area:
        ratio = math.sqrt(target_area / current_area)
        suggested_w *= ratio
        suggested_h *= ratio
        
    return {
        'Nome': nome_instancia,
        'Num_Pecas_Diferentes': num_pecas_diferentes,
        'Num_Pecas_Total': total_pecas,
        'Largura_Atual': round(w_bin, 2) if w_bin else 'N/A',
        'Altura_Atual': round(h_bin, 2) if h_bin else 'N/A',
        'Sugestao_W': round(suggested_w, 2),
        'Sugestao_H': round(suggested_h, 2),
        'Rotacoes': str(rotations) if rotations else 'N/A'
    }

if __name__ == "__main__":
    instancias = ["fu","jackobs1","jackobs2","shapes0","shapes1","shapes2","albano","shirts","trousers","dighe1","dighe2","dagli","mao","marques","swim","set0","set1","set2","series0","series1"]
    
    dados_csv = []
    print("Gerando relatório...")
    
    for inst in instancias:
        info = validar_instancia(inst)
        if info:
            dados_csv.append(info)
            print(f"Processado: {inst}")
    
    # Salvar em CSV
    csv_file = 'instancias_info.csv'
    colunas = ['Nome', 'Num_Pecas_Diferentes', 'Num_Pecas_Total', 'Largura_Atual', 'Altura_Atual', 'Sugestao_W', 'Sugestao_H', 'Rotacoes']
    
    try:
        with open(csv_file, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=colunas)
            writer.writeheader()
            writer.writerows(dados_csv)
        print(f"\nRelatório salvo com sucesso em: {csv_file}")
        
        # Preview do CSV
        print("-" * 120)
        print(f"{'Nome':<15} | {'Dif':<5} | {'Tot':<5} | {'W_Atu':<10} | {'H_Atu':<10} | {'W_Sug':<10} | {'H_Sug':<10} | {'Rot'}")
        print("-" * 120)
        for row in dados_csv:
            print(f"{row['Nome']:<15} | {row['Num_Pecas_Diferentes']:<5} | {row['Num_Pecas_Total']:<5} | {row['Largura_Atual']:<10} | {row['Altura_Atual']:<10} | {row['Sugestao_W']:<10} | {row['Sugestao_H']:<10} | {row['Rotacoes']}")
        print("-" * 120)
        
    except Exception as e:
        print(f"Erro ao salvar CSV: {e}")
