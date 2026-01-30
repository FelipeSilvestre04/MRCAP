import shapely
import csv
from shapely.geometry import Polygon, LinearRing, MultiPolygon
from shapely.ops import unary_union
import matplotlib.pyplot as plt
import os
import json 
import math

# --- FUNÇÃO DE GERAÇÃO DE ARQUIVO (Mantida, mas não usada nesta versão) ---
def gerar_sparrow_json(poligonos_tratados_com_area, nome_instancia, output_filepath, altura_chapa=None):
    """
    Gera um arquivo JSON no formato de entrada do Sparrow.
    
    :param poligonos_tratados_com_area: Lista de tuplas (id, vertices, area)
    :param nome_instancia: Nome da instância (ex: "EB-1_buffer")
    :param output_filepath: Caminho completo para salvar o arquivo .json
    :param altura_chapa: Altura da chapa (float). Se None, calcula automaticamente.
    """
    
    if altura_chapa is None:
        soma_areas = sum(area for _, _, area in poligonos_tratados_com_area)
        if soma_areas == 0:
            print("Aviso: Soma das áreas é zero. Não é possível calcular altura automática.")
            strip_height = 1000.0 # Valor padrão de fallback
        else:
            DENSITY = 0.5  
            # Fórmula geral: altura = sqrt(soma_das_areas / densidade)
            altura_calculada = math.sqrt(soma_areas / DENSITY)
            print(f"Soma das áreas das peças: {soma_areas:.2f}")
            print(f"Altura da chapa (strip_height) calculada ({int(DENSITY*100)}% densidade): {altura_calculada:.2f}")
            strip_height = altura_calculada
    else:
        strip_height = altura_chapa
        print(f"Altura da chapa (strip_height) fornecida: {strip_height:.2f}")

    sparrow_data = {
        "name": nome_instancia,
        "items": [],
        "strip_height": round(strip_height, 4)
    }

    for id_poligono, vertices, _ in poligonos_tratados_com_area:
        min_x = min(v[0] for v in vertices)
        min_y = min(v[1] for v in vertices)
        
        vertices_normalizados = [
            [round(v[0] - min_x, 1), round(v[1] - min_y, 1)] 
            for v in vertices
        ]
        
        if vertices_normalizados[0] != vertices_normalizados[-1]:
             vertices_json = vertices_normalizados + [vertices_normalizados[0]]
        else:
             vertices_json = vertices_normalizados

        item = {
            "id": id_poligono,
            "allowed_orientations": [0.0, 90.0, 180.0, 270.0],
            "shape": {
                "type": "simple_polygon",
                "data": vertices_json
            },
            "min_quality": None,
            "demand": 1
        }
        sparrow_data["items"].append(item)

    try:
        os.makedirs(os.path.dirname(output_filepath), exist_ok=True)
        with open(output_filepath, 'w') as f_json:
            json.dump(sparrow_data, f_json, indent=2)
        print(f"Arquivo JSON '{output_filepath}' gerado com {len(sparrow_data['items'])} itens.")
    
    except Exception as e:
        print(f"Erro ao gerar o arquivo JSON: {e}")

# --- FUNÇÃO DE PLOTAGEM (Original) ---
def calcular_e_plotar_maior_area_livre(lista_de_poligonos):
    """
    Calcula e plota a maior área livre contínua em um layout de polígonos,
    usando uma operação de abertura morfológica.
    """
    if not lista_de_poligonos:
        print("A lista de polígonos está vazia.")
        return

    fig, ax = plt.subplots(figsize=(8, 8))
    polygons_shapely = [Polygon(p) for p in lista_de_poligonos]
    all_polygons_union = unary_union(polygons_shapely)

    min_x, min_y, max_x, max_y = all_polygons_union.bounds
    margin = 1.0
    bounding_box = Polygon([
        (min_x - margin, min_y - margin), (max_x + margin, min_y - margin),
        (max_x + margin, max_y + margin), (min_x - margin, max_y + margin)
    ])
    free_space = bounding_box.difference(all_polygons_union)
    
    buffer_distance = 100 
    largest_continuous_polygon = None

    if not free_space.is_empty:
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

    ax.set_title('Maior Área Livre Contínua')
    
    for poly in polygons_shapely:
        x, y = poly.exterior.xy
        ax.fill(x, y, alpha=0.5, color='gray', ec='black')

    if largest_continuous_polygon and not largest_continuous_polygon.is_empty:
        area_val = largest_continuous_polygon.area/bounding_box.area * 100
        print(f"Maior área livre contínua encontrada com área: {area_val:.2f}")
        x_l, y_l = largest_continuous_polygon.exterior.xy
        ax.fill(x_l, y_l, color='green', alpha=0.6, label=f'Maior Área Contínua ({area_val:.2f})')
    else:
        print("Nenhuma área livre contínua significativa foi encontrada.")

    ax.set_aspect('equal', adjustable='box')
    ax.legend()
    plt.grid(True)
    plt.show()

