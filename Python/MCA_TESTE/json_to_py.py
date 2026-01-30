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
    (FUNÇÃO ORIGINAL - 4 PASSOS)
    Gera uma figura ilustrando os passos da Abertura Morfológica para MCA.
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

    # --- FIGSIZE CORRIGIDO PARA 4 PAINÉIS ---
    # Altura 5.5, bottom=0.12 -> H_plot = 4.84
    # 4 painéis 'equal' -> L_plot = 4.84
    # 3 wspace=0.05 -> L_wspace = 0.05 * 4.84
    # L_total = 4*4.84 + 3*(0.05*4.84) = 19.36 + 0.726 = 20.086
    fig, axes = plt.subplots(1, 4, figsize=(20.09, 5.5)) 
    
    # --- TÍTULO REMOVIDO ---
    # fig.suptitle(f"Ilustração do Processo de Cálculo da MCA (Distância de Buffer e = {buffer_distance:.1f})", fontsize=14) 

    steps_data = {}

    # --- Função para plotar fundo (bin + peças) ---
    def plot_background(ax):
        # Plot Bin (apenas borda)
        xb, yb = area_corte_poly.exterior.xy
        for interior in area_corte_poly.interiors:
            xi, yi = interior.xy
            ax.plot(xi, yi, color=color_bin_edge, linewidth=1.5, zorder=1)
        ax.plot(xb, yb, color=color_bin_edge, linewidth=1.5, zorder=1) # Exterior por último

        # Plot Peças Originais
        for piece in polygons_shapely_original:
            plot_shapely_geometry(ax, piece, color_piece_fill, color_piece_edge, 0.7, 0.5, zorder=2) # zorder 2
        
        ax.set_aspect('equal', adjustable='box') 
        
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

    # --- Painel (a): Layout Inicial com Retalho ---
    ax = axes[0]
    ax.set_xlabel("(a) Layout com Retalho Inicial (R)", fontsize=11) 
    plot_background(ax) 
    steps_data['a'] = remnant_polygon
    plot_shapely_geometry(ax, remnant_polygon, color_remnant_fill, color_remnant_edge, 0.6, 0.5, zorder=3)

    # --- Painel (b): Após Erosão ---
    ax = axes[1]
    ax.set_xlabel(f"(b) Sobrepõe Erosão por {buffer_distance:.1f}", fontsize=11) 
    plot_background(ax) 
    eroded_space = None
    try:
        eroded_space = remnant_polygon.buffer(-buffer_distance)
        if eroded_space and not eroded_space.is_valid and not eroded_space.is_empty:
            eroded_space = eroded_space.buffer(0)
            if not eroded_space.is_valid: eroded_space = None
        steps_data['b'] = eroded_space
        if eroded_space and not eroded_space.is_empty:
            plot_shapely_geometry(ax, eroded_space, color_eroded_fill, color_eroded_edge, 0.8, 0.5, zorder=3)
        else:
            ax.text(0.5, 0.5, "Vazio após erosão", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
    except Exception as e:
        print(f"Erro na erosão (passo b): {e}")
        ax.text(0.5, 0.5, "Erro na erosão", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)
        steps_data['b'] = None

    # --- Painel (c): Seleção do Maior Polígono Eroído ---
    ax = axes[2]
    ax.set_xlabel("(c) Sobrepõe Seleção do Maior", fontsize=11) 
    plot_background(ax)
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
    ax.set_xlabel(f"(a) Maximum Contiguous Area Metric", fontsize=11) 
    plot_background(ax) 
    final_mca_polygon = None
    largest_eroded_polygon = steps_data.get('c')
    mca_percent = 0.0

    if largest_eroded_polygon and largest_eroded_polygon.is_valid:
        try:
            dilation_distance = abs(buffer_distance)
            final_mca_polygon = largest_eroded_polygon.buffer(dilation_distance)

            if final_mca_polygon and not final_mca_polygon.is_valid and not final_mca_polygon.is_empty:
                final_mca_polygon = final_mca_polygon.buffer(0)
                if not final_mca_polygon.is_valid: final_mca_polygon = None
            steps_data['d'] = final_mca_polygon
            if final_mca_polygon and final_mca_polygon.is_valid and not final_mca_polygon.is_empty:
                plot_shapely_geometry(ax, final_mca_polygon, color_final_mca_fill, color_final_mca_edge, 0.7, 0.8, zorder=3)
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

    # --- AJUSTE DE ESPAÇAMENTO (MODIFICADO) ---
    fig.subplots_adjust(
        left=0,       # Margem esquerda removida
        right=1,      # Margem direita removida
        bottom=0.12,  # Margem inferior mantida para os xlabels
        top=1,        # Margem superior removida
        wspace=0.05,  # Espaço horizontal entre painéis
        hspace=0.1
    )
    
    if filename:
        try:
            save_path = os.path.join(os.getcwd(), filename)
            dir_name = os.path.dirname(save_path)
            if dir_name: os.makedirs(dir_name, exist_ok=True)
            plt.savefig(save_path, dpi=300) # Sem bbox_inches='tight'
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
    if not geometry.is_valid:
        geometry = geometry.buffer(0)
        if not geometry.is_valid or geometry.is_empty:
            return

    if geometry.geom_type == 'Polygon':
        x, y = geometry.exterior.xy
        ax.fill(x, y, color=face_color, ec=edge_color, alpha=alpha, linewidth=linewidth, hatch=hatch, zorder=zorder)
        for interior in geometry.interiors:
            xi, yi = interior.xy
            ax.fill(xi, yi, color='white', ec=edge_color, linewidth=linewidth*0.8, zorder=zorder+1) 
    elif geometry.geom_type == 'MultiPolygon':
        for geom in geometry.geoms:
            if geom.is_valid and not geom.is_empty:
                x, y = geom.exterior.xy
                ax.fill(x, y, color=face_color, ec=edge_color, alpha=alpha, linewidth=linewidth, hatch=hatch, zorder=zorder)
                for interior in geom.interiors:
                    xi, yi = interior.xy
                    ax.fill(xi, yi, color='white', ec=edge_color, linewidth=linewidth*0.8, zorder=zorder+1)


# ------------------------------------------------------------------
# NOVA FUNÇÃO DE CÁLCULO
# ------------------------------------------------------------------
def calculate_mca_polygon(remnant_polygon, buffer_distance):
    """
    Executa os passos de cálculo da MCA (erosão, seleção, dilatação) e 
    retorna o polígono final.
    """
    buffer_distance = abs(buffer_distance)
    
    # --- Passo (b): Erosão ---
    eroded_space = None
    try:
        eroded_space = remnant_polygon.buffer(-buffer_distance)
        if eroded_space and not eroded_space.is_valid and not eroded_space.is_empty:
            eroded_space = eroded_space.buffer(0)
            if not eroded_space.is_valid: eroded_space = None
    except Exception as e:
        print(f"Erro na erosão: {e}")
        return None

    # --- Passo (c): Seleção do Maior ---
    largest_eroded_polygon = None
    all_eroded_polygons_valid = []

    if eroded_space and not eroded_space.is_empty:
        if eroded_space.geom_type == 'Polygon':
            if eroded_space.is_valid and eroded_space.area > 1e-6:
                all_eroded_polygons_valid.append(eroded_space)
        elif eroded_space.geom_type == 'MultiPolygon':
            all_eroded_polygons_valid = [p for p in eroded_space.geoms if p.is_valid and p.area > 1e-6]

        if all_eroded_polygons_valid:
            largest_eroded_polygon = max(all_eroded_polygons_valid, key=lambda p: p.area)
    
    if not largest_eroded_polygon:
        # print("Nenhum polígono válido para selecionar após erosão.")
        return None

    # --- Passo (d): Dilatação ---
    final_mca_polygon = None
    if largest_eroded_polygon and largest_eroded_polygon.is_valid:
        try:
            dilation_distance = abs(buffer_distance)
            final_mca_polygon = largest_eroded_polygon.buffer(dilation_distance)
            if final_mca_polygon and not final_mca_polygon.is_valid and not final_mca_polygon.is_empty:
                final_mca_polygon = final_mca_polygon.buffer(0)
            if not final_mca_polygon.is_valid: final_mca_polygon = None
        except Exception as e:
            print(f"Erro na dilatação: {e}")
            return None

    return final_mca_polygon

# ------------------------------------------------------------------
# NOVA FUNÇÃO DE PLOTAGEM (1x2)
# ------------------------------------------------------------------
def plot_dual_mca_comparison(
    layout1_data, 
    layout2_data, 
    filename=None,
    # --- Parâmetros de Cor ---
    color_bin_edge = 'black',
    color_piece_fill = '#ADD8E6', # Azul claro
    color_piece_edge = 'darkblue',
    color_final_mca_fill = 'lightgreen',
    color_final_mca_edge = 'darkgreen'
    ):
    """
    Gera uma figura 1x2 comparando o Retalho Final (Passo d) de dois layouts.
    """
    
    # --- FIGSIZE CORRIGIDO PARA 2 PAINÉIS ---
    # Altura 5.5, bottom=0.12 -> H_plot = 4.84
    # 2 painéis 'equal' -> L_plot = 4.84
    # 1 wspace=0.05 -> L_wspace = 0.05 * 4.84
    # L_total = 2*4.84 + 1*(0.05*4.84) = 9.68 + 0.242 = 9.922
    fig, axes = plt.subplots(1, 2, figsize=(9.92, 5.5)) 

    # --- Função de fundo (agora interna) ---
    def plot_background(ax, area_corte_poly, polygons_shapely_original):
        # Plot Bin
        xb, yb = area_corte_poly.exterior.xy
        for interior in area_corte_poly.interiors:
            xi, yi = interior.xy
            ax.plot(xi, yi, color=color_bin_edge, linewidth=1.5, zorder=1)
        ax.plot(xb, yb, color=color_bin_edge, linewidth=1.5, zorder=1)
        # Plot Peças
        for piece in polygons_shapely_original:
            plot_shapely_geometry(ax, piece, color_piece_fill, color_piece_edge, 0.7, 0.5, zorder=2)
        ax.set_aspect('equal', adjustable='box')
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.spines['left'].set_visible(False)

        # Define os limites baseado no bin
        minx, miny, maxx, maxy = area_corte_poly.bounds
        margin_x = (maxx - minx) * 0.05
        margin_y = (maxy - miny) * 0.05
        margin_x = max(margin_x, 5)
        margin_y = max(margin_y, 5)
        ax.set_xlim(minx - margin_x, maxx + margin_x)
        ax.set_ylim(miny - margin_y, maxy + margin_y)


    # --- Painel 1: Layout 1 (Final) ---
    ax = axes[0]
    ax.set_xlabel("(a) Maximum Contiguous Area Metric", fontsize=11)
    plot_background(ax, layout1_data['area_corte_poly'], layout1_data['polygons_shapely_original'])
    if layout1_data['final_mca_polygon'] and not layout1_data['final_mca_polygon'].is_empty:
        plot_shapely_geometry(ax, layout1_data['final_mca_polygon'], 
                            color_final_mca_fill, color_final_mca_edge, 0.7, 0.8, zorder=3)
    else:
        ax.text(0.5, 0.5, "Sem retalho final", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)

    # --- Painel 2: Layout 2 (Final) ---
    ax = axes[1]
    ax.set_xlabel("(b) Maximum Contiguous Convex Area Metric", fontsize=11)
    plot_background(ax, layout2_data['area_corte_poly'], layout2_data['polygons_shapely_original'])
    if layout2_data['final_mca_polygon'] and not layout2_data['final_mca_polygon'].is_empty:
        plot_shapely_geometry(ax, layout2_data['final_mca_polygon'], 
                            color_final_mca_fill, color_final_mca_edge, 0.7, 0.8, zorder=3)
    else:
        ax.text(0.5, 0.5, "Sem retalho final", ha='center', va='center', transform=ax.transAxes, fontsize=9, color='red', zorder=4)

    # --- AJUSTE DE ESPAÇAMENTO ---
    fig.subplots_adjust(
        left=0,
        right=1,
        bottom=0.12, 
        top=1,
        wspace=0.05, # Espaço entre os 2 painéis
        hspace=0.1
    )
    
    if filename:
        try:
            save_path = os.path.join(os.getcwd(), filename)
            dir_name = os.path.dirname(save_path)
            if dir_name: os.makedirs(dir_name, exist_ok=True)
            plt.savefig(save_path, dpi=300) # Sem bbox_inches='tight'
            print(f"Figura de comparação MCA salva em '{save_path}'")
            plt.close(fig)
        except Exception as e:
            print(f"Erro ao salvar a figura de comparação: {e}")
            if plt.fignum_exists(fig.number): plt.close(fig)
    else:
        plt.show()


if __name__ == "__main__":

    # --- Dados Layout 1 ---
    # (Vou usar os mesmos dados para os dois, apenas para fins de exemplo)
    # (Em um caso real, você teria dados diferentes aqui)
    pecas_posicionadas_input_2 = [[(1213.732692965652, 40.19999999999999), (1491.532692965652, 25.0), (1484.4326929656518, 411.0), (1500.4326929656518, 417.4), (1501.032692965652, 454.5), (1344.1326929656518, 466.69999999999993), (1346.3326929656519, 494.9), (1316.3326929656519, 494.5), (1300.1326929656518, 473.6), (1310.9326929656518, 427.4), (1208.732692965652, 262.2), (1209.4326929656518, 90.0), (1185.1326929656518, 85.29999999999995), (1184.3326929656519, 51.89999999999998)], [(138.10000000000002, 1042.3326929656519), (205.40000000000003, 1058.3326929656519), (302.40000000000003, 1048.532692965652), (314.20000000000005, 1413.732692965652), (336.1, 1419.6326929656518), (333.5, 1475.1326929656518), (89.00000000000003, 1477.3326929656519), (83.40000000000003, 1501.032692965652), (28.700000000000045, 1496.4326929656518), (25.0, 1265.232692965652), (70.5, 1241.232692965652), (106.00000000000003, 1118.232692965652), (107.20000000000002, 1053.8326929656519)], [(364.9, 1471.8999999999999), (347.4, 1226.6999999999998), (689.8, 1218.1), (694.2, 1190.6), (749.0, 1193.8), (746.4, 1407.1999999999998), (766.2, 1413.5), (766.0, 1470.1), (431.29999999999995, 1477.8999999999999), (424.79999999999995, 1501.0), (372.0, 1500.3999999999999)], [(1069.7, 1259.6999999999998), (1075.9, 1223.5), (1432.8000000000002, 1232.5), (1438.3000000000002, 1210.1), (1475.0, 1210.1), (1485.5, 1232.3999999999999), (1478.6, 1440.1999999999998), (1501.0, 1445.8), (1501.0, 1481.8999999999999), (1477.5, 1494.0), (1144.5, 1479.6), (1139.7, 1500.8999999999999), (1102.9, 1501.0), (1096.7, 1267.3999999999999)], [(1043.0, 1487.3), (796.5, 1501.0), (789.1999999999999, 1169.6), (766.3, 1165.0), (768.3, 1109.2), (979.7, 1106.4), (986.0, 1085.5), (1041.1, 1086.6), (1048.0, 1421.9), (1073.0, 1429.0), (1071.5, 1480.7)], [(765.1, 41.4), (1116.2, 47.4), (1121.1, 25.0), (1157.9, 25.0), (1161.3, 254.9), (1183.7, 260.1), (1182.9, 296.8), (1159.8, 308.8), (1149.7, 298.4), (830.5, 294.5), (825.1, 315.9), (789.6999999999999, 316.5), (758.4, 84.8)], [(1231.7, 776.3), (1403.4, 794.6), (1411.8000000000002, 777.9000000000001), (1466.8000000000002, 779.2), (1478.2, 1119.3), (1501.0, 1125.1), (1499.0, 1179.0), (1301.1000000000001, 1181.8), (1295.5, 1203.7), (1239.2, 1202.6), (1228.4, 842.6), (1197.7, 837.7), (1201.7, 784.5)], [(456.59999999999997, 44.20000000000002), (679.5, 46.599999999999994), (683.5, 25.00000000000003), (733.9, 26.00000000000003), (731.4, 302.80000000000007), (751.9, 308.19999999999993), (750.8, 353.1), (588.9, 356.5), (594.3, 379.69999999999993), (553.9, 379.0), (552.0, 340.69999999999993), (448.09999999999997, 257.6), (452.4, 100.79999999999998), (426.79999999999995, 95.9), (426.2, 52.900000000000006)], [(33.3, 1007.7), (51.1, 771.7), (25.0, 765.3), (31.0, 727.5), (204.4, 743.9), (255.1, 731.8), (266.4, 772.3), (370.8, 846.3), (353.5, 857.1), (344.8, 979.3), (365.9, 988.0), (361.6, 1025.8), (80.89999999999999, 1014.9), (71.0, 1038.9), (37.7, 1036.1)], [(59.7, 388.6), (48.2, 99.80000000000001), (25.5, 97.0), (25.0, 58.5), (252.89999999999998, 50.30000000000001), (257.7, 25.600000000000023), (293.0, 25.0), (306.0, 48.400000000000034), (305.9, 311.80000000000007), (328.2, 316.40000000000003), (330.1, 351.50000000000006)], [(1464.9, 494.90000000000003), (1501.0, 501.1), (1487.1000000000001, 715.1), (1281.6000000000001, 725.8), (1276.2, 754.9000000000001), (1238.9, 751.9000000000001), (1223.2, 726.5), (1240.2, 716.6), (1249.8000000000002, 566.1), (1232.3000000000002, 559.7), (1232.5, 522.4), (1457.8000000000002, 520.0)], [(31.8, 436.6), (126.9, 436.6), (133.1, 418.0), (170.0, 419.9), (172.0, 646.0), (196.2, 648.8), (193.7, 688.0), (106.1, 686.7), (101.2, 705.6), (61.9, 705.3), (25.0, 484.6)], [(360.6, 1054.6), (533.4, 1061.0), (545.7, 1042.2), (598.5, 1041.6), (603.7, 1131.1), (629.0, 1135.3), (628.5, 1180.7), (602.5, 1195.3), (592.7, 1182.9), (408.8, 1177.2), (402.8, 1195.8), (359.5, 1196.3), (353.7, 1115.5), (329.4, 1111.3), (328.8, 1069.0)], [(1212.2, 1135.9), (1208.7, 1179.1), (1138.3999999999999, 1179.8000000000002), (1133.6, 1198.8000000000002), (1086.8999999999999, 1198.8000000000002), (1076.3999999999999, 984.9000000000001), (1053.8, 981.1000000000001), (1056.1, 936.4000000000001), (1135.0, 934.7), (1139.8, 912.2), (1185.3999999999999, 914.6000000000001), (1195.6, 938.4000000000001), (1187.0, 1130.5)], [(701.1, 1158.3), (653.9, 1140.5), (661.9, 1107.3), (643.1, 1098.8), (673.4, 1077.3), (709.8000000000001, 975.1999999999999), (695.6, 906.8), (749.6, 903.3), (771.0, 930.9), (754.3000000000001, 950.5999999999999), (756.9, 1022.5), (770.1, 1030.1), (777.6, 1081.3), (715.2, 1096.0)], [(364.1, 167.39999999999998), (391.5, 183.7), (436.9, 325.8), (492.8, 325.4), (487.9, 358.7), (460.5, 387.49999999999994), (434.9, 353.7), (355.0, 359.8), (356.5, 217.0), (334.9, 216.39999999999998), (334.5, 185.3)]]

    pecas_posicionadas_input_1 = [[(40.2, 312.3), (25.0, 34.5), (411.0, 41.60000000000002), (417.4, 25.600000000000023), (454.5, 25.0), (466.7, 181.9), (494.9, 179.7), (494.5, 209.7), (473.6, 225.9), (427.4, 215.1), (262.2, 317.3), (90.0, 316.6), (85.3, 340.9), (51.9, 341.7)], [(483.7, 1303.0), (467.7, 1370.3), (477.5, 1467.3), (112.30000000000001, 1479.1), (106.39999999999998, 1501.0), (50.89999999999998, 1498.4), (48.69999999999999, 1253.9), (25.0, 1248.3), (29.599999999999966, 1193.6), (260.79999999999995, 1189.9), (284.79999999999995, 1235.4), (407.79999999999995, 1270.9), (472.2, 1272.1)], [(758.9000000000001, 1483.5), (513.7, 1501.0), (505.1, 1158.6000000000001), (477.6, 1154.2), (480.8, 1099.4), (694.2, 1102.0), (700.5, 1082.2), (757.1, 1082.4), (764.9000000000001, 1417.1), (788.0, 1423.6), (787.4000000000001, 1476.4)], [(744.1999999999999, 25.0), (780.4, 31.200000000000003), (771.4, 388.1), (793.8, 393.6), (793.8, 430.3), (771.5, 440.8), (563.6999999999999, 433.9), (558.0999999999999, 456.3), (522.0, 456.3), (509.9, 432.8), (524.3, 99.80000000000001), (502.99999999999994, 95.0), (502.9, 58.20000000000001), (736.5, 51.99999999999999)], [(1224.3, 38.69999999999999), (1470.8, 25.0), (1478.1, 356.4), (1501.0, 361.0), (1499.0, 416.79999999999995), (1287.6, 419.6), (1281.3, 440.5), (1226.1999999999998, 439.4), (1219.3, 104.09999999999997), (1194.3, 97.0), (1195.8, 45.30000000000001)], [(1484.6, 450.79999999999995), (1478.6, 801.9), (1501.0, 806.8), (1501.0, 843.5999999999999), (1271.1, 847.0), (1265.9, 869.4), (1229.2, 868.5999999999999), (1217.2, 845.5), (1227.6, 835.4), (1231.5, 516.1999999999999), (1210.1, 510.79999999999995), (1209.5, 475.4), (1441.2, 444.09999999999997)], [(1053.0, 1501.0), (881.3000000000001, 1482.6999999999998), (872.9000000000001, 1499.3999999999999), (817.9000000000001, 1498.1), (806.5, 1158.0), (783.7, 1152.1999999999998), (785.7, 1098.3), (983.6, 1095.5), (989.2, 1073.6), (1045.5, 1074.6999999999998), (1056.3000000000002, 1434.6999999999998), (1087.0, 1439.6), (1083.0, 1492.8)], [(1470.6, 1481.8), (1247.7, 1479.4), (1243.7, 1501.0), (1193.3, 1500.0), (1195.8, 1223.1999999999998), (1175.3, 1217.8), (1176.4, 1172.8999999999999), (1338.3, 1169.5), (1332.9, 1146.3), (1373.3, 1147.0), (1375.2, 1185.3), (1479.1, 1268.3999999999999), (1474.8, 1425.1999999999998), (1500.4, 1430.1), (1501.0, 1473.1)], [(33.3, 645.0), (51.1, 409.0), (25.0, 402.6), (31.0, 364.8), (204.4, 381.2), (255.1, 369.1), (266.4, 409.6), (370.8, 483.6), (353.5, 494.4), (344.8, 616.6), (365.9, 625.3), (361.6, 663.1), (80.89999999999999, 652.2), (71.0, 676.2), (37.7, 673.4000000000001)], [(1164.5, 25.000000000000004), (1176.0, 313.8), (1198.7, 316.6), (1199.2, 355.1), (971.3000000000001, 363.3), (966.5, 388.0), (931.2, 388.6), (918.2, 365.2), (918.3000000000001, 101.8), (896.0, 97.2), (894.1, 62.10000000000001)], [(1053.3, 1013.7), (1047.1, 1049.8), (833.0999999999999, 1035.9), (822.4, 830.4), (793.3, 825.0), (796.3, 787.7), (821.6999999999999, 772.0), (831.5999999999999, 789.0), (982.0999999999999, 798.6), (988.5, 781.1), (1025.8, 781.3), (1028.2, 1006.6)], [(43.6, 1160.8), (43.6, 1065.7), (25.0, 1059.5), (26.9, 1022.5999999999999), (253.00000000000003, 1020.5999999999999), (255.80000000000004, 996.4), (295.0, 998.9), (293.7, 1086.5), (312.6, 1091.3999999999999), (312.3, 1130.7), (91.6, 1167.6)], [(626.6, 824.1999999999999), (633.0, 651.4), (614.2, 639.0999999999999), (613.6, 586.3), (703.1, 581.0999999999999), (707.3000000000001, 555.8), (752.7, 556.3), (767.3, 582.3), (754.9000000000001, 592.0999999999999), (749.2, 776.0), (767.8, 782.0), (768.3, 825.3), (687.5, 831.0999999999999), (683.3000000000001, 855.4), (641.0, 856.0)], [(623.5, 878.3000000000001), (620.0, 921.5), (549.7, 922.2), (544.9000000000001, 941.2), (498.20000000000005, 941.2), (487.70000000000005, 727.3000000000001), (465.1, 723.5), (467.40000000000003, 678.8000000000001), (546.3000000000001, 677.1), (551.1, 654.6), (596.7, 657.0), (606.9000000000001, 680.8000000000001), (598.3000000000001, 872.9000000000001)], [(1143.3, 382.1), (1190.5, 399.90000000000003), (1182.5, 433.1), (1201.3, 441.6), (1171.0, 463.1), (1134.6, 565.2), (1148.8, 633.6), (1094.8, 637.1), (1073.3999999999999, 609.5), (1090.1, 589.8), (1087.5, 517.9000000000001), (1074.3, 510.3), (1066.8, 459.1), (1129.2, 444.40000000000003)], [(54.60000000000002, 699.9000000000001), (82.00000000000001, 716.2), (127.4, 858.3000000000001), (183.3, 857.9000000000001), (178.4, 891.2), (151.0, 920.0), (125.4, 886.2), (45.5, 892.3000000000001), (47.0, 749.5), (25.400000000000006, 748.9000000000001), (25.0, 717.8000000000001)]]

    area_corte_vertices_input = ([0, 0], [1526.032692965652, 0], [1526.032692965652, 1526.032692965652], [0, 1526.032692965652])
    
    # --- Parâmetros ---
    mca_buffer_dist_val = 50.0
    buffer_seguranca = 0
    
    # --- Lógica de cálculo (reutilizada) ---
    def processar_layout_data(pecas_input, area_corte_input):
        """Função helper para carregar dados, calcular retalho inicial e MCA final."""
        try:
            area_corte_poly_obj = Polygon(area_corte_input)
            if not area_corte_poly_obj.is_valid: area_corte_poly_obj = area_corte_poly_obj.buffer(0)
            if not area_corte_poly_obj.is_valid or area_corte_poly_obj.is_empty: raise ValueError("Área de corte inválida.")

            polygons_shapely_list = []
            for i, coords in enumerate(pecas_input):
                try:
                    poly = Polygon(coords)
                    if not poly.is_valid: poly = poly.buffer(0)
                    if poly.is_valid and not poly.is_empty: polygons_shapely_list.append(poly)
                except Exception as e: print(f"Erro peça {i}: {e}. Ignorando.")
            if not polygons_shapely_list: raise ValueError("Nenhuma peça válida.")

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
                print("Layout sem retalho inicial.")
                # Retorna dados mesmo assim, para plotar o fundo
                final_mca_poly = None
            else:
                # --- Chama a nova função de CÁLCULO ---
                final_mca_poly = calculate_mca_polygon(initial_remnant_obj, mca_buffer_dist_val)
            
            # --- Prepara o dicionário de dados ---
            layout_data = {
                "area_corte_poly": area_corte_poly_obj,
                "polygons_shapely_original": polygons_shapely_list,
                "initial_remnant_polygon": initial_remnant_obj,
                "final_mca_polygon": final_mca_poly
            }
            return layout_data

        except ValueError as ve: 
            print(f"Erro de Valor ao processar layout: {ve}")
            return None
        except Exception as e: 
            print(f"Erro inesperado ao processar layout: {e}")
            return None

    # --- ESCOLHA QUAL FIGURA GERAR ---

    # --- OPÇÃO 1: Gerar a figura original de 4 passos ---
    # print("Gerando a Figura 1 (4 Passos)...")
    # layout_para_plotar_4_passos = processar_layout_data(pecas_posicionadas_input_1, area_corte_vertices_input)
    # if layout_para_plotar_4_passos and not layout_para_plotar_4_passos['initial_remnant_polygon'].is_empty:
    #     plot_mca_calculation_steps(
    #         area_corte_poly = layout_para_plotar_4_passos['area_corte_poly'],
    #         polygons_shapely_original = layout_para_plotar_4_passos['polygons_shapely_original'],
    #         remnant_polygon = layout_para_plotar_4_passos['initial_remnant_polygon'],
    #         buffer_distance = mca_buffer_dist_val,
    #         filename = "fig_mca_4_passos.png"
    #     )
    # else:
    #     print("Não foi possível gerar a figura de 4 passos.")


    # --- OPÇÃO 2: Gerar a nova figura de comparação 1x2 ---
    print("Gerando a Figura 2 (Comparação 1x2)...")
    layout1_plot_data = processar_layout_data(pecas_posicionadas_input_1, area_corte_vertices_input)
    layout2_plot_data = processar_layout_data(pecas_posicionadas_input_2, area_corte_vertices_input)

    if layout1_plot_data and layout2_plot_data:
        plot_dual_mca_comparison(
            layout1_data=layout1_plot_data,
            layout2_data=layout2_plot_data,
            filename="fig_mca_comparacao_final.png"
        )
    else:
        print("Erro: Falha ao processar um ou ambos os layouts. Figura de comparação não gerada.")