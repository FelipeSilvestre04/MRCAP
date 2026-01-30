# Importe sua classe e as bibliotecas necessárias
from SPP2D import SPP2D
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MPolygon
import os
import numpy as np

# ==============================================================================
# VERSÃO FINAL DA FUNÇÃO DE PLOTAGEM - Limpa e com texto interno
# ==============================================================================
def draw_geometric_tools_final_version(
    already_placed_pieces,
    area_width,
    area_height,
    candidate_placements, # Recebe uma lista de "fantasmas" para desenhar
    filename=None
):
    """
    Cria uma figura limpa que simula o posicionamento de uma peça
    em várias posições candidatas, com legendas dentro das peças.
    """
    fig, ax = plt.subplots(figsize=(10, 8))

    # 1. Desenha a área de corte
    ax.add_patch(Rectangle((0, 0), area_width, area_height,
                           edgecolor='black', facecolor='white', linewidth=2, zorder=1))

    # 2. Desenha as peças já posicionadas em um tom de vermelho transparente
    for verts in already_placed_pieces:
        poly = MPolygon(verts, closed=True, facecolor=(173/255, 216/255, 230/255), alpha=1, edgecolor='#00008B', zorder=2)
        ax.add_patch(poly)

    # 3. Desenha cada "peça fantasma" candidata
    if candidate_placements:
        for candidate in candidate_placements:
            rule_name = candidate['rule_name']
            if rule_name is 'BL':
                rule_name = 'LB'
            elif rule_name is 'LB':
                rule_name = 'BL'
            elif rule_name is 'NCG':
                rule_name = 'NLC'
            elif rule_name is 'NCNFP':
                rule_name = 'NFC'
            elif rule_name is 'UR':
                rule_name = 'RU'    
            elif rule_name is 'RU':
                rule_name = 'UR'
            elif rule_name is 'UL':
                rule_name = 'LU'
            elif rule_name is 'NC':
                rule_name = 'NBC'
            verts = candidate['vertices']

            # Desenha o polígono semi-transparente (um pouco mais escuro para destaque)
            poly = MPolygon(verts, closed=True, facecolor='red', alpha=0.60, 
                            edgecolor='darkred', linewidth=2.5, linestyle='--', zorder=4)
            ax.add_patch(poly)
            
            # Adiciona a legenda no centro da peça fantasma
            centroid = np.mean(verts, axis=0)
            ax.text(centroid[0], centroid[1], f"{rule_name}\nPosition", 
                    ha='center', va='center', fontsize=12, fontweight='bold', color='black',
                    zorder=5, bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', boxstyle='round,pad=0.3'))

    # 4. Configurações finais para focar apenas na área de corte
    ax.set_aspect('equal')
    ax.axis('off')
    # Adiciona uma pequena margem para que os contornos não fiquem cortados
    ax.set_xlim(-area_width*0.02, area_width * 1.02)
    ax.set_ylim(-area_height*0.02, area_height * 1.02)
    plt.tight_layout(pad=0.2)

    if filename:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        plt.savefig(filename, dpi=300)
        print(f"Figura salva em: {filename}")
    else:
        plt.show()
    plt.close(fig)

# ==============================================================================
# BLOCO DE EXECUÇÃO (Permanece interativo para você escolher o layout)
# ==============================================================================
if __name__ == '__main__':

    # --- FASE 1: Configuração Interativa do Layout ---
    env = SPP2D(dataset='fu', decoder="D1_A")
    print("--- Configuração do Layout Inicial ---")
    print("Instruções: Posicione algumas peças para criar o cenário para a figura.")
    
    pecas_colocadas = 0
    while True:
        print(f"\nPeças já posicionadas: {pecas_colocadas}. Peças restantes: {len(env.lista)}")
        if not env.lista:
            print("Todas as peças foram posicionadas.")
            break

        try:
            regra_str = input(f"Digite o índice da regra {list(env.regras.keys())} (ou 'f' para finalizar setup): ")
            if regra_str.lower() == 'f':
                break
            
            regra_idx = int(regra_str)
            grau_idx = 0 # Fixando rotação em 0 para simplificar
            
            success = env.pack(0, grau_idx, regra_idx) 
            
            if success:
                print(f"Peça posicionada com sucesso.")
                pecas_colocadas += 1
            else:
                print(f"Falha ao posicionar. Tente outra regra.")

        except (ValueError, KeyError):
            print("Entrada inválida. Por favor, digite um número de regra válido ou 'f'.")

    # --- FASE 2: Geração da Figura de Análise ---
    print("\n--- Gerando a figura de análise para a próxima peça ---")
    
    if env.lista:
        peca_a_analisar_idx = 0
        rotacao_a_analisar = 0

        peca_a_analisar_coords = env.rot_pol(peca_a_analisar_idx, rotacao_a_analisar)
        
        rules_to_show = ['NCG', 'NCNFP']
        
        candidate_placements = []
        for rule_name in rules_to_show:
            func_to_call = next((func for func in env.regras.values() if func.__name__.upper() == rule_name), None)
            
            if func_to_call:
                pos = func_to_call(peca_a_analisar_idx, rotacao_a_analisar)
                if pos:
                    translated_verts = [(v[0] + pos[0], v[1] + pos[1]) for v in peca_a_analisar_coords]
                    candidate_placements.append({
                        'rule_name': rule_name,
                        'vertices': translated_verts
                    })

        if candidate_placements:
            draw_geometric_tools_final_version(
                already_placed_pieces=env.pecas_posicionadas,
                area_width=env.base,
                area_height=env.altura,
                candidate_placements=candidate_placements,
                filename="output\\geometric_tools_final_layout.svg"
            )
        else:
            print("Nenhuma posição válida encontrada para as regras especificadas.")
    else:
        print("Não há mais peças para gerar a figura de análise.")