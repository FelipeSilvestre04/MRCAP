import os
import ast  # Para converter strings em literais Python (listas, tuplas) com segurança
import math
from collections import defaultdict
import matplotlib.pyplot as plt
from shapely.geometry import Polygon
from shapely.affinity import rotate, translate, affine_transform
from shapely import unary_union
import reprlib

# ------------------------------------------------------------------
# FUNÇÃO 1: CALCULAR_AREA_CONTINUA_NAO_UTILIZADA (Sem Alterações)
# ------------------------------------------------------------------
def calcular_area_continua_nao_utilizada(pecas_posicionadas, area_corte_vertices, plot=False, buffer_distance=100, name_image="layout_salvo", save=False):
    """
    Calcula a maior área contínua não utilizada, com opções para plotar e salvar.
    (Docstring original mantida)
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
            # ch_factor = largest_continuous_polygon.area / ch.area if ch.area > 0 else 0
            ch_factor = 1

    # --- 4. Cálculo das Métricas ---
    area_continua_original = 0.0
    area_continua_ponderada = 0.0
    if largest_continuous_polygon and not largest_continuous_polygon.is_empty:
        area_continua_original = largest_continuous_polygon.area
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
                image_filename = f"C:\\Users\\felip\\Documents\\GitHub\\sparrow\\data\\output\\embraer_results_oneliner\\{name_image}.png"
                data_filename = f"C:\\Users\\felip\\Documents\\GitHub\\sparrow\\data\\output\\embraer_results_oneliner\\{name_image}.txt"
            else:
                image_filename = f"C:\\Users\\felip\\Documents\\GitHub\\sparrow\\data\\output\\embraer_results_oneliner\\{name_image}.png"
                data_filename = f"C:\\Users\\felip\\Documents\\GitHub\\sparrow\\data\\output\\embraer_results_oneliner\\{name_image}.txt"
            plt.savefig(image_filename, dpi=300, bbox_inches='tight')
            plt.close(fig)

            with open(data_filename, "w") as f:
                r = reprlib.Repr()
                r.maxlist = 10000
                f.write(f"pecas_posicionadas = {r.repr(pecas_posicionadas)}\n\n")
                f.write(f"area_corte_vertices = {r.repr(area_corte_vertices)}\n")
            
            print(f"Layout e dados salvos em '{image_filename}' e '{data_filename}'")
        elif plot:
            plt.show()

    return area_continua_ponderada, porcentagem_continua, largest_continuous_polygon


# ------------------------------------------------------------------
# FUNÇÃO 2: EXTRAIR_E_PROCESSAR_DADOS (Sem Alterações)
# ------------------------------------------------------------------
def extrair_e_processar_dados(diretorio):
    """
    Varre o diretório, lê os arquivos, extrai os dados e calcula
    a porcentagem contínua para cada um.
    
    Retorna um dicionário agrupado por 'EB-i' com a lista de porcentagens.
    Ex: {"EB-1": [10.5, 11.2], "EB-14": [15.1, 14.8, 16.0]}
    """
    resultados_por_eb = defaultdict(list)
    
    print(f"Iniciando varredura e processamento em: {diretorio}\n")
    
    try:
        nomes_dos_arquivos = os.listdir(diretorio)
    except FileNotFoundError:
        print(f"Erro Crítico: O diretório não foi encontrado: {diretorio}")
        return {}
    except Exception as e:
        print(f"Erro ao acessar o diretório: {e}")
        return {}

    arquivos_processados = 0
    
    for nome_arquivo in nomes_dos_arquivos:
        
        if nome_arquivo.startswith("EB-") and nome_arquivo.endswith(".txt"):
            
            eb_id = nome_arquivo.split('_')[0]
            caminho_completo = os.path.join(diretorio, nome_arquivo)
            
            pecas_posicionadas = None
            area_corte_vertices = None
            
            try:
                with open(caminho_completo, 'r', encoding='utf-8') as f:
                    for linha in f:
                        linha_limpa = linha.strip()
                        
                        if linha_limpa.startswith("pecas_posicionadas ="):
                            string_da_lista_pecas = linha_limpa.split('=', 1)[1].strip()
                            pecas_posicionadas = ast.literal_eval(string_da_lista_pecas)
                        
                        elif linha_limpa.startswith("area_corte_vertices ="):
                            string_da_lista_area = linha_limpa.split('=', 1)[1].strip()
                            area_corte_vertices = ast.literal_eval(string_da_lista_area)

                if pecas_posicionadas is not None and area_corte_vertices is not None:
                    
                    _ , porcentagem_continua, _ = calcular_area_continua_nao_utilizada(
                        pecas_posicionadas, 
                        area_corte_vertices, 
                        plot=False,
                        save=False,
                        buffer_distance=50 
                    )
                    
                    resultados_por_eb[eb_id].append(porcentagem_continua)
                    arquivos_processados += 1
                
                else:
                    if not nome_arquivo.endswith("_summary.txt"):
                        print(f"  - AVISO: Arquivo {nome_arquivo} está incompleto (falta 'pecas' ou 'area_corte'). Pulando.")

            except (ValueError, SyntaxError) as e:
                print(f"  - AVISO: Erro ao ler dados no arquivo {nome_arquivo}. (Mal formatado?) Pulando. Erro: {e}")
            except IOError as e:
                print(f"  - AVISO: Não foi possível ler o arquivo {nome_arquivo}: {e}")
            except Exception as e:
                print(f"  - AVISO: Ocorreu um erro inesperado com o arquivo {nome_arquivo}: {e}")

    print(f"\n--- Varredura Concluída ---")
    print(f"Total de arquivos de dados processados: {arquivos_processados}")
    
    return resultados_por_eb


# ------------------------------------------------------------------
# BLOCO DE EXECUÇÃO PRINCIPAL (COM ALTERAÇÕES PARA SALVAR ARQUIVOS)
# ------------------------------------------------------------------
if __name__ == "__main__":
    
    meu_diretorio = r"C:\Users\felip\Documents\GitHub\RKO\Python\MCCA copy"
    
    # 1. Executa a função de extração e processamento
    dados_calculados = extrair_e_processar_dados(meu_diretorio)
    
    todas_as_porcentagens_gerais = []
    
    # --- NOVO ---
    # Dicionário para guardar as médias de cada EB
    medias_por_eb = {}
    
    print("\n" + "="*40)
    print("--- GERANDO SUMÁRIOS POR INSTÂNCIA ---")
    
    if not dados_calculados:
        print("Nenhum dado foi processado.")
    else:
        # 2. Itera sobre os resultados agrupados
        for eb_id, lista_de_porcentagens in sorted(dados_calculados.items()):
            
            nome_arquivo_sumario = f"{eb_id}_summary.txt"
            caminho_arquivo_sumario = os.path.join(meu_diretorio, nome_arquivo_sumario)

            if lista_de_porcentagens:
                # 3. Calcula as estatísticas
                num_runs = len(lista_de_porcentagens)
                media = sum(lista_de_porcentagens) / num_runs
                min_val = min(lista_de_porcentagens)
                max_val = max(lista_de_porcentagens)
                
                todas_as_porcentagens_gerais.extend(lista_de_porcentagens)
                
                # --- NOVO ---
                # Guarda a média desta EB no dicionário
                medias_por_eb[eb_id] = media
                
                # 4. Escreve o sumário no arquivo individual
                try:
                    with open(caminho_arquivo_sumario, 'w', encoding='utf-8') as f:
                        f.write(f"--- Resultados para {eb_id} ---\n")
                        f.write(f"  Média: {media:.2f}%\n")
                        f.write(f"  Mínimo: {min_val:.2f}%\n")
                        f.write(f"  Máximo: {max_val:.2f}%\n")
                        f.write(f"  Número de Runs: {num_runs}\n")
                        
                        f.write("\n  Valores Individuais:\n")
                        for i, valor in enumerate(lista_de_porcentagens):
                            f.write(f"    Run {i+1}: {valor:.2f}%\n")
                    
                    print(f"Sumário para {eb_id} salvo em: {nome_arquivo_sumario}")
                
                except IOError as e:
                    print(f"Erro ao salvar sumário para {eb_id}: {e}")
            
            else:
                print(f"Nenhum run processado com sucesso para {eb_id}.")

        # 5. Calcula e salva o sumário GERAL
        print("\n" + "="*40)
        print("--- GERANDO SUMÁRIO GERAL ---")
        
        nome_arquivo_geral = "_GERAL_summary.txt"
        caminho_arquivo_geral = os.path.join(meu_diretorio, nome_arquivo_geral)
        
        try:
            with open(caminho_arquivo_geral, 'w', encoding='utf-8') as f:
                
                # --- NOVO ---
                # Adiciona a lista de médias de cada instância no topo
                f.write("--- MÉDIAS POR INSTÂNCIA ---\n")
                if medias_por_eb:
                    # .items() pega a chave (eb_id) e o valor (media_eb)
                    # O 'sorted()' garante que elas fiquem em ordem
                    for eb_id, media_eb in sorted(medias_por_eb.items()):
                        f.write(f"  Média {eb_id}: {media_eb:.2f}%\n")
                else:
                    f.write("  Nenhuma média de instância foi calculada.\n")
                
                # Adiciona o sumário geral (como antes)
                f.write("\n\n--- SUMÁRIO GERAL (TODOS OS RUNS) ---\n")
                
                if todas_as_porcentagens_gerais:
                    total_runs = len(todas_as_porcentagens_gerais)
                    media_geral = sum(todas_as_porcentagens_gerais) / total_runs
                    min_geral = min(todas_as_porcentagens_gerais)
                    max_geral = max(todas_as_porcentagens_gerais)
                    
                    f.write(f"  Total de Runs Processados: {total_runs}\n")
                    f.write(f"  Média Geral: {media_geral:.2f}%\n")
                    f.write(f"  Mínimo Geral: {min_geral:.2f}%\n")
                    f.write(f"  Máximo Geral: {max_geral:.2f}%\n")
                    
                    # Imprime no console também
                    print(f"  Total de Runs Processados: {total_runs}")
                    print(f"  Média Geral: {media_geral:.2f}%")
                    print(f"  Mínimo Geral: {min_geral:.2f}%")
                    print(f"  Máximo Geral: {max_geral:.2f}%")
                    
                else:
                    f.write("  Nenhum dado foi processado.\n")
                    print("  Nenhum dado foi processado.")
            
            print(f"\nSumário GERAL salvo em: {nome_arquivo_geral}")
            
        except IOError as e:
            print(f"Erro ao salvar sumário GERAL: {e}")
            
        print("="*40)