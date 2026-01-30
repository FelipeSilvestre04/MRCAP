"""
Script para atualizar as dimensões no arquivo Knapsack2D.py

Este script permite escolher qual proporção usar para cada instância
e atualiza automaticamente o dicionário specs_data no arquivo Knapsack2D.py
"""

import os
import re

# Dimensões calculadas para cada instância com diferentes proporções
DIMENSOES = {
    'set0': {
        '1:1': (1360.62, 1360.62),
        '3:4': (1178.33, 1571.11),
        '4:3': (1571.11, 1178.33),
        '16:9': (1814.16, 1020.47),
        '9:16': (1020.47, 1814.16),
        '2:3': (1110.94, 1666.41),
        '3:2': (1666.41, 1110.94),
        '5:8': (1075.67, 1721.07),
        '8:5': (1721.07, 1075.67),
    },
    'set1': {
        '1:1': (1687.92, 1687.92),
        '3:4': (1461.78, 1949.04),
        '4:3': (1949.04, 1461.78),
        '16:9': (2250.56, 1265.94),
        '9:16': (1265.94, 2250.56),
        '2:3': (1378.18, 2067.27),
        '3:2': (2067.27, 1378.18),
        '5:8': (1334.42, 2135.07),
        '8:5': (2135.07, 1334.42),
    },
    'set2': {
        '1:1': (1710.64, 1710.64),
        '3:4': (1481.45, 1975.27),
        '4:3': (1975.27, 1481.45),
        '16:9': (2280.85, 1282.98),
        '9:16': (1282.98, 2280.85),
        '2:3': (1396.73, 2095.09),
        '3:2': (2095.09, 1396.73),
        '5:8': (1352.38, 2163.8),
        '8:5': (2163.8, 1352.38),
    },
    'series0': {
        '1:1': (2433.63, 2433.63),
        '3:4': (2107.59, 2810.12),
        '4:3': (2810.12, 2107.59),
        '16:9': (3244.84, 1825.22),
        '9:16': (1825.22, 3244.84),
        '2:3': (1987.05, 2980.58),
        '3:2': (2980.58, 1987.05),
        '5:8': (1923.95, 3078.33),
        '8:5': (3078.33, 1923.95),
    },
    'series1': {
        '1:1': (4606.5, 4606.5),
        '3:4': (3989.35, 5319.13),
        '4:3': (5319.13, 3989.35),
        '16:9': (6142.0, 3454.88),
        '9:16': (3454.88, 6142.0),
        '2:3': (3761.19, 5641.79),
        '3:2': (5641.79, 3761.19),
        '5:8': (3641.76, 5826.81),
        '8:5': (5826.81, 3641.76),
    },
}

def gerar_codigo_python(proporcao='1:1'):
    """
    Gera o código Python para o dicionário specs_data
    
    Args:
        proporcao: String indicando a proporção desejada (ex: '1:1', '16:9', '3:4')
    
    Returns:
        String com o código formatado
    """
    linhas = []
    linhas.append("    specs_data = {")
    linhas.append("        'fu':        (34.0,     28.96,    [0, 1, 2, 3]),")
    linhas.append("        'jackobs1':  (13.0,     27.41,    [0, 1, 2, 3]),")
    linhas.append("        'jackobs2':  (28.2,     43.55,    [0, 1, 2, 3]),")
    linhas.append("        'shapes0':   (63.0,     23.03,    [0]),")
    linhas.append("        'shapes1':   (59.0,     24.59,    [0, 2]),")
    linhas.append("        'shapes2':   (27.3,     10.79,    [0, 2]),")
    linhas.append("        'albano':    (10122.63, 3833.58,  [0, 2]),")
    linhas.append("        'shirts':    (63.13,    31.11,    [0, 2]),")
    linhas.append("        'trousers':  (245.75,   63.65,    [0, 2]),")
    linhas.append("        'dighe1':    (138.14,   65.82,    [0]),")
    linhas.append("        'dighe2':    (134.05,   67.82,    [0]),")
    linhas.append("        'dagli':     (65.6,     42.17,    [0, 2]),")
    linhas.append("        'mao':       (2058.6,   1659.82,  [0, 1, 2, 3]),")
    linhas.append("        'marques':   (83.6,     78.23,    [0, 1, 2, 3]),")
    linhas.append("        'swim':      (6568.0,   3521.79,  [0, 2]),")
    
    # Adicionar as novas instâncias com as dimensões calculadas
    for inst in ['set0', 'set1', 'set2', 'series0', 'series1']:
        w, h = DIMENSOES[inst][proporcao]
        linhas.append(f"        '{inst}':{' ' * (12-len(inst))}({w:<10}, {h:<10}, [0, 1, 2, 3]),")
    
    linhas.append("    }")
    
    return '\n'.join(linhas)

def main():
    print("=" * 80)
    print("GERADOR DE CÓDIGO PARA ATUALIZAR Knapsack2D.py")
    print("=" * 80)
    print()
    print("Você pode escolher uma proporção diferente para cada instância!")
    print()
    print("Proporções disponíveis:")
    print("  1. 1:1   (Quadrado)")
    print("  2. 16:9  (Widescreen horizontal)")
    print("  3. 9:16  (Smartphone vertical)")
    print("  4. 3:4   (Vertical tradicional)")
    print("  5. 4:3   (Horizontal tradicional)")
    print("  6. 5:8   (Proporção áurea vertical)")
    print("  7. 8:5   (Proporção áurea horizontal)")
    print("  8. 2:3   (Vertical moderado)")
    print("  9. 3:2   (Horizontal moderado)")
    print()
    
    # Mapeamento de escolha para proporção
    escolhas = {
        '1': '1:1',
        '2': '16:9',
        '3': '9:16',
        '4': '3:4',
        '5': '4:3',
        '6': '5:8',
        '7': '8:5',
        '8': '2:3',
        '9': '3:2',
    }
    
    # Dicionário para armazenar a escolha de cada instância
    proporcoes_escolhidas = {}
    
    # Perguntar para cada instância
    instancias = ['set0', 'set1', 'set2', 'series0', 'series1']
    
    for inst in instancias:
        print(f"\n{'-'*80}")
        print(f"📦 Instância: {inst.upper()}")
        
        # Mostrar informações da instância
        if inst == 'set0':
            print(f"   25 peças | Área total: 2,036,420 | Maior peça: 733.8 × 794.5")
        elif inst == 'set1':
            print(f"   25 peças | Área total: 3,133,986 | Maior peça: 1124.5 × 794.6")
        elif inst == 'set2':
            print(f"   50 peças | Área total: 3,218,905 | Maior peça: 691.8 × 675.8")
        elif inst == 'series0':
            print(f"   118 peças | Área total: 6,514,817 | Maior peça: 1294.2 × 639.0")
        elif inst == 'series1':
            print(f"   96 peças | Área total: 23,341,841 | Maior peça: 1306.5 × 794.6")
        
        print(f"{'-'*80}")
        
        escolha = input(f"Escolha a proporção para {inst} (1-9) [padrão: 1]: ").strip() or '1'
        
        if escolha not in escolhas:
            print(f"⚠️  Escolha inválida. Usando padrão (1:1)")
            escolha = '1'
        
        proporcao = escolhas[escolha]
        proporcoes_escolhidas[inst] = proporcao
        
        w, h = DIMENSOES[inst][proporcao]
        print(f"✅ {inst}: {proporcao} → {w:.2f} × {h:.2f}")
    
    # Gerar código com proporções personalizadas
    print(f"\n{'='*80}")
    print("GERANDO CÓDIGO COM PROPORÇÕES PERSONALIZADAS")
    print(f"{'='*80}\n")
    
    # Construir o código
    linhas = []
    linhas.append("    specs_data = {")
    linhas.append("        'fu':        (34.0,     28.96,    [0, 1, 2, 3]),")
    linhas.append("        'jackobs1':  (13.0,     27.41,    [0, 1, 2, 3]),")
    linhas.append("        'jackobs2':  (28.2,     43.55,    [0, 1, 2, 3]),")
    linhas.append("        'shapes0':   (63.0,     23.03,    [0]),")
    linhas.append("        'shapes1':   (59.0,     24.59,    [0, 2]),")
    linhas.append("        'shapes2':   (27.3,     10.79,    [0, 2]),")
    linhas.append("        'albano':    (10122.63, 3833.58,  [0, 2]),")
    linhas.append("        'shirts':    (63.13,    31.11,    [0, 2]),")
    linhas.append("        'trousers':  (245.75,   63.65,    [0, 2]),")
    linhas.append("        'dighe1':    (138.14,   65.82,    [0]),")
    linhas.append("        'dighe2':    (134.05,   67.82,    [0]),")
    linhas.append("        'dagli':     (65.6,     42.17,    [0, 2]),")
    linhas.append("        'mao':       (2058.6,   1659.82,  [0, 1, 2, 3]),")
    linhas.append("        'marques':   (83.6,     78.23,    [0, 1, 2, 3]),")
    linhas.append("        'swim':      (6568.0,   3521.79,  [0, 2]),")
    
    # Adicionar as novas instâncias com as proporções escolhidas
    for inst in instancias:
        proporcao = proporcoes_escolhidas[inst]
        w, h = DIMENSOES[inst][proporcao]
        linhas.append(f"        '{inst}':{' ' * (12-len(inst))}({w:<10}, {h:<10}, [0, 1, 2, 3]),  # {proporcao}")
    
    linhas.append("    }")
    
    codigo = '\n'.join(linhas)
    print(codigo)
    
    print(f"\n{'='*80}")
    print("INSTRUÇÕES PARA ATUALIZAR Knapsack2D.py:")
    print(f"{'='*80}")
    print("1. Abra o arquivo: Python/Problems/2DIKP/Knapsack2D.py")
    print("2. Localize a função 'dimensions' (aproximadamente linha 370)")
    print("3. Substitua o dicionário 'specs_data' pelo código acima")
    print("4. Salve o arquivo")
    print()
    
    # Salvar em arquivo
    output_file = 'codigo_specs_data.txt'
    with open(output_file, 'w') as f:
        f.write(codigo)
    print(f"✅ Código também salvo em: {output_file}")
    
    # Mostrar resumo das dimensões escolhidas
    print(f"\n{'='*80}")
    print("RESUMO DAS DIMENSÕES PERSONALIZADAS:")
    print(f"{'='*80}")
    print(f"{'Instância':<15} | {'Proporção':<10} | {'Largura':<12} | {'Altura':<12} | {'Área Bin':<15}")
    print("-" * 90)
    
    for inst in instancias:
        proporcao = proporcoes_escolhidas[inst]
        w, h = DIMENSOES[inst][proporcao]
        area = w * h
        print(f"{inst:<15} | {proporcao:<10} | {w:<12.2f} | {h:<12.2f} | {area:<15.2f}")

if __name__ == "__main__":
    main()