# --- <<< NOVA FUNÇÃO DE ANÁLISE >>> ---
def analisar_instancia(poligonos_tratados_com_area, nome_instancia):
    """
    Extrai e retorna um dicionário com os dados da instância 
    (sem gerar arquivos), calculados para uma densidade de 0.5.
    """
    
    # 1. Número de peças (Total)
    num_pecas = len(poligonos_tratados_com_area)
    
    if num_pecas == 0:
        # Retorna None se não houver peças, para pular esta instância
        return None

    # 2. Número de peças diferentes (baseado na forma normalizada)
    formas_unicas = set()
    for _, vertices, _ in poligonos_tratados_com_area:
        if not vertices: 
            continue
            
        # Normaliza a peça para a origem (0,0)
        min_x = min(v[0] for v in vertices)
        min_y = min(v[1] for v in vertices)
        
        # Cria uma tupla de tuplas (que pode ser adicionada a um set)
        # com os vértices normalizados e arredondados.
        forma_normalizada = tuple(
            (round(v[0] - min_x, 1), round(v[1] - min_y, 1))
            for v in vertices
        )
        formas_unicas.add(forma_normalizada)
    
    num_pecas_diferentes = len(formas_unicas)

    # 3. Altura e Largura (com densidade 0.5)
    soma_areas = sum(area for _, _, area in poligonos_tratados_com_area)
    DENSITY = 0.5  # Conforme solicitado
    
    altura_calculada = 0.0
    if soma_areas > 0:
        # A fórmula usada (sqrt(soma_areas / densidade)) assume que
        # a chapa é quadrada (Altura == Largura).
        altura_calculada = math.sqrt(soma_areas / DENSITY)
    
    # Baseado na fórmula, a largura é igual à altura
    largura_calculada = altura_calculada 

    # 4. Monta o dicionário de dados
    dados = {
        "Instancia": nome_instancia,
        "Num_Pecas": num_pecas,
        "Num_Pecas_Diferentes": num_pecas_diferentes,
        "Altura_0.5": round(altura_calculada, 2),
        "Largura_0.5": round(largura_calculada, 2)
    }
    
    return dados

# --- Início do Script Principal ---

file_path = 'Trajectory_layer_'
    
# ---------- PARÂMETROS DE CONTROLE ----------
CLOSING_DISTANCE = 5.0 
OPENING_DISTANCE = 5.0
SIMPLIFICATION_TOLERANCE = 10
# --------------------------------------------

# <<< MODIFICAÇÃO 1: Lista para guardar o resumo >>>
todos_os_dados_instancias = [] 

