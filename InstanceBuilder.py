import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from shapely.geometry import Polygon
import os
import glob
import math

# Configuration
INPUT_DIR = r"C:\Users\felip\Documents\GitHub\RKO\Python\Problems\2DISPP"
DEFAULT_OUTPUT_DIR = r"C:\Users\felip\Documents\GitHub\RKO\Python\Problems\2DISPP"

class InstanceBuilder(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("RKO Instance Builder")
        self.geometry("1400x900")

        self.library_pieces = [] 
        self.current_instance = [] 
        self.source_files = []
        self.global_max_dim = 100.0 # Default fallback

        self._setup_ui()
        self.load_library()

    def _setup_ui(self):
        # Main Layout
        main_pane = ttk.PanedWindow(self, orient=tk.HORIZONTAL)
        main_pane.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # --- LEFT COLUMN (Library) ---
        left_frame = ttk.LabelFrame(main_pane, text="Biblioteca de Peças")
        main_pane.add(left_frame, weight=1)

        # Filter Controls
        filter_frame = ttk.Frame(left_frame)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Arquivo Fonte:").pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="Todos")
        self.filter_combo = ttk.Combobox(filter_frame, textvariable=self.filter_var, state="readonly")
        self.filter_combo.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        self.filter_combo.bind("<<ComboboxSelected>>", self.apply_filter)
        
        ttk.Button(filter_frame, text="Inspecionar Arquivo", command=self.inspect_selected_file).pack(side=tk.LEFT, padx=5)

        # Scrollable Canvas
        self.canvas = tk.Canvas(left_frame)
        scrollbar = ttk.Scrollbar(left_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # --- RIGHT COLUMN (New Instance) ---
        right_frame = ttk.LabelFrame(main_pane, text="Nova Instância")
        main_pane.add(right_frame, weight=1)

        self.tree = ttk.Treeview(right_frame, columns=("Source", "Vertices"), show="headings")
        self.tree.heading("Source", text="Origem")
        self.tree.heading("Vertices", text="Vértices")
        self.tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = ttk.Frame(right_frame)
        btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(btn_frame, text="Remover Selecionado", command=self.remove_item).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Limpar Tudo", command=self.clear_instance).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Salvar Instância (.dat)", command=self.save_instance).pack(side=tk.RIGHT, padx=5)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def load_library(self):
        print(f"Lendo arquivos de: {INPUT_DIR}")
        dat_files = glob.glob(os.path.join(INPUT_DIR, "EB-*.dat"))
        dat_files = [f for f in dat_files if "_buffer" not in os.path.basename(f)]
        
        def sort_key(filepath):
            try:
                name = os.path.basename(filepath)
                num_part = name.replace("EB-", "").replace(".dat", "").replace("_buffer", "")
                return (int(num_part), name)
            except ValueError:
                return (float('inf'), name)
        
        dat_files.sort(key=sort_key)
        self.source_files = ["Todos"] + [os.path.basename(f) for f in dat_files]
        self.filter_combo['values'] = self.source_files
        self.filter_combo.current(0)

        # First Pass: Load all and find Global Max Dimension
        temp_pieces = []
        max_dim = 0.0
        
        unique_id_counter = 0
        seen_geometries = set()

        for filepath in dat_files:
            filename = os.path.basename(filepath)
            try:
                polys = self.read_dat_file(filepath)
                for vertices in polys:
                    geom_sig = str(vertices)
                    if geom_sig in seen_geometries:
                        continue
                    seen_geometries.add(geom_sig)

                    poly = Polygon(vertices)
                    minx, miny, maxx, maxy = poly.bounds
                    w, h = maxx - minx, maxy - miny
                    max_dim = max(max_dim, w, h)

                    piece_data = {
                        'uid': unique_id_counter,
                        'source': filename,
                        'vertices': vertices,
                        'poly': poly
                    }
                    temp_pieces.append(piece_data)
                    unique_id_counter += 1
            except Exception as e:
                print(f"Erro ao ler {filename}: {e}")

        self.global_max_dim = max_dim * 1.1 # Add 10% padding
        print(f"Dimensão Máxima Global calculada: {self.global_max_dim:.2f}")

        self.library_pieces = temp_pieces
        self.apply_filter()

    def apply_filter(self, event=None):
        # Clear current widgets
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()

        selected_file = self.filter_var.get()
        
        for piece in self.library_pieces:
            if selected_file == "Todos" or piece['source'] == selected_file:
                self.add_piece_widget(piece)

    def add_piece_widget(self, piece_data):
        frame = ttk.Frame(self.scrollable_frame, relief="ridge", borderwidth=2)
        frame.pack(fill=tk.X, padx=5, pady=5)

        info_text = f"ID: {piece_data['uid']} | {piece_data['source']}"
        lbl = ttk.Label(frame, text=info_text, width=20)
        lbl.pack(side=tk.LEFT, padx=10)

        # Thumbnail with Global Scale
        fig = plt.Figure(figsize=(2, 2), dpi=50)
        ax = fig.add_subplot(111)
        x, y = piece_data['poly'].exterior.xy
        ax.fill(x, y, alpha=0.5, fc='blue', ec='black')
        
        # Enforce global scale
        ax.set_xlim(0, self.global_max_dim)
        ax.set_ylim(0, self.global_max_dim)
        ax.set_aspect('equal')
        ax.axis('off')
        
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(side=tk.LEFT, padx=10)

        btn = ttk.Button(frame, text="Adicionar", command=lambda p=piece_data: self.prompt_add_piece(p))
        btn.pack(side=tk.RIGHT, padx=10)

    def inspect_selected_file(self):
        selected_file = self.filter_var.get()
        if selected_file == "Todos":
            messagebox.showinfo("Info", "Selecione um arquivo específico para inspecionar.")
            return

        # Filter pieces for this file
        pieces = [p for p in self.library_pieces if p['source'] == selected_file]
        if not pieces:
            return

        top = tk.Toplevel(self)
        top.title(f"Inspeção: {selected_file}")
        top.geometry("1200x800")

        # Scrollable Canvas for Inspection
        canvas = tk.Canvas(top)
        scrollbar = ttk.Scrollbar(top, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)

        scroll_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Grid layout for plots
        cols = 4
        
        for i, piece in enumerate(pieces):
            row = i // cols
            col = i % cols
            
            p_frame = ttk.Frame(scroll_frame, relief="groove", borderwidth=1)
            p_frame.grid(row=row, column=col, padx=5, pady=5)
            
            ttk.Label(p_frame, text=f"ID: {piece['uid']}").pack()
            
            fig = plt.Figure(figsize=(3, 3), dpi=80)
            ax = fig.add_subplot(111)
            x, y = piece['poly'].exterior.xy
            ax.fill(x, y, alpha=0.6, fc='orange', ec='black')
            
            # Use Global Scale
            ax.set_xlim(0, self.global_max_dim)
            ax.set_ylim(0, self.global_max_dim)
            ax.set_aspect('equal')
            ax.grid(True, alpha=0.3)
            
            canv = FigureCanvasTkAgg(fig, master=p_frame)
            canv.draw()
            canv.get_tk_widget().pack()

    def read_dat_file(self, filepath):
        polygons = []
        with open(filepath, 'r') as f:
            content = f.read().strip().split('\n')
            lines = [l.strip() for l in content if l.strip()]
        
        if not lines:
            return []

        try:
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
                    polygons.append(vertices)
                except (ValueError, IndexError):
                    idx += 1
        except ValueError:
            pass
        
        return polygons

    def prompt_add_piece(self, piece_data):
        qty = simpledialog.askinteger("Quantidade", f"Quantas cópias da peça {piece_data['uid']}?", parent=self, minvalue=1, initialvalue=1)
        if qty:
            for _ in range(qty):
                self.add_to_instance(piece_data)

    def add_to_instance(self, piece_data):
        self.current_instance.append(piece_data)
        self.tree.insert("", "end", values=(piece_data['source'], len(piece_data['vertices'])))

    def remove_item(self):
        selected = self.tree.selection()
        for item in selected:
            idx = self.tree.index(item)
            del self.current_instance[idx]
            self.tree.delete(item)

    def clear_instance(self):
        self.current_instance = []
        for item in self.tree.get_children():
            self.tree.delete(item)

    def save_instance(self):
        if not self.current_instance:
            messagebox.showwarning("Aviso", "A instância está vazia!")
            return

        filepath = filedialog.asksaveasfilename(
            initialdir=DEFAULT_OUTPUT_DIR,
            defaultextension=".dat",
            filetypes=[("DAT files", "*.dat"), ("All files", "*.*")]
        )

        if not filepath:
            return

        try:
            with open(filepath, 'w') as f:
                f.write(f"{len(self.current_instance)}\n\n")
                for piece in self.current_instance:
                    verts = piece['vertices']
                    f.write(f"{len(verts)}\n")
                    for x, y in verts:
                        f.write(f"{x:.1f} {y:.1f}\n")
                    f.write("\n")
            
            messagebox.showinfo("Sucesso", f"Instância salva em:\n{filepath}")
        except Exception as e:
            messagebox.showerror("Erro", f"Falha ao salvar: {e}")

if __name__ == "__main__":
    app = InstanceBuilder()
    app.mainloop()
