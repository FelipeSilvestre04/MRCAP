import pygame
import sys
import copy
from collections import OrderedDict
import math
from shapely.geometry import Point, Polygon, LineString, MultiPoint, MultiLineString

# Supondo que SPP2D.py está na mesma pasta
from SPP2D import SPP2D, extrair_vertices

# --- Classe auxiliar para Botões ---
class Button:
    def __init__(self, rect, text, bg_color=(200, 200, 200), text_color=(0, 0, 0), font_size=18):
        self.rect = pygame.Rect(rect)
        self.text = text
        self.bg_color = bg_color
        self.text_color = text_color
        self.font = pygame.font.SysFont('Arial', font_size, bold=True)

    def draw(self, screen):
        pygame.draw.rect(screen, self.bg_color, self.rect, border_radius=8)
        pygame.draw.rect(screen, (50, 50, 50), self.rect, width=3, border_radius=8)
        text_surf = self.font.render(self.text, True, self.text_color)
        text_rect = text_surf.get_rect(center=self.rect.center)
        screen.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)

# --- Classe Principal do Visualizador ---
class Visualizer:
    def __init__(self, spp_env, screen_width=1280, screen_height=800):
        self.spp_env = spp_env
        self.width, self.height = screen_width, screen_height
        self.padding, self.sidebar_width, self.panel_height = 50, 300, 140
        pygame.init()
        self.screen = pygame.display.set_mode((self.width, self.height))
        pygame.display.set_caption("GEOMETRY-ITOR Framework")
        self.font = pygame.font.SysFont('Arial', 20); self.font_metrics = pygame.font.SysFont('Arial', 22, bold=True)
        self.font_count = pygame.font.SysFont('Arial', 18, bold=True); self.font_title = pygame.font.SysFont('Arial', 50, bold=True)
        self.clock = pygame.time.Clock()
        self.BG_COLOR = (240, 240, 240); self.BIN_COLOR = (20, 20, 40); self.SIDEBAR_COLOR = (210, 210, 210)
        self.PIECE_COLORS = [(227,88,88),(98,194,91),(91,157,194),(230,155,79),(170,102,204),(240,228,66)]
        
        self.mode = 'MENU'
        
        # Estado do Modo SPP
        self.spp_selected_piece_idx = None; self.spp_selected_rotation = 0; self.spp_unique_pieces_view = []
        self.spp_feasible_vertices = []; self.spp_current_vertex_idx = 0; self.spp_sidebar_scroll_y = 0
        self.spp_sidebar_content_height = 0; self.spp_buttons = {}
        self.spp_hovered_rule_name = None # NOVO: Para preview dinâmico

        # Estado do Modo NFP
        self.nfp_placed_pieces = []; self.nfp_selected_piece_idx = None; self.nfp_selected_rotation = 0
        self.nfp_vertices = []; self.nfp_current_vertex_idx = 0; self.nfp_sidebar_scroll_y = 0; self.nfp_buttons = {}
        
        self.spp_scale_factor = self._calculate_spp_scale()
        self.menu_buttons = {}; self.back_to_menu_button = Button((self.width - 110, 10, 100, 40), "Menu", bg_color=(100,100,100))

    def run(self):
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
            
            # Reseta o botão sobrevoado a cada frame
            self.spp_hovered_rule_name = None

            if self.mode == 'MENU':
                self._handle_menu_events(events, mouse_pos)
                self._draw_menu()
            elif self.mode == 'SPP_SOLVER':
                self._handle_spp_events(events, mouse_pos)
                self._draw_spp_mode()
            elif self.mode == 'NFP_EXPLORER':
                self._handle_nfp_events(events, mouse_pos)
                self._draw_nfp_mode()
            
            pygame.display.flip()
            self.clock.tick(60)
        pygame.quit()
        sys.exit()

    def _draw_menu(self):
        self.screen.fill(self.BG_COLOR)
        title_surf = self.font_title.render("GEOMETRY-ITOR Framework", True, (50, 50, 50))
        self.screen.blit(title_surf, title_surf.get_rect(centerx=self.width / 2, y=150))
        menu_button_w, menu_button_h, center_x = 500, 70, self.width / 2
        self.menu_buttons = {
            'SPP_SOLVER': Button((center_x - menu_button_w / 2, 300, menu_button_w, menu_button_h), "Solucionador de Empacotamento (SPP)", font_size=24),
            'NFP_EXPLORER': Button((center_x - menu_button_w / 2, 400, menu_button_w, menu_button_h), "Explorador de Geometria (NFP)", font_size=24),
        }
        for button in self.menu_buttons.values(): button.draw(self.screen)

    def _handle_menu_events(self, events, mouse_pos):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.menu_buttons['SPP_SOLVER'].is_clicked(mouse_pos): self._reset_spp_mode(); self.mode = 'SPP_SOLVER'
                if self.menu_buttons['NFP_EXPLORER'].is_clicked(mouse_pos): self._reset_nfp_mode(); self.mode = 'NFP_EXPLORER'

    # --- Métodos do Modo NFP --- (Sem alterações, incluído para ser completo)
    def _reset_nfp_mode(self):
        self.nfp_placed_pieces = []; self.nfp_selected_piece_idx = None; self.nfp_selected_rotation = 0
        self.nfp_vertices = []; self.nfp_current_vertex_idx = 0; self.spp_env.reset()

    def _handle_nfp_events(self, events, mouse_pos):
        if mouse_pos[0] < self.sidebar_width:
            for event in events:
                if event.type == pygame.MOUSEWHEEL:
                    self.nfp_sidebar_scroll_y -= event.y * 20
                    max_scroll = self.spp_sidebar_content_height - self.height
                    self.nfp_sidebar_scroll_y = max(0, min(self.nfp_sidebar_scroll_y, max_scroll if max_scroll > 0 else 0))
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_to_menu_button.is_clicked(mouse_pos): self.mode = 'MENU'; return
                for piece_info in self.spp_unique_pieces_view:
                    if piece_info.get('rect') and piece_info['rect'].collidepoint(mouse_pos):
                        self.nfp_selected_piece_idx = piece_info['first_idx']; self.nfp_selected_rotation = 0
                        if self.nfp_placed_pieces: self._update_nfp()
                        return
                if self.nfp_buttons['RESET'].is_clicked(mouse_pos): self._reset_nfp_mode()
                if self.nfp_selected_piece_idx is not None:
                    if 'ROT' in self.nfp_buttons and self.nfp_buttons['ROT'].is_clicked(mouse_pos):
                        self.nfp_selected_rotation = (self.nfp_selected_rotation + 1) % 4
                        if self.nfp_placed_pieces: self._update_nfp()
                    if not self.nfp_placed_pieces and 'PLACE_INIT' in self.nfp_buttons and self.nfp_buttons['PLACE_INIT'].is_clicked(mouse_pos):
                        peca_original = self.spp_env.lista[self.nfp_selected_piece_idx]; original_index_in_list = self.spp_env.lista_original.index(peca_original)
                        self.nfp_placed_pieces.append({'x':0, 'y':0, 'grau_idx': self.nfp_selected_rotation, 'pol_idx': original_index_in_list})
                        self.spp_env.lista.pop(self.nfp_selected_piece_idx); self.nfp_selected_piece_idx = None
                    if self.nfp_placed_pieces and self.nfp_vertices:
                        num_v = len(self.nfp_vertices)
                        if self.nfp_buttons['NEXT_V'].is_clicked(mouse_pos): self.nfp_current_vertex_idx = (self.nfp_current_vertex_idx + 1) % num_v
                        if self.nfp_buttons['PREV_V'].is_clicked(mouse_pos): self.nfp_current_vertex_idx = (self.nfp_current_vertex_idx - 1 + num_v) % num_v
                        if self.nfp_buttons['PLACE_V'].is_clicked(mouse_pos):
                            pos = self.nfp_vertices[self.nfp_current_vertex_idx]; peca_original = self.spp_env.lista[self.nfp_selected_piece_idx]
                            original_index_in_list = self.spp_env.lista_original.index(peca_original)
                            self.nfp_placed_pieces.append({'x':pos[0], 'y':pos[1], 'grau_idx': self.nfp_selected_rotation, 'pol_idx': original_index_in_list})
                            self.spp_env.lista.pop(self.nfp_selected_piece_idx); self.nfp_selected_piece_idx, self.nfp_vertices = None, []

    def _draw_nfp_panel(self):
        panel_rect = pygame.Rect(self.sidebar_width, self.height - self.panel_height, self.width - self.sidebar_width, self.panel_height); pygame.draw.rect(self.screen, (220, 220, 220), panel_rect)
        p_y, base_x = self.height - self.panel_height + 20, self.sidebar_width; self.nfp_buttons = {'RESET': Button((self.width - 110, p_y + 65, 90, 40), "Reset", bg_color=(220, 50, 50))}
        if self.nfp_selected_piece_idx is not None:
            self.nfp_buttons['ROT'] = Button((self.width - 210, p_y + 15, 190, 40), "Rotacionar")
            if not self.nfp_placed_pieces: self.nfp_buttons['PLACE_INIT'] = Button((base_x + 20, p_y + 40, 250, 60), "Posicionar Peça Inicial", font_size=20)
            else:
                self.nfp_buttons.update({'PLACE_V': Button((base_x + 275, p_y - 5, 180, 40), "Posicionar Vértice", bg_color=(170, 102, 204)), 'PREV_V': Button((base_x + 295, p_y + 70, 50, 40), "<"), 'NEXT_V': Button((base_x + 355, p_y + 70, 50, 40), ">")})
                num_v = len(self.nfp_vertices); v_text = f"{self.nfp_current_vertex_idx + 1}/{num_v}" if num_v > 0 else "N/A"
                v_surf = self.font.render(v_text, True, (0, 0, 0)); self.screen.blit(v_surf, v_surf.get_rect(center=(self.nfp_buttons['NEXT_V'].rect.right + 50, self.nfp_buttons['NEXT_V'].rect.centery)))
        for button in self.nfp_buttons.values(): button.draw(self.screen)
        
    def _update_nfp(self):
        if self.nfp_selected_piece_idx is None or not self.nfp_placed_pieces: self.nfp_vertices, self.nfp_draw_polygons, self.nfp_intersection_geoms = [], [], []; return
        original_indices, original_pecas_posicionadas = self.spp_env.indices_pecas_posicionadas, self.spp_env.pecas_posicionadas
        try:
            self.spp_env.indices_pecas_posicionadas = [[p['x'], p['y'], p['grau_idx'], p['pol_idx']] for p in self.nfp_placed_pieces]
            nfp_polygon, nfp_intersec = self.spp_env.nfp(self.nfp_selected_piece_idx, self.nfp_selected_rotation)
            self.nfp_draw_polygons, all_vertices = [], []
            if hasattr(nfp_polygon, 'exterior'):
                exterior_verts = list(nfp_polygon.exterior.coords); self.nfp_draw_polygons.append(exterior_verts); all_vertices.extend(exterior_verts)
                for interior in nfp_polygon.interiors: hole_verts = list(interior.coords); self.nfp_draw_polygons.append(hole_verts); all_vertices.extend(hole_verts)
            self.nfp_intersection_geoms = []
            if nfp_intersec and not nfp_intersec.is_empty:
                all_vertices.extend(extrair_vertices(nfp_intersec))
                if hasattr(nfp_intersec, 'geoms'): self.nfp_intersection_geoms.extend(list(nfp_intersec.geoms))
                else: self.nfp_intersection_geoms.append(nfp_intersec)
            self.nfp_vertices = list(OrderedDict.fromkeys(all_vertices))
        finally:
            self.spp_env.indices_pecas_posicionadas, self.spp_env.pecas_posicionadas = original_indices, original_pecas_posicionadas
        self.nfp_current_vertex_idx = 0

    def _draw_nfp_mode(self):
        self.screen.fill((220, 220, 230)); self._draw_sidebar(scroll_y_attr='nfp_sidebar_scroll_y')
        all_placed_coords = []
        for i, piece_info in enumerate(self.nfp_placed_pieces):
            peca_original = self.spp_env.lista_original[piece_info['pol_idx']]; original_lista = self.spp_env.lista; self.spp_env.lista = [peca_original]
            peca_rotacionada = self.spp_env.rot_pol(0, piece_info['grau_idx']); self.spp_env.lista = original_lista
            peca_final_coords = [(p[0] + piece_info['x'], p[1] + piece_info['y']) for p in peca_rotacionada]
            all_placed_coords.extend(peca_final_coords); screen_coords = self._transform_nfp_coords(peca_final_coords)
            pygame.draw.polygon(self.screen, self.PIECE_COLORS[i % len(self.PIECE_COLORS)], screen_coords); pygame.draw.polygon(self.screen, (50, 50, 50), screen_coords, 2)
        if all_placed_coords:
            min_x, max_x = min(p[0] for p in all_placed_coords), max(p[0] for p in all_placed_coords)
            min_y, max_y = min(p[1] for p in all_placed_coords), max(p[1] for p in all_placed_coords)
            self.nfp_view_center = ((min_x + max_x) / 2, (min_y + max_y) / 2)
        else: self.nfp_view_center = (0, 0)
        if self.nfp_selected_piece_idx is not None and self.nfp_vertices:
            for i, polygon_verts in enumerate(self.nfp_draw_polygons):
                nfp_screen_coords = self._transform_nfp_coords(polygon_verts); color = (255, 0, 255) if i == 0 else (255, 165, 0)
                pygame.draw.polygon(self.screen, color, nfp_screen_coords, 2)
            for geom in self.nfp_intersection_geoms:
                if geom.geom_type in ['Polygon', 'LinearRing']:
                    intersec_coords = self._transform_nfp_coords(list(geom.exterior.coords)); pygame.draw.polygon(self.screen, (0, 255, 255), intersec_coords, 3)
                elif geom.geom_type == 'Point':
                    intersec_coords = self._transform_nfp_coords([(geom.x, geom.y)])[0]; pygame.draw.circle(self.screen, (0, 255, 255), intersec_coords, 6, 3)
            pos = self.nfp_vertices[self.nfp_current_vertex_idx]; peca_rot = self.spp_env.rot_pol(self.nfp_selected_piece_idx, self.nfp_selected_rotation)
            preview_coords = self._transform_nfp_coords(peca_rot, offset=pos); preview_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            pygame.draw.polygon(preview_surface, (170,102,204,180), preview_coords); self.screen.blit(preview_surface, (0,0))
            pygame.draw.circle(self.screen, (200,0,0), self._transform_nfp_coords([pos])[0], 5)
        self._draw_nfp_panel(); self.back_to_menu_button.draw(self.screen)

    def _transform_nfp_coords(self, poly_pts, offset=(0, 0)):
        view_center_x = self.sidebar_width + (self.width - self.sidebar_width) / 2; view_center_y = (self.height - self.panel_height) / 2; scale = 5
        return [(int(view_center_x + (x - self.nfp_view_center[0] + offset[0]) * scale), int(view_center_y - (y - self.nfp_view_center[1] + offset[1]) * scale)) for x, y in poly_pts]

    # --- Métodos para o Modo SPP_SOLVER ---
    def _reset_spp_mode(self):
        self.spp_selected_piece_idx, self.spp_selected_rotation = None, 0
        self.spp_feasible_vertices, self.spp_current_vertex_idx = [], 0
        self.spp_sidebar_scroll_y = 0; self.spp_env.reset()

    def _draw_spp_mode(self):
        self.screen.fill(self.BG_COLOR)
        bin_rect = [(0,0),(self.spp_env.base,0),(self.spp_env.base,self.spp_env.altura),(0,self.spp_env.altura)]
        pygame.draw.polygon(self.screen, self.BIN_COLOR, self._transform_spp_coords(bin_rect), 2)
        for i, peca in enumerate(self.spp_env.pecas_posicionadas):
            pygame.draw.polygon(self.screen, self.PIECE_COLORS[i % len(self.PIECE_COLORS)], self._transform_spp_coords(peca))
            pygame.draw.polygon(self.screen, (50, 50, 50), self._transform_spp_coords(peca), 1)
        self._draw_heuristic_previews(); self._draw_vertex_preview()
        self._draw_sidebar(scroll_y_attr='spp_sidebar_scroll_y')
        self._draw_panel_and_buttons()
        used_width, eff = self.spp_env.get_used_width(), self.spp_env.get_efficiency()
        self.screen.blit(self.font_metrics.render(f"Largura: {used_width:.2f}", True, (0,0,0)), (self.sidebar_width + self.padding, 10))
        self.screen.blit(self.font_metrics.render(f"Eficiência: {eff:.2f}%", True, (0,0,0)), (self.sidebar_width + self.padding, 40))
        self.back_to_menu_button.draw(self.screen)

    def _handle_spp_events(self, events, mouse_pos):
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.back_to_menu_button.is_clicked(mouse_pos): self.mode = 'MENU'; return
                self._handle_spp_clicks(mouse_pos)
            if event.type == pygame.MOUSEWHEEL and mouse_pos[0] < self.sidebar_width:
                self.spp_sidebar_scroll_y -= event.y * 20
                max_scroll = self.spp_sidebar_content_height - self.height
                self.spp_sidebar_scroll_y = max(0, min(self.spp_sidebar_scroll_y, max_scroll if max_scroll > 0 else 0))

    def _handle_spp_clicks(self, mouse_pos):
        buttons = self.spp_buttons
        if buttons['RESET'].is_clicked(mouse_pos): self._reset_spp_mode()
        if buttons['UNDO'].is_clicked(mouse_pos): self.spp_env.remover_ultima_acao(); self._update_feasible_region()
        if buttons['ROT'].is_clicked(mouse_pos) and self.spp_selected_piece_idx is not None: self.spp_selected_rotation = (self.spp_selected_rotation + 1) % 4; self._update_feasible_region()
        
        num_vertices = len(self.spp_feasible_vertices)
        if num_vertices > 0:
            if buttons['NEXT_V'].is_clicked(mouse_pos): self.spp_current_vertex_idx = (self.spp_current_vertex_idx + 1) % num_vertices
            if buttons['PREV_V'].is_clicked(mouse_pos): self.spp_current_vertex_idx = (self.spp_current_vertex_idx - 1 + num_vertices) % num_vertices
            if buttons['PLACE_V'].is_clicked(mouse_pos):
                pos = self.spp_feasible_vertices[self.spp_current_vertex_idx]
                self.spp_env.acao(self.spp_selected_piece_idx, pos[0], pos[1], self.spp_selected_rotation)
                self.spp_selected_piece_idx, self.spp_feasible_vertices = None, []
                return
                
        # --- LÓGICA DE CLIQUE DINÂMICA PARA TODAS AS HEURÍSTICAS ---
        for rule_func in self.spp_env.regras.values():
            rule_name = rule_func.__name__
            if rule_name in buttons and buttons[rule_name].is_clicked(mouse_pos) and self.spp_selected_piece_idx is not None:
                pos = rule_func(self.spp_selected_piece_idx, self.spp_selected_rotation)
                if pos:
                    self.spp_env.acao(self.spp_selected_piece_idx, pos[0], pos[1], self.spp_selected_rotation)
                    self.spp_selected_piece_idx, self.spp_feasible_vertices = None, []
                    return
                    
        for piece_info in self.spp_unique_pieces_view:
            if piece_info.get('rect') and piece_info['rect'].collidepoint(mouse_pos):
                self.spp_selected_piece_idx = piece_info['first_idx']
                self.spp_selected_rotation = 0
                self._update_feasible_region()
                return

    def _calculate_spp_scale(self):
        env_w, env_h = self.spp_env.base, self.spp_env.altura; scale_x = (self.width - self.sidebar_width - 2 * self.padding) / env_w
        scale_y = (self.height - self.panel_height - 2 * self.padding) / env_h; return min(scale_x, scale_y) * 0.98

    def _transform_spp_coords(self, poly_pts, offset=(0, 0)):
        return [(int(self.padding + self.sidebar_width + (x + offset[0]) * self.spp_scale_factor),
                 int(self.height - self.padding - self.panel_height - ((y + offset[1]) * self.spp_scale_factor)))
                for x, y in poly_pts]

    def _update_feasible_region(self):
        if self.spp_selected_piece_idx is not None: self.spp_feasible_vertices = self.spp_env.feasible(self.spp_selected_piece_idx, self.spp_selected_rotation); self.spp_current_vertex_idx = 0
        else: self.spp_feasible_vertices = []

    def _prepare_unique_pieces_view(self):
        counts = OrderedDict()
        for i, peca in enumerate(self.spp_env.lista):
            if not peca: continue
            min_x, min_y = min(p[0] for p in peca), min(p[1] for p in peca)
            norm_peca = tuple(sorted((p[0] - min_x, p[1] - min_y) for p in peca))
            if norm_peca not in counts: counts[norm_peca] = {'count': 0, 'first_idx': i, 'original_peca': peca}
            counts[norm_peca]['count'] += 1
        self.spp_unique_pieces_view = list(counts.values())

    def _draw_sidebar(self, scroll_y_attr):
        self._prepare_unique_pieces_view(); sidebar_area = pygame.Rect(0, 0, self.sidebar_width, self.height)
        pygame.draw.rect(self.screen, self.SIDEBAR_COLOR, sidebar_area); title_surf = self.font.render("Peças Disponíveis", True, (0, 0, 0)); self.screen.blit(title_surf, (10, 10))
        thumb_w, thumb_h, thumb_pad = 120, 90, 10; start_x, start_y = thumb_pad, 50; current_x, current_y = start_x, start_y
        content_rects = []
        for _ in self.spp_unique_pieces_view:
            if current_y + thumb_h > self.height and current_x == start_x: current_y, current_x = start_y, current_x + thumb_w + thumb_pad
            content_rects.append(pygame.Rect(current_x, current_y, thumb_w, thumb_h)); current_y += thumb_h + thumb_pad
        self.spp_sidebar_content_height = current_y; scroll_y = getattr(self, scroll_y_attr)
        for i, piece_info in enumerate(self.spp_unique_pieces_view):
            content_rect = content_rects[i]; screen_rect = content_rect.move(0, -scroll_y)
            if sidebar_area.colliderect(screen_rect):
                peca = piece_info['original_peca']; min_x, min_y = min(p[0] for p in peca), min(p[1] for p in peca)
                norm_peca = [(p[0]-min_x, p[1]-min_y) for p in peca]; max_x, max_y = max(p[0] for p in norm_peca), max(p[1] for p in norm_peca)
                scale = min((thumb_w-thumb_pad)/max(1, max_x), (thumb_h-thumb_pad)/max(1, max_y))
                thumb_coords = [(screen_rect.left+thumb_pad/2+p[0]*scale, screen_rect.top+thumb_pad/2+p[1]*scale) for p in norm_peca]
                piece_info['rect'] = screen_rect; pygame.draw.rect(self.screen, (225, 225, 225), screen_rect, border_radius=3)
                pygame.draw.polygon(self.screen, self.PIECE_COLORS[i % len(self.PIECE_COLORS)], thumb_coords)
                count_surf = self.font_count.render(f"x{piece_info['count']}", True, (0, 0, 0)); self.screen.blit(count_surf, (screen_rect.right - 30, screen_rect.top + 5))
                is_selected = piece_info['first_idx'] == self.spp_selected_piece_idx or piece_info['first_idx'] == self.nfp_selected_piece_idx
                pygame.draw.polygon(self.screen, (255, 0, 0) if is_selected else (50, 50, 50), thumb_coords, 3 if is_selected else 1)
        if self.spp_sidebar_content_height > self.height:
            scrollbar_track = pygame.Rect(self.sidebar_width - 12, 0, 12, self.height); pygame.draw.rect(self.screen, (200, 200, 200), scrollbar_track)
            handle_height = self.height * (self.height / self.spp_sidebar_content_height); handle_height = max(20, handle_height)
            scroll_ratio = scroll_y / (self.spp_sidebar_content_height - self.height); handle_y = (self.height - handle_height) * scroll_ratio
            scrollbar_handle = pygame.Rect(self.sidebar_width - 12, handle_y, 12, handle_height); pygame.draw.rect(self.screen, (130, 130, 130), scrollbar_handle, border_radius=6)
        pygame.draw.line(self.screen, (150, 150, 150), (self.sidebar_width, 0), (self.sidebar_width, self.height), 2)

    def _draw_panel_and_buttons(self):
        panel_rect = pygame.Rect(self.sidebar_width, self.height - self.panel_height, self.width - self.sidebar_width, self.panel_height)
        pygame.draw.rect(self.screen, (220, 220, 220), panel_rect)
        pygame.draw.line(self.screen, (150, 150, 150), (self.sidebar_width, self.height - self.panel_height), (self.width, self.height - self.panel_height), 2)
        
        self.spp_buttons = {}
        mouse_pos = pygame.mouse.get_pos()

        base_x, p_y = self.sidebar_width + 15, self.height - self.panel_height + 5
        btn_w, btn_h, btn_pad_x, btn_pad_y = 90, 35, 10, 5
        
        # self.screen.blit(self.font.render("Direcional (Esq/Dir)", True, (0,0,0)), (base_x, p_y))
        col_x = base_x
        self.spp_buttons['BL'] = Button((col_x, p_y + 25, btn_w, btn_h), "BL"); self.spp_buttons['LB'] = Button((col_x, p_y + 25 + btn_h + btn_pad_y, btn_w, btn_h), "LB")
        self.spp_buttons['BR'] = Button((col_x + btn_w + btn_pad_x, p_y + 25, btn_w, btn_h), "BR"); self.spp_buttons['RB'] = Button((col_x + btn_w + btn_pad_x, p_y + 25 + btn_h + btn_pad_y, btn_w, btn_h), "RB")
        
        col_x = base_x + 2 * (btn_w + btn_pad_x)
        # self.screen.blit(self.font.render("Direcional (Cima/Baixo)", True, (0,0,0)), (col_x, p_y))
        self.spp_buttons['UL'] = Button((col_x, p_y + 25, btn_w, btn_h), "UL"); self.spp_buttons['LU'] = Button((col_x, p_y + 25 + btn_h + btn_pad_y, btn_w, btn_h), "LU")
        self.spp_buttons['UR'] = Button((col_x + btn_w + btn_pad_x, p_y + 25, btn_w, btn_h), "UR"); self.spp_buttons['RU'] = Button((col_x + btn_w + btn_pad_x, p_y + 25 + btn_h + btn_pad_y, btn_w, btn_h), "RU")

        col_x = base_x + 4 * (btn_w + btn_pad_x)
        # self.screen.blit(self.font.render("Encaixe Forçado", True, (0,0,0)), (col_x, p_y))
        self.spp_buttons['BL_NFP'] = Button((col_x, p_y + 25, btn_w, btn_h), "BL_NFP"); self.spp_buttons['LB_NFP'] = Button((col_x, p_y + 25 + btn_h + btn_pad_y, btn_w, btn_h), "LB_NFP")

        col_x = base_x + 5 * (btn_w + btn_pad_x) + 10
        # self.screen.blit(self.font.render("Centralidade", True, (0,0,0)), (col_x, p_y))
        self.spp_buttons['NC'] = Button((col_x, p_y + 25, btn_w+20, 25), "Bin Center", font_size=14); self.spp_buttons['NCG'] = Button((col_x, p_y + 25 + 25 + 5, btn_w+20, 25), "Layout Center", font_size=14)
        self.spp_buttons['NCNFP'] = Button((col_x, p_y + 25 + 2*(25 + 5), btn_w+20, 25), "Feasible Center", font_size=14)

        ctrl_x = self.width - 240
        # self.screen.blit(self.font.render("Controle de Vértices", True, (0,0,0)), (ctrl_x, p_y))
        self.spp_buttons['PLACE_V'] = Button((ctrl_x - 300, p_y + 25, 180, 40), "Posicionar Vértice", bg_color=(170, 102, 204))
        self.spp_buttons['PREV_V'] = Button((ctrl_x - 300, p_y + 70, 50, 40), "<"); self.spp_buttons['NEXT_V'] = Button((ctrl_x -200, p_y + 70, 50, 40), ">")

        self.spp_buttons['ROT'] = Button((self.width - 210, p_y, 190, 40), "Rotacionar")
        self.spp_buttons['UNDO'] = Button((self.width - 210, p_y + 50, 90, 40), "Undo", bg_color=(240, 170, 0))
        self.spp_buttons['RESET'] = Button((self.width - 110, p_y + 50, 90, 40), "Reset", bg_color=(220, 50, 50))
        
        for name, button in self.spp_buttons.items():
            button.draw(self.screen)
            if self.spp_env.regras and name in [r.__name__ for r in self.spp_env.regras.values()] and button.is_clicked(mouse_pos):
                self.spp_hovered_rule_name = name

        num_v = len(self.spp_feasible_vertices); v_text = f"{self.spp_current_vertex_idx + 1}/{num_v}" if num_v > 0 else "N/A"
        v_surf = self.font.render(v_text, True, (0, 0, 0)); text_rect = v_surf.get_rect(center=(self.spp_buttons['NEXT_V'].rect.right + 40, self.spp_buttons['NEXT_V'].rect.centery))
        self.screen.blit(v_surf, text_rect)

    def _draw_heuristic_previews(self):
        if self.spp_selected_piece_idx is None or self.spp_hovered_rule_name is None: return

        rule_method = getattr(self.spp_env, self.spp_hovered_rule_name, None)
        if not rule_method: return
            
        pos = rule_method(self.spp_selected_piece_idx, self.spp_selected_rotation)
        if pos:
            peca_rot = self.spp_env.rot_pol(self.spp_selected_piece_idx, self.spp_selected_rotation)
            preview_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA)
            peca_screen_coords = self._transform_spp_coords(peca_rot, offset=pos)
            
            button_color = self.spp_buttons.get(self.spp_hovered_rule_name).bg_color if self.spp_hovered_rule_name in self.spp_buttons else (150,150,150)
            preview_color = list(button_color) + [128]
            pygame.draw.polygon(preview_surface, preview_color, peca_screen_coords)
            self.screen.blit(preview_surface, (0, 0))

    def _draw_vertex_preview(self):
        if self.spp_selected_piece_idx is not None and self.spp_feasible_vertices:
            pos = self.spp_feasible_vertices[self.spp_current_vertex_idx]; peca_rot = self.spp_env.rot_pol(self.spp_selected_piece_idx, self.spp_selected_rotation)
            preview_surface = pygame.Surface((self.width, self.height), pygame.SRCALPHA); peca_screen_coords = self._transform_spp_coords(peca_rot, offset=pos)
            pygame.draw.polygon(preview_surface, (170, 102, 204, 180), peca_screen_coords); self.screen.blit(preview_surface, (0, 0))
            pos_x, pos_y = self._transform_spp_coords([pos])[0]; pygame.draw.circle(self.screen, (200, 0, 0), (pos_x, pos_y), 5)

if __name__ == '__main__':
    # 1. CRIE A INSTÂNCIA DO SEU AMBIENTE SPP2D
    # Troque o 'dataset' pelo nome da instância que deseja visualizar
    meu_ambiente_spp = SPP2D(dataset='swim', decoder='D1_A', pairwise_IN=True)

    # 2. CRIE A INSTÂNCIA DO VISUALIZADOR, PASSANDO SEU AMBIENTE
    visualizador = Visualizer(spp_env=meu_ambiente_spp, screen_width=1600, screen_height=900)
    
    # 3. EXECUTE O VISUALIZADOR
    visualizador.run()