import os
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MplPolygon
# Importa apenas o necessário para as figuras
from shapely.geometry import Polygon, MultiPolygon, box, Point
from shapely import unary_union
import numpy as np # Para centroide e pontos aleatórios


def plot_mca_calculation_steps(
    area_corte_poly,
    polygons_shapely_original,
    remnant_polygon,
    buffer_distance,
    filename=None,
    # --- NOVOS PARÂMETROS DE COR ---
    color_bin_edge = 'black',
    color_piece_fill = '#ADD8E6', # Azul claro
    color_piece_edge = 'darkblue',
    color_remnant_fill = 'lightgreen',
    color_remnant_edge = 'darkblue',
    color_eroded_fill = 'lightgreen',
    color_eroded_edge = 'black',
    color_selected_fill = 'red', # Azul claro diferente das peças
    color_selected_edge = 'red',
    color_other_eroded_fill = 'lightgreen',
    # 	 color_other_eroded_fill = 'lightgray',
    color_other_eroded_edge = 'gray',
    color_final_mca_fill = 'lightgreen',
    color_final_mca_edge = 'darkgreen'
    # --- FIM DOS PARÂMETROS DE COR ---
    ):
    """
    Gera uma figura ilustrando os passos da Abertura Morfológica para MCA.
    TODOS os painéis mostram o bin (preto) e as peças (azul).
    - Painel A: Sobrepõe Retalho Inicial (verde).
    - Painel B: Sobrepõe resultado da Erosão (cinza).
    - Painel C: Sobrepõe resultados da Erosão (cinza claro), destaca Maior (azul claro).
    - Painel D: Sobrepõe Retalho Final MCA (verde).
    Remove legendas inferiores de área. Cores configuráveis.

    Args:
        area_corte_poly (Polygon): O polígono do bin (área de corte).
        polygons_shapely_original (list): Lista dos polígonos Shapely das peças originais (já validados).
        remnant_polygon (Polygon or MultiPolygon): O polígono/multipolígono inicial do retalho.
        buffer_distance (float): A distância 'e' para erosão/dilatação (deve ser positiva).
        filename (str, optional): Nome base do arquivo para salvar (sem diretório). Se None, mostra na tela.
        **color_... : Parâmetros opcionais para definir as cores dos elementos.
    """
    # Validações Iniciais
    if not isinstance(remnant_polygon, (Polygon, MultiPolygon)) or remnant_polygon.is_empty:
        print("Erro: Polígono de retalho inválido ou vazio.")
        return
    if not remnant_polygon.is_valid: remnant_polygon = remnant_polygon.buffer(0)
    if not remnant_polygon.is_valid or remnant_polygon.is_empty:
        print("Erro: Falha ao corrigir polígono de retalho.")
        return
    if not area_corte_poly or not area_corte_poly.is_valid or area_corte_poly.is_empty:
        print("Erro: Polígono da área de corte inválido ou vazio.")
        return

    buffer_distance = abs(buffer_distance)

    # --- MUDANÇA CHAVE 1: FIGSIZE ---
    # A largura foi reduzida de 22 para 18.2 para melhor acomodar 4 painéis quadrados
    # A proporção de 22 / 5.5 = 4. A de 18.2 / 5.5 = 3.3
    fig, axes = plt.subplots(1, 4, figsize=(12.2, 3.3)) 
    # --- FIM DA MUDANÇA 1 ---

    # Título principal (sem y=)
    # fig.suptitle(f"Ilustração do Processo de Cálculo da MCA (Distância de Buffer e = {buffer_distance:.1f})", fontsize=14) 

    steps_data = {}

    # --- Função para plotar fundo (bin + peças) ---
    def plot_background(ax):
        # Plot Bin (apenas borda)
        xb, yb = area_corte_poly.exterior.xy
        # Plota interiores (buracos) do bin, se houver
        for interior in area_corte_poly.interiors:
            xi, yi = interior.xy
            ax.plot(xi, yi, color=color_bin_edge, linewidth=1.5, zorder=1)
        ax.plot(xb, yb, color=color_bin_edge, linewidth=1.5, zorder=1) # Exterior por último

        # Plot Peças Originais
        for piece in polygons_shapely_original:
            plot_shapely_geometry(ax, piece, color_piece_fill, color_piece_edge, 0.7, 0.5, zorder=2) # zorder 2
        
        # Esta linha é a causa do problema de espaçamento, mas é necessária
        ax.set_aspect('equal', adjustable='box') 
        
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

    # --- Painel (a): Layout Inicial com Retalho ---
    ax = axes[0]
    ax.set_xlabel("(a) Initial Layout with Remnant (R)", fontsize=11) 
    plot_background(ax) # Plota bin (preto) e peças (azul)
    steps_data['a'] = remnant_polygon
    plot_shapely_geometry(ax, remnant_polygon, color_remnant_fill, color_remnant_edge, 0.6, 0.5, zorder=3) # zorder 3

    # --- Painel (b): Após Erosão ---
    ax = axes[1]
    ax.set_xlabel(f"(b) Result of Erosion ", fontsize=11) 
    plot_background(ax) # Plota bin (preto) e peças (azul)
    eroded_space = None
    try:
        eroded_space = remnant_polygon.buffer(-buffer_distance)
        if eroded_space and not eroded_space.is_valid and not eroded_space.is_empty:
            eroded_space = eroded_space.buffer(0)
            if not eroded_space.is_valid: eroded_space = None
        steps_data['b'] = eroded_space
        if eroded_space and not eroded_space.is_empty:
            plot_shapely_geometry(ax, eroded_space, color_eroded_fill, color_eroded_edge, 0.8, 0.5, zorder=3) # zorder 3
        else:
            ax.text(0.5, 0.5, "Vazio após erosão", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
    except Exception as e:
        print(f"Erro na erosão (passo b): {e}")
        ax.text(0.5, 0.5, "Erro na erosão", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
        steps_data['b'] = None

    # --- Painel (c): Seleção do Maior Polígono Eroído ---
    ax = axes[2]
    ax.set_xlabel("(c) Selection of Largest Eroded Polygon", fontsize=11) 
    plot_background(ax) # Plota bin (preto) e peças (azul)
    largest_eroded_polygon = None
    all_eroded_polygons_valid = []
    eroded_space_from_b = steps_data.get('b')

    if eroded_space_from_b and not eroded_space_from_b.is_empty:
        if eroded_space_from_b.geom_type == 'Polygon':
            if eroded_space_from_b.is_valid and eroded_space_from_b.area > 1e-6:
                all_eroded_polygons_valid.append(eroded_space_from_b)
        elif eroded_space_from_b.geom_type == 'MultiPolygon':
            all_eroded_polygons_valid = [p for p in eroded_space_from_b.geoms if p.is_valid and p.area > 1e-6]

        if all_eroded_polygons_valid:
            largest_eroded_polygon = max(all_eroded_polygons_valid, key=lambda p: p.area)
        steps_data['c'] = largest_eroded_polygon

        if all_eroded_polygons_valid:
            for geom in all_eroded_polygons_valid:
                if geom != largest_eroded_polygon:
                    plot_shapely_geometry(ax, geom, color_other_eroded_fill, color_other_eroded_edge, 0.5, 0.5, zorder=3)
            if largest_eroded_polygon:
                plot_shapely_geometry(ax, largest_eroded_polygon, color_selected_fill, color_selected_edge, 0.9, 0.8, zorder=4)
        else:
            ax.text(0.5, 0.5, "Nenhum polígono\nválido para selecionar", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
            steps_data['c'] = None
    else:
        ax.text(0.5, 0.5, "Nenhum polígono\npara selecionar", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
        steps_data['c'] = None

    # --- Painel (d): Layout com Retalho Final MCA ---
    ax = axes[3]
    ax.set_xlabel(f"(d) Result after Dilation", fontsize=11) 
    plot_background(ax) # Plota bin (preto) e peças (azul)
    final_mca_polygon = None
    largest_eroded_from_c = steps_data.get('c')
    mca_percent = 0.0

    if largest_eroded_from_c and largest_eroded_from_c.is_valid:
        try:
            dilation_distance = abs(buffer_distance)
            final_mca_polygon = largest_eroded_from_c.buffer(dilation_distance)

            if final_mca_polygon and not final_mca_polygon.is_valid and not final_mca_polygon.is_empty:
                final_mca_polygon = final_mca_polygon.buffer(0)
                if not final_mca_polygon.is_valid: final_mca_polygon = None

            steps_data['d'] = final_mca_polygon

            if final_mca_polygon and final_mca_polygon.is_valid and not final_mca_polygon.is_empty:
                final_mca_area = final_mca_polygon.area
                plot_shapely_geometry(ax, final_mca_polygon, color_final_mca_fill, color_final_mca_edge, 0.7, 0.8, zorder=3) # zorder 3
            else:
                ax.text(0.5, 0.5, "Sem retalho final\n(Inválido/Vazio)", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
                steps_data['d'] = None
        except Exception as e:
            print(f"Erro na dilatação ou plotagem (passo d): {e}")
            ax.text(0.5, 0.5, "Erro na dilatação", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
            steps_data['d'] = None
    else:
        ax.text(0.5, 0.5, "Nenhum polígono\npara dilatar", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
        steps_data['d'] = None


    # --- Ajuste Final dos Limites (baseado no bin) ---
    minx, miny, maxx, maxy = area_corte_poly.bounds
    margin_x = (maxx - minx) * 0.05
    margin_y = (maxy - miny) * 0.05
    margin_x = max(margin_x, 5)
    margin_y = max(margin_y, 5)

    global_minx = minx - margin_x
    global_maxx = maxx + margin_x
    global_miny = miny - margin_y
    global_maxy = maxy + margin_y

    for ax_i in axes:
        ax_i.set_xlim(global_minx, global_maxx)
        ax_i.set_ylim(global_miny, global_maxy)
        # ax_i.set_aspect('equal') # Movido para dentro do plot_background


    # --- MUDANÇA CHAVE 2: wspace ---
    # Ajusta o espaçamento para dar lugar ao suptitle e aos xlabels (legendas)
    fig.subplots_adjust(
        left=0,    # Margem esquerda mínima
        right=1,   # Margem direita mínima
        bottom=0.12,  # Margem inferior aumentada para os xlabels
        top=1,      # Margem superior ajustada para o super-título
        wspace=0.00,  # <-- MUDANÇA CHAVE 2: wspace BEM PEQUENO
        hspace=0.1    # Espaço vertical (não relevante aqui, mas bom ter)
    )
    
    if filename:
        try:
            save_path = os.path.join(os.getcwd(), filename) # Salva na pasta atual
            dir_name = os.path.dirname(save_path)
            if dir_name: os.makedirs(dir_name, exist_ok=True)
            
            # --- MUDANÇA CHAVE 3: savefig ---
            # REMOVIDO o bbox_inches='tight' para respeitar o subplots_adjust
            plt.savefig(save_path, dpi=300)
            # --- FIM DA MUDANÇA 3 ---

            print(f"Figura do cálculo da MCA salva em '{save_path}'")
            plt.close(fig)
        except Exception as e:
            print(f"Erro ao salvar a figura do cálculo da MCA: {e}")
            if plt.fignum_exists(fig.number): plt.close(fig)
    else:
        plt.show()
# ------------------------------------------------------------------
# Função Auxiliar para Plotar Geometrias (com buracos)
# ------------------------------------------------------------------
def plot_shapely_geometry(ax, geometry, face_color, edge_color, alpha, linewidth, hatch=None, zorder=1):
    """Plota um Polygon ou MultiPolygon do Shapely no eixo Matplotlib."""
    if geometry is None or geometry.is_empty:
        return
    # Tenta corrigir geometria inválida silenciosamente antes de plotar
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
        if not geometry.is_valid or geometry.is_empty:
            return

    if geometry.geom_type == 'Polygon':
        x, y = geometry.exterior.xy
        ax.fill(x, y, color=face_color, ec=edge_color, alpha=alpha, linewidth=linewidth, hatch=hatch, zorder=zorder)
        for interior in geometry.interiors:
            xi, yi = interior.xy
            # Corrigido: buracos devem ser brancos (fundo)
            ax.fill(xi, yi, color='#ADD8E6', ec=edge_color, linewidth=linewidth*0.8, zorder=zorder+1) 
    elif geometry.geom_type == 'MultiPolygon':
        for geom in geometry.geoms:
            if geom.is_valid and not geom.is_empty:
                x, y = geom.exterior.xy
                ax.fill(x, y, color=face_color, ec=edge_color, alpha=alpha, linewidth=linewidth, hatch=hatch, zorder=zorder)
                for interior in geom.interiors:
                    xi, yi = interior.xy
                    # Corrigido: buracos devem ser brancos (fundo)
                    ax.fill(xi, yi, color='#ADD8E6', ec=edge_color, linewidth=linewidth*0.8, zorder=zorder+1)


if __name__ == "__main__":

    pecas_posicionadas = [[(1485.832692965652, 1213.732692965652), (1501.0326929656521, 1491.532692965652), (1115.0326929656521, 1484.4326929656518), (1108.632692965652, 1500.4326929656518), (1071.5326929656521, 1501.032692965652), (1059.332692965652, 1344.132692965652), (1031.132692965652, 1346.3326929656519), (1031.5326929656521, 1316.3326929656519), (1052.432692965652, 1300.132692965652), (1098.632692965652, 1310.9326929656518), (1263.832692965652, 1208.732692965652), (1436.0326929656521, 1209.4326929656518), (1440.732692965652, 1185.132692965652), (1474.132692965652, 1184.3326929656519)], [(801.4206355928875, 1075.754956599337), (817.4206355928875, 1008.454956599337), (807.6206355928875, 911.454956599337), (1172.8206355928874, 899.654956599337), (1178.7206355928874, 877.754956599337), (1234.2206355928874, 880.354956599337), (1236.4206355928875, 1124.854956599337), (1260.1206355928875, 1130.454956599337), (1255.5206355928876, 1185.1549565993369), (1024.3206355928876, 1188.8549565993371), (1000.3206355928875, 1143.3549565993371), (877.3206355928875, 1107.854956599337), (812.9206355928875, 1106.654956599337)], [(1099.7, 832.5), (1082.2, 587.3000000000001), (1424.6, 578.7), (1429.0, 551.2), (1483.8000000000002, 554.4000000000001), (1481.2, 767.8000000000001), (1501.0, 774.1), (1500.8000000000002, 830.7), (1166.1000000000001, 838.5), (1159.6000000000001, 861.6), (1106.8, 861.0)], [(1451.3999999999999, 25.0), (1487.6, 31.200000000000003), (1478.6, 388.1), (1501.0, 393.6), (1501.0, 430.3), (1478.6999999999998, 440.8), (1270.8999999999999, 433.9), (1265.3, 456.3), (1229.1999999999998, 456.3), (1217.1, 432.8), (1231.5, 99.80000000000001), (1210.1999999999998, 95.0), (1210.1, 58.20000000000001), (1443.6999999999998, 51.99999999999999)], [(999.3, 1224.3), (1013.0, 1470.8000000000002), (681.6, 1478.1), (677.0, 1501.0), (621.2, 1499.0), (618.4, 1287.6), (597.5, 1281.3), (598.6, 1226.2), (933.9000000000001, 1219.3), (941.0, 1194.3), (992.7, 1195.8)], [(780.2, 41.4), (1131.3, 47.4), (1136.2, 25.0), (1173.0, 25.0), (1176.4, 254.9), (1198.8, 260.1), (1198.0, 296.8), (1174.9, 308.8), (1164.8, 298.4), (845.6, 294.5), (840.2, 315.9), (804.8, 316.5), (773.5, 84.8)], [(573.5, 1231.7), (555.1999999999999, 1403.4), (571.9, 1411.8), (570.6, 1466.8), (230.49999999999997, 1478.1999999999998), (224.69999999999996, 1501.0), (170.79999999999998, 1499.0), (167.99999999999997, 1301.1), (146.1, 1295.5), (147.19999999999996, 1239.2), (507.19999999999993, 1228.4), (512.1, 1197.7), (565.3, 1201.7)], [(1043.6, 866.9), (820.6999999999999, 864.5), (816.6999999999999, 886.0999999999999), (766.3, 885.0999999999999), (768.8, 608.3), (748.3, 602.9), (749.4, 558.0), (911.3, 554.5999999999999), (905.9, 531.4), (946.3, 532.0999999999999), (948.2, 570.4), (1052.1, 653.5), (1047.8, 810.3), (1073.4, 815.2), (1074.0, 858.2)], [(770.9, 252.29999999999998), (753.0999999999999, 488.30000000000007), (779.2, 494.69999999999993), (773.2, 532.5), (599.8, 516.1), (549.1, 528.1999999999999), (537.8, 487.69999999999993), (433.4, 413.7), (450.7, 402.9), (459.4, 280.7), (438.3, 272.0), (442.59999999999997, 234.19999999999996), (723.3, 245.1), (733.2, 221.1), (766.5, 223.89999999999995)], [(571.6, 818.9000000000001), (282.8, 830.4000000000001), (280.0, 853.1), (241.5, 853.6), (233.3, 625.7), (208.60000000000002, 620.9000000000001), (208.0, 585.6), (231.40000000000003, 572.6), (494.8, 572.7), (499.40000000000003, 550.4000000000001), (534.5, 548.5)], [(555.9, 1095.5), (549.7, 1131.6), (335.7, 1117.7), (325.0, 912.1999999999999), (295.9, 906.8), (298.9, 869.5), (324.29999999999995, 853.8), (334.2, 870.8), (484.7, 880.4), (491.09999999999997, 862.9), (528.4, 863.0999999999999), (530.8, 1088.4)], [(43.6, 1216.3000000000002), (43.6, 1121.2), (25.0, 1115.0), (26.9, 1078.1000000000001), (253.00000000000003, 1076.1000000000001), (255.80000000000004, 1051.9), (295.0, 1054.4), (293.7, 1142.0), (312.6, 1146.9), (312.3, 1186.2), (91.6, 1223.1000000000001)], [(400.59999999999997, 56.79999999999998), (394.19999999999993, 229.59999999999994), (413.0, 241.89999999999995), (413.59999999999997, 294.69999999999993), (324.09999999999997, 299.9), (319.9, 325.19999999999993), (274.5, 324.69999999999993), (259.9, 298.69999999999993), (272.29999999999995, 288.9), (278.0, 104.99999999999997), (259.4, 98.99999999999997), (258.9, 55.69999999999996), (339.69999999999993, 49.89999999999995), (343.9, 25.599999999999937), (386.19999999999993, 24.99999999999997)], [(87.9, 506.5), (44.699999999999996, 503.0), (44.0, 432.70000000000005), (25.0, 427.90000000000003), (25.0, 381.20000000000005), (238.9, 370.70000000000005), (242.7, 348.1), (287.4, 350.40000000000003), (289.1, 429.3), (311.6, 434.1), (309.2, 479.70000000000005), (285.4, 489.90000000000003), (93.3, 481.3)], [(907.7, 491.1), (925.5, 443.90000000000003), (958.7, 451.90000000000003), (967.2, 433.1), (988.7, 463.40000000000003), (1090.8, 499.8), (1159.2, 485.6), (1162.7, 539.6), (1135.1000000000001, 561.0), (1115.4, 544.3000000000001), (1043.5, 546.9), (1035.9, 560.1), (984.7, 567.6), (970.0, 505.20000000000005)], [(778.5, 1064.2), (762.1999999999999, 1091.6), (620.0999999999999, 1137.0), (620.5, 1192.9), (587.1999999999999, 1188.0), (558.4, 1160.6), (592.1999999999999, 1135.0), (586.0999999999999, 1055.1), (728.9, 1056.6), (729.5, 1035.0), (760.5999999999999, 1034.6)]]

    area_corte_vertices = ([0, 0], [1526.032692965652, 0], [1526.032692965652, 1526.032692965652], [0, 1526.032692965652])
    print("Gerando a Figura 2 (Passos do Cálculo da MCA) com os dados fornecidos e cores ajustadas...")

    # --- Calcular o Retalho Inicial (R) ---
    try:
        area_corte_poly_obj = Polygon(area_corte_vertices)
        if not area_corte_poly_obj.is_valid: area_corte_poly_obj = area_corte_poly_obj.buffer(0)
        if not area_corte_poly_obj.is_valid or area_corte_poly_obj.is_empty: raise ValueError("Área de corte inválida.")

        polygons_shapely_list = []
        for i, coords in enumerate(pecas_posicionadas):
            try:
                poly = Polygon(coords)
                if not poly.is_valid: poly = poly.buffer(0)
                if poly.is_valid and not poly.is_empty: polygons_shapely_list.append(poly)
            except Exception as e: print(f"Erro peça {i}: {e}. Ignorando.")
        if not polygons_shapely_list: raise ValueError("Nenhuma peça válida.")

        buffer_seguranca = 0.0 # Ajuste conforme necessário
        buffered_polygons_list = []
        for i, poly in enumerate(polygons_shapely_list):
            try:
                buffered_poly = poly.buffer(buffer_seguranca, join_style='mitre')
                if not buffered_poly.is_valid: buffered_poly = buffered_poly.buffer(0)
                if buffered_poly.is_valid and not buffered_poly.is_empty:
                    buffered_polygons_list.append(buffered_poly)
                elif poly.is_valid: buffered_polygons_list.append(poly)
            except Exception as e:
                print(f"Erro buffer peça {i}: {e}. Usando original se válido.")
                if poly.is_valid: buffered_polygons_list.append(poly)
        if not buffered_polygons_list: raise ValueError("Nenhuma peça após buffer.")

        all_polygons_union_buffered_obj = unary_union(buffered_polygons_list)
        if not all_polygons_union_buffered_obj.is_valid: all_polygons_union_buffered_obj = all_polygons_union_buffered_obj.buffer(0)
        if not all_polygons_union_buffered_obj.is_valid or all_polygons_union_buffered_obj.is_empty: raise ValueError("União bufada inválida.")

        initial_remnant_obj = area_corte_poly_obj.difference(all_polygons_union_buffered_obj)
        if not initial_remnant_obj.is_valid: initial_remnant_obj = initial_remnant_obj.buffer(0)
        if not initial_remnant_obj.is_valid: raise ValueError("Retalho inicial inválido.")

        if initial_remnant_obj.is_empty:
            print("Não há área livre (retalho) para gerar a figura.")
        else:
            mca_buffer_dist_val = 50.0
            save_filename_fig2_val = "fig_mca_calculation_steps_correct_colors_final_v3.png" # Novo nome

            # Chama a função de plotagem passando todos os elementos necessários
            # E as cores desejadas como argumentos nomeados
            plot_mca_calculation_steps(
                area_corte_poly = area_corte_poly_obj,
                polygons_shapely_original = polygons_shapely_list,
                remnant_polygon = initial_remnant_obj,
                buffer_distance = mca_buffer_dist_val,
                filename = save_filename_fig2_val,
                # --- Exemplo de como passar cores personalizadas ---
                # color_bin_edge = 'dimgray',
                # color_piece_fill = 'cyan',
                # color_piece_edge = 'blue',
                # color_remnant_fill = 'yellow',
                # color_remnant_edge = 'orange',
                # color_final_mca_fill = 'lime',
                # color_final_mca_edge = 'green'
                # --- Se não passar, usa os defaults definidos na função ---
            )

    except ValueError as ve: print(f"Erro de Valor: {ve}")
    except ImportError: print("Erro: Bibliotecas não encontradas.")
    except Exception as e: print(f"Erro inesperado: {e}")