for i in range(1, 15):
    file_name = f'{i}.csv'
    poligonos_originais = []
    poligonos_tratados = [] 

    try:
        with open(f'{file_path}{file_name}', 'r', newline='') as file:
            leitor_csv = csv.reader(file)
            header = next(leitor_csv)
            
            for row in leitor_csv:
                if not row: continue

                id_poligono = int(row[0])
                lista_de_vertices = []
                celulas_coordenadas = row[1:]
                
                for celula in celulas_coordenadas:
                    if not celula: continue
                    coordenadas_str = celula.strip().replace('[', '').replace(']', '')
                    x_str, y_str = coordenadas_str.split(',')
                    vertice = (float(x_str), float(y_str))
                    lista_de_vertices.append(vertice)
                
                if not lista_de_vertices: continue

                poligonos_originais.append((id_poligono, lista_de_vertices))

                # --- BLOCO DE TRATAMENTO GEOMÉTRICO ---
                current_polygon = Polygon(lista_de_vertices).buffer(0)
                if current_polygon.is_empty: continue

                closed_geom = current_polygon.buffer(CLOSING_DISTANCE).buffer(-CLOSING_DISTANCE)
                if closed_geom.is_empty: continue
                
                eroded_geom = closed_geom.buffer(-OPENING_DISTANCE)
                if eroded_geom.is_empty: continue

                largest_eroded_part = max(eroded_geom.geoms, key=lambda p: p.area, default=None) if eroded_geom.geom_type == 'MultiPolygon' else eroded_geom
                if largest_eroded_part is None: continue

                final_polygon = largest_eroded_part.buffer(OPENING_DISTANCE)
                if final_polygon.is_empty or final_polygon.geom_type != 'Polygon': continue

                simplified_polygon = final_polygon.simplify(SIMPLIFICATION_TOLERANCE, preserve_topology=True)
                if simplified_polygon.is_empty or simplified_polygon.geom_type != 'Polygon': continue

                # --- ETAPA DE ARREDONDAMENTO E VALIDAÇÃO ---
                rounded_coords = [(round(x, 1), round(y, 1)) for x, y in simplified_polygon.exterior.coords]
                if len(rounded_coords) < 4: continue
                
                rounded_polygon = Polygon(rounded_coords).buffer(0)
                if not rounded_polygon.is_valid or rounded_polygon.is_empty: continue

                area_poligono = rounded_polygon.area

                # --- ETAPA DE FORMATAÇÃO PARA poly_decomp (ORDEM CCW) ---
                ring = LinearRing(list(rounded_polygon.exterior.coords))
                
                coords_ccw = list(ring.coords)[::-1] if not ring.is_ccw else list(ring.coords)
                
                if coords_ccw and coords_ccw[0] == coords_ccw[-1]:
                    coords_finais_para_lib = coords_ccw[:-1]
                else:
                    coords_finais_para_lib = coords_ccw
                
                if len(coords_finais_para_lib) >= 3:
                     poligonos_tratados.append((id_poligono, coords_finais_para_lib, area_poligono))

    except FileNotFoundError:
        print(f"Aviso: O arquivo '{file_path}{file_name}' não foi encontrado. Pulando.")
        continue

    # --- ESCRITA DO ARQUIVO DE INSTÂNCIA (.dat) ---
    if poligonos_tratados:
        output_filename_dat = f'C:\\Users\\felip\\Documents\\GitHub\\RKO\\Python\\Problems\\2DISPP\\EB-{i}.dat'
        
        os.makedirs(os.path.dirname(output_filename_dat), exist_ok=True)

        with open(output_filename_dat, 'w') as f:
            f.write(f"{len(poligonos_tratados)}\n\n")

            for id_poligono, vertices, _ in poligonos_tratados: # Ignora a área
                min_x = min(v[0] for v in vertices)
                min_y = min(v[1] for v in vertices)
                vertices_normalizados = [(v[0] - min_x, v[1] - min_y) for v in vertices]

                f.write(f"{len(vertices_normalizados)}\n")
                for x, y in vertices_normalizados:
                    f.write(f"{x:.1f} {y:.1f}\n") 
                f.write("\n")
        
        print(f"Arquivo '{output_filename_dat}' gerado com {len(poligonos_tratados)} polígonos.")

        # --- <<< MODIFICAÇÃO 2: Bloco de Análise de Dados (Substitui o JSON) >>> ---
        nome_instancia = f"EB-{i}"
        
        # Chama a nova função de análise
        dados_instancia = analisar_instancia(poligonos_tratados, nome_instancia)
        
        if dados_instancia:
            # Guarda os dados para o resumo final
            todos_os_dados_instancias.append(dados_instancia)
            
            # Imprime os dados imediatamente
            print(f"--- Dados da Instância: {nome_instancia} ---")
            print(f"  Total de Peças: {dados_instancia['Num_Pecas']}")
            print(f"  Peças Diferentes: {dados_instancia['Num_Pecas_Diferentes']}")
            print(f"  Altura (50%): {dados_instancia['Altura_0.5']:.2f}")
            print(f"  Largura (50%): {dados_instancia['Largura_0.5']:.2f}")
            print("-" * (28 + len(nome_instancia)))
        # --- <<< FIM DA MODIFICAÇÃO 2 >>> ---

    else:
        print(f"Nenhum polígono válido foi processado para o arquivo '{file_name}'. Nenhum arquivo de saída foi gerado.")

    # --- VISUALIZAÇÃO (Opcional) ---
    if poligonos_tratados:
        print(f"Média de vértices por polígono tratado: {sum(len(v) for _, v, _ in poligonos_tratados) / len(poligonos_tratados):.2f}")
        print(f"Média de vértices por polígono original: {sum(len(v) for _, v in poligonos_originais) / len(poligonos_originais):.2f}")
        
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(20, 10))
        ax1.set_title(f'Originais ({len(poligonos_originais)}) - {file_name}')
        for _, vertices in poligonos_originais:
            vertices_fechados = vertices + [vertices[0]]
            listas_x, listas_y = zip(*vertices_fechados)
            ax1.plot(listas_x, listas_y, linestyle='-', alpha=0.7)
        ax1.set_aspect('equal', adjustable='box')
        ax1.grid(True)
        
        ax2.set_title(f'Tratados ({len(poligonos_tratados)})')
        for _, vertices, _ in poligonos_tratados: # Ignora a área
            vertices_fechados = vertices + [vertices[0]]
            listas_x, listas_y = zip(*vertices_fechados)
            ax2.plot(listas_x, listas_y, linestyle='-', alpha=0.7)
        ax2.set_aspect('equal', adjustable='box')
        ax2.grid(True)
        plt.show()

# --- <<< MODIFICAÇÃO 3: Impressão do Resumo Final >>> ---
print("\n" * 3)
print("=" * 80)
print("Resumo de Todas as Instâncias (Densidade 0.5)")
print("=" * 80)

if todos_os_dados_instancias:
    # Imprime o cabeçalho
    print(f"{'Instancia':<15} | {'Num_Pecas':>10} | {'Pecas_Difer':>12} | {'Altura':>10} | {'Largura':>10}")
    print("-" * 80)
    
    # Imprime os dados de cada instância
    for dados in todos_os_dados_instancias:
        print(f"{dados['Instancia']:<15} | {dados['Num_Pecas']:>10} | {dados['Num_Pecas_Diferentes']:>12} | {dados['Altura_0.5']:>10.2f} | {dados['Largura_0.5']:>10.2f}")
else:
    print("Nenhum dado foi gerado.")

print("=" * 80)