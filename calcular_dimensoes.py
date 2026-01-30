import os
import math
from shapely.geometry import Polygon
import csv

def ler_poligonos(filepath):
    """Lê polígonos de um arquivo .dat"""
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

def calcular_area_total(poligonos):
    """Calcula a área total de uma lista de polígonos"""
    return sum(p.area for p in poligonos)

def gerar_dimensoes_bin(area_total, proporcoes):
    """
    Gera dimensões de bins para diferentes proporções.
    
    Args:
        area_total: Área total das peças
        proporcoes: Lista de tuplas (largura_ratio, altura_ratio, nome)
    
    Returns:
        Lista de dicionários com as dimensões calculadas
    """
    # Área do bin deve ser tal que área_peças/área_bin = 110% (peças são maiores que o bin)
    # Isso significa que 10% das peças não cabem no bin
    area_bin = area_total / 1.10  # bin é menor que as peças
    
    resultados = []
    for w_ratio, h_ratio, nome in proporcoes:
        # Para proporção w:h, temos:
        # area_bin = w * h
        # w/h = w_ratio/h_ratio
        # Resolvendo: w = sqrt(area_bin * w_ratio / h_ratio)
        #             h = sqrt(area_bin * h_ratio / w_ratio)
        
        w = math.sqrt(area_bin * w_ratio / h_ratio)
        h = math.sqrt(area_bin * h_ratio / w_ratio)
        
        # Calculando a ocupação real
        ocupacao = (area_total / (w * h)) * 100
        
        resultados.append({
            'proporcao': nome,
            'largura': round(w, 2),
            'altura': round(h, 2),
            'area_bin': round(w * h, 2),
            'ocupacao_percent': round(ocupacao, 2)
        })
    
    return resultados

def processar_instancia(nome_instancia, base_path):
    """Processa uma instância e retorna informações sobre ela"""
    # Tentar encontrar o arquivo
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
        print(f"ERRO: Arquivo para '{nome_instancia}' não encontrado")
        return None
    
    poligonos = ler_poligonos(filepath)
    if not poligonos:
        print(f"ERRO: Nenhum polígono lido de '{nome_instancia}'")
        return None
    
    area_total = calcular_area_total(poligonos)
    
    # Calcular dimensões máximas das peças
    max_w = max(p.bounds[2] - p.bounds[0] for p in poligonos)
    max_h = max(p.bounds[3] - p.bounds[1] for p in poligonos)
    
    # Definir proporções a testar
    # (largura_ratio, altura_ratio, nome)
    proporcoes = [
        (1, 1, "1:1 (Quadrado)"),
        (3, 4, "3:4"),
        (4, 3, "4:3"),
        (1, 2, "1:2"),
        (2, 1, "2:1"),
        (9, 16, "9:16"),
        (16, 9, "16:9"),
        (2, 3, "2:3"),
        (3, 2, "3:2"),
        (5, 8, "5:8"),
        (8, 5, "8:5"),
    ]
    
    dimensoes = gerar_dimensoes_bin(area_total, proporcoes)
    
    # Filtrar apenas dimensões que comportam as maiores peças
    dimensoes_validas = []
    for dim in dimensoes:
        # Verificar se a maior peça cabe no bin (considerando rotações)
        if (dim['largura'] >= max_w and dim['altura'] >= max_h) or \
           (dim['largura'] >= max_h and dim['altura'] >= max_w):
            dimensoes_validas.append(dim)
    
    return {
        'nome': nome_instancia,
        'num_pecas': len(poligonos),
        'area_total': round(area_total, 2),
        'max_w': round(max_w, 2),
        'max_h': round(max_h, 2),
        'dimensoes': dimensoes_validas
    }

def main():
    base_path = os.getcwd()
    
    # Instâncias a processar
    instancias = ["set0", "set1", "set2", "series0", "series1"]
    
    print("=" * 100)
    print("CALCULANDO DIMENSÕES DE BINS ONDE ÁREA_PEÇAS/ÁREA_BIN = 110%")
    print("(ou seja, 10% das peças NÃO CABEM no bin)")
    print("=" * 100)
    print()
    
    todos_resultados = []
    
    for nome_inst in instancias:
        print(f"\n{'='*100}")
        print(f"Processando: {nome_inst.upper()}")
        print(f"{'='*100}")
        
        resultado = processar_instancia(nome_inst, base_path)
        
        if resultado:
            todos_resultados.append(resultado)
            
            print(f"\nNúmero de peças: {resultado['num_pecas']}")
            print(f"Área total das peças: {resultado['area_total']}")
            print(f"Maior largura de peça: {resultado['max_w']}")
            print(f"Maior altura de peça: {resultado['max_h']}")
            print(f"\nDimensões válidas do bin (que comportam as peças):")
            print(f"{'-'*100}")
            print(f"{'Proporção':<20} | {'Largura':<12} | {'Altura':<12} | {'Área Bin':<15} | {'Ocupação %':<12}")
            print(f"{'-'*100}")
            
            for dim in resultado['dimensoes']:
                print(f"{dim['proporcao']:<20} | {dim['largura']:<12} | {dim['altura']:<12} | "
                      f"{dim['area_bin']:<15} | {dim['ocupacao_percent']:<12}")
    
    # Salvar em CSV
    print(f"\n\n{'='*100}")
    print("SALVANDO RESULTADOS EM CSV")
    print(f"{'='*100}")
    
    csv_file = 'dimensoes_calculadas.csv'
    
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['Instância', 'Num_Peças', 'Área_Total', 'Max_W_Peça', 'Max_H_Peça', 
                        'Proporção', 'Largura_Bin', 'Altura_Bin', 'Área_Bin', 'Ocupação_%'])
        
        for res in todos_resultados:
            for dim in res['dimensoes']:
                writer.writerow([
                    res['nome'],
                    res['num_pecas'],
                    res['area_total'],
                    res['max_w'],
                    res['max_h'],
                    dim['proporcao'],
                    dim['largura'],
                    dim['altura'],
                    dim['area_bin'],
                    dim['ocupacao_percent']
                ])
    
    print(f"\nResultados salvos em: {csv_file}")
    
    # Gerar sugestões para atualizar Knapsack2D.py
    print(f"\n\n{'='*100}")
    print("SUGESTÕES PARA ATUALIZAR Knapsack2D.py")
    print(f"{'='*100}")
    print("\nEscolha uma proporção para cada instância e adicione no dicionário specs_data:")
    print()
    
    for res in todos_resultados:
        if res['dimensoes']:
            # Pegar a primeira proporção válida como exemplo
            dim = res['dimensoes'][0]
            print(f"'{res['nome']}':" + " " * (15-len(res['nome'])) + 
                  f"({dim['largura']:<10}, {dim['altura']:<10}, [0, 1, 2, 3]),")

if __name__ == "__main__":
    main()
