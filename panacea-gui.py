import customtkinter as ctk
from tkinter import filedialog
import os
import time
import subprocess
import re
import tempfile
import platform
import shutil
from PIL import Image, ImageDraw
from typing import Optional
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from gui.visualizer import TreeVisualizer
from gui.palette import PALETTE
import tree_to_prism as tp

class PanaceaApp(ctk.CTk):
    """
    Main application class for the PANACEA Framework GUI (PRISM-games Edition).
    """

    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.palette = PALETTE
        
        # --- UI DESIGN METRICS ---
        self.ui_radius = 16
        self.inner_radius = 12
        self.btn_radius = 8

        self.title("PANACEA Desktop GUI - PRISM-games Engine")
        self.geometry("1500x800")
        self.minsize(1080, 680)
        self.configure(fg_color=self.palette["bg"])

        self.current_xml_path: Optional[str] = None
        self.current_tree = None
        self.displayed_tree = None
        
        # --- ANALYSIS & STATS TRACKING ---
        self.prism_cmd: Optional[str] = None  # Cached path for PRISM executable
        self.run_history = []                 # List of tuples: (Modification_Label, Value)
        self.pending_modifications = []       # List of actions since last analysis run
        self.tree_modified = False

        self.icons = self.build_icons()
        self.setup_ui_layout()
        self.setup_sidebar()
        self.setup_tabs()
        
        self.write_to_console("System initialized for PRISM-games. Load an XML to begin.")
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_ui_layout(self):
        """Initializes the main grid containers."""
        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=330, corner_radius=0, fg_color=self.palette["panel"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, padx=24, pady=24, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)

    def setup_stats_tab(self):
        """Sets up the Statistics tab with specialized plotting for game verification."""
        self.tab_stats.grid_columnconfigure(0, weight=0)
        self.tab_stats.grid_columnconfigure(1, weight=1)
        self.tab_stats.grid_rowconfigure(0, weight=1)

        # Control Panel
        ctrl_frame = ctk.CTkFrame(self.tab_stats, fg_color="transparent")
        ctrl_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 20), pady=10)

        ctk.CTkLabel(ctrl_frame, text="Optimization History", font=ctk.CTkFont(size=20, weight="bold"), text_color=self.palette["text"]).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(ctrl_frame, text="Execute analysis to track how changes\naffect the security of the model.", font=ctk.CTkFont(size=13), text_color=self.palette["muted"], justify="left").pack(anchor="w", pady=(0, 20))

        self.btn_run_stats = ctk.CTkButton(
            ctrl_frame, text="Run PRISM-games Analysis", 
            image=self.icons["generate"], compound="left", 
            height=50, corner_radius=self.btn_radius,
            fg_color=self.palette["surface"], text_color=self.palette["muted"],
            state="disabled", command=self.run_stats_analysis
        )
        self.btn_run_stats.pack(fill="x", pady=(0, 20))

        self.btn_clear_history = ctk.CTkButton(
            ctrl_frame, text="Reset Plot", 
            image=self.icons["clear"], compound="left",
            height=32, corner_radius=self.btn_radius,
            fg_color="transparent", hover_color=self.palette["danger"],
            border_width=1, border_color=self.palette["border"],
            text_color=self.palette["text"], command=self._clear_stats_history
        )
        self.btn_clear_history.pack(fill="x")

        # Plot Canvas Area
        self.plot_frame = ctk.CTkFrame(self.tab_stats, fg_color=self.palette["card"], corner_radius=self.ui_radius, border_width=1, border_color=self.palette["border"])
        self.plot_frame.grid(row=0, column=1, sticky="nsew", pady=10)

        self.stats_fig = Figure(figsize=(8, 5), dpi=100)
        self.stats_ax = self.stats_fig.add_subplot(111)
        self.stats_fig.patch.set_facecolor(self.palette["card"])
        self.stats_ax.set_facecolor(self.palette["card"])
        
        # Style axes for dark mode
        self.stats_ax.tick_params(colors=self.palette["text"])
        for spine in self.stats_ax.spines.values():
            spine.set_color(self.palette["border"])

        self.stats_canvas = FigureCanvasTkAgg(self.stats_fig, master=self.plot_frame)
        self.stats_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=10)
        self._update_stats_plot()

    def run_stats_analysis(self):
        """Runs the background verification and updates the visual plot."""
        if not self.tree_modified or not self.current_tree:
            return

        self.write_to_console("--- ANALYSIS STARTED (PRISM-games) ---")
        
        # Lock to prevent redundant runs
        self.tree_modified = False
        self._update_stats_button_state()

        tree_to_run = self.displayed_tree if self.displayed_tree else self.current_tree
        use_time = self.time_analysis.get() == 1

        try:
            # Generate PRISM-games compatible models
            prism_model = tp.get_prism_model_time(tree_to_run) if use_time else tp.get_prism_model(tree_to_run)
            
            temp_dir = tempfile.gettempdir()
            temp_prism = os.path.join(temp_dir, "panacea_games.prism")
            temp_props = os.path.join(temp_dir, "panacea_games.props")

            tp.save_prism_model(prism_model, temp_prism)
            tp.save_prism_properties(temp_props)

            # Execution
            result = self._execute_prism(temp_prism, temp_props, silent=True)

            if result is not None:
                # Create a concise label for the X-axis
                if not self.pending_modifications:
                    label = "Base"
                elif len(self.pending_modifications) == 1:
                    label = self.pending_modifications[0]
                else:
                    label = f"{len(self.pending_modifications)} changes"

                run_count = len(self.run_history) + 1
                self.run_history.append((f"Run {run_count}\n({label})", result))
                self.pending_modifications.clear()
                
                self._update_stats_plot()
                self.write_to_console(f"[SUCCESS] Result added to plot: {result}")
            else:
                self.tree_modified = True # Unlock on failure
                self._update_stats_button_state()

        except Exception as e:
            self.write_to_console(f"[CRITICAL] Stats engine error: {str(e)}")
            self.tree_modified = True
            self._update_stats_button_state()

        self.write_to_console("--- ANALYSIS COMPLETED ---")

    def _get_prism_cmd(self) -> Optional[str]:
        """Intelligently locates the PRISM-games executable across OS environments."""
        if self.prism_cmd and os.path.exists(self.prism_cmd):
            return self.prism_cmd
            
        is_windows = platform.system() == "Windows"
        cmd_name = "prism.bat" if is_windows else "prism"
        
        # 1. Search in System PATH
        path_in_env = shutil.which(cmd_name)
        if path_in_env:
            self.prism_cmd = path_in_env
            return self.prism_cmd
            
        # 2. Search in common installation directories
        home = os.path.expanduser("~")
        if is_windows:
            common_paths = [
                r"C:\Program Files\prism-games\bin\prism.bat",
                r"C:\Program Files (x86)\prism-games\bin\prism.bat",
                r"C:\prism-games\bin\prism.bat"
            ]
        else:
            common_paths = [
                "/usr/local/bin/prism",
                "/usr/bin/prism",
                "/opt/prism-games/bin/prism",
                os.path.join(home, "prism-games/bin/prism"),
                os.path.join(home, "prism/bin/prism")
            ]
            
        for p in common_paths:
            if os.path.exists(p) and os.path.isfile(p):
                self.prism_cmd = p
                self.write_to_console(f"[INFO] Auto-located PRISM at: {p}")
                return self.prism_cmd
                
        # 3. Fallback: Ask user via file dialog (saved for the session)
        self.write_to_console(f"[WARNING] '{cmd_name}' not found in PATH or standard folders.")
        self.write_to_console("[INFO] Please locate the PRISM executable manually.")
        
        file_path = filedialog.askopenfilename(
            title=f"Locate PRISM-games executable ({cmd_name})",
            filetypes=[("Batch Files", "*.bat"), ("Executable", "*.exe"), ("All files", "*.*")] if is_windows else [("All files", "*.*")]
        )
        
        if file_path:
            self.prism_cmd = file_path
            self.write_to_console(f"[SUCCESS] PRISM path manually set to: {self.prism_cmd}")
            return self.prism_cmd
            
        self.write_to_console("[ERROR] PRISM executable not provided. Analysis aborted.")
        return None

    def _execute_prism(self, model_path: str, props_path: str, silent: bool = False) -> Optional[float]:
        """Executes the PRISM model checker in a background subprocess."""
        prism_exec = self._get_prism_cmd()
        if not prism_exec:
            return None

        if not silent:
            self.write_to_console("[PROCESS] Launching PRISM-games engine...")
        
        try:
            is_windows = platform.system() == "Windows"
            
            command = [prism_exec, model_path, props_path]
            
            # FIX FONDAMENTALE: Impostiamo la cartella di lavoro (cwd) sulla cartella 'bin' di PRISM.
            # Questo permette a Java di risolvere correttamente i percorsi relativi verso i file .jar
            prism_bin_dir = os.path.dirname(prism_exec)

            process = subprocess.Popen(
                command, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                shell=is_windows,
                cwd=prism_bin_dir  # <--- IL PARAMETRO AGGIUNTO
            )
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                self.write_to_console(f"[ERROR] Engine returned code {process.returncode}:\n{stderr.strip()}")
                return None

            match = re.search(r"Result:\s*([\d\.]+)", stdout)
            
            if match:
                result_value = float(match.group(1))
                if not silent:
                    self.write_to_console("--- ANALYSIS RESULT ---")
                    self.write_to_console(f"Computed Value: {result_value}")
                    self.write_to_console("-----------------------")
                return result_value
            else:
                self.write_to_console("[WARNING] Could not parse the final result from PRISM output.")
                if not silent:
                    self.write_to_console("Check the terminal output structure for verification.")
                return None

        except Exception as e:
            self.write_to_console(f"[CRITICAL] Execution error: {str(e)}")
            return None
        
    def _update_stats_plot(self):
        """Redraws the analysis chart."""
        self.stats_ax.cla()
        self.stats_ax.set_facecolor(self.palette["card"])

        if not self.run_history:
            self.stats_ax.text(0.5, 0.5, "Chart empty. Modify the tree and run analysis.", ha='center', va='center', color=self.palette["muted"])
            self.stats_ax.set_xticks([])
            self.stats_ax.set_yticks([])
            self.stats_fig.subplots_adjust(bottom=0.1)
        else:
            labels = [h[0] for h in self.run_history]
            values = [h[1] for h in self.run_history]
            x = list(range(len(values)))

            self.stats_ax.plot(x, values, marker='o', linewidth=2, color=self.palette["accent"], markersize=8)
            for i, v in enumerate(values):
                self.stats_ax.annotate(f"{v:.2f}", (x[i], values[i]), xytext=(0, 10), textcoords="offset points", ha='center', color=self.palette["text"], weight='bold')

            self.stats_ax.set_title("Cost / Reward Evolution", color=self.palette["text"], fontsize=14, pad=15)
            self.stats_ax.set_ylabel("Computed Result", color=self.palette["text"], fontsize=11)
            
            self.stats_ax.set_xticks(x)
            self.stats_ax.set_xticklabels(labels, fontsize=9, color=self.palette["text"])
            self.stats_fig.subplots_adjust(bottom=0.15 + (0.05 if len(self.run_history) > 4 else 0.0))
            
            y_min, y_max = min(values), max(values)
            y_range = y_max - y_min
            if y_range == 0:
                self.stats_ax.set_ylim(y_min - 10, y_max + 10)
            else:
                self.stats_ax.set_ylim(y_min - y_range * 0.1, y_max + y_range * 0.2)
                
            if len(values) == 1:
                self.stats_ax.set_xlim(-0.5, 0.5)

            self.stats_ax.grid(True, alpha=0.2, linestyle='--', color=self.palette["border"])

        self.stats_canvas.draw()

    # --- TRACKING UPDATES FOR EXISTING METHODS ---

    def _on_context_edit(self, node_label: str):
        if not self.current_tree:
            self.write_to_console("[WARNING] No tree loaded.")
            return

        tree_to_edit = self.displayed_tree if self.displayed_tree else self.current_tree
        node = tree_to_edit.get_node(node_label)
        
        if not node:
            self.write_to_console(f"[ERROR] Node '{node_label}' not found.")
            return

        edit_win = ctk.CTkToplevel(self)
        edit_win.title(f"Node Editor: {node_label}")
        edit_win.geometry("350x300")
        edit_win.configure(fg_color=self.palette["card"])
        edit_win.attributes("-topmost", True)
        edit_win.grab_set()
        edit_win.resizable(False, False)

        ctk.CTkLabel(
            edit_win, 
            text=f"Parameters for: {node_label}", 
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.palette["text"]
        ).pack(pady=(20, 20))

        cost_frame = ctk.CTkFrame(edit_win, fg_color="transparent")
        cost_frame.pack(fill="x", padx=40, pady=10)
        ctk.CTkLabel(cost_frame, text="Cost:", font=ctk.CTkFont(size=15)).pack(side="left")
        cost_entry = ctk.CTkEntry(cost_frame, width=120)
        cost_entry.pack(side="right")
        cost_entry.insert(0, str(node.cost))

        time_frame = ctk.CTkFrame(edit_win, fg_color="transparent")
        time_frame.pack(fill="x", padx=40, pady=10)
        ctk.CTkLabel(time_frame, text="Time:", font=ctk.CTkFont(size=15)).pack(side="left")
        time_entry = ctk.CTkEntry(time_frame, width=120)
        time_entry.pack(side="right")
        time_entry.insert(0, str(node.time))

        def save_changes():
            new_cost = cost_entry.get().strip()
            new_time = time_entry.get().strip()
            
            node.cost = new_cost
            node.time = new_time
            
            self.write_to_console(f"[EDIT] Node '{node_label}' -> Cost: {new_cost} | Time: {new_time}")
            
            self.pending_modifications.append(f"Edit: {node_label}")
            self.tree_modified = True
            self._update_stats_button_state()
            
            edit_win.grab_release()
            edit_win.destroy()

        ctk.CTkButton(
            edit_win, 
            text="Save Changes", 
            fg_color=self.palette["success"],
            hover_color="#1E8449",
            font=ctk.CTkFont(size=15, weight="bold"),
            command=save_changes
        ).pack(pady=(30, 10))

    def _on_context_prune(self, node_label: str):
        if not self.current_tree:
            self.write_to_console("[WARNING] No tree loaded.")
            return
        try:
            tree_to_prune = self.displayed_tree if self.displayed_tree else self.current_tree
            self.write_to_console(f"[PRUNING] Applying pruning at node: {node_label}")
            pruned_tree = tree_to_prune.prune(node_label)
            self.displayed_tree = pruned_tree
            self.visualizer.draw_tree(pruned_tree)
            
            self.pending_modifications.append(f"Prune: {node_label}")
            self.tree_modified = True
            self._update_stats_button_state()
            
            self.write_to_console("[SUCCESS] Pruned tree displayed. Right-click again to prune further.")
        except Exception as e:
            self.write_to_console(f"[ERROR] Pruning failed: {str(e)}")

    def _update_stats_button_state(self):
        if self.current_tree and self.tree_modified:
            self.btn_run_stats.configure(state="normal", fg_color=self.palette["success"], text_color="#FFFFFF")
        else:
            self.btn_run_stats.configure(state="disabled", fg_color=self.palette["surface"], text_color=self.palette["muted"])

    def _clear_stats_history(self):
        self.run_history.clear()
        self.pending_modifications.clear()
        self._update_stats_plot()
        self.write_to_console("[STATS] Plot history cleared.")
        self._update_stats_button_state()

    def load_xml(self):
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
        if file_path:
            try:
                self.current_xml_path = file_path
                file_name = os.path.basename(file_path)
                self.write_to_console(f"[INFO] XML loaded successfully: {file_name}")
                self.current_tree = tp.parse_file(file_path)
                self.displayed_tree = None
                self.tree_placeholder.grid_remove()
                self.visualizer.draw_tree(self.current_tree)
                self.update_file_ui(True, file_name)
                
                self.pending_modifications = ["Initial Load"]
                self.tree_modified = True
                self._update_stats_button_state()
                
            except Exception as e:
                self.write_to_console(f"[ERROR] Failed to load XML: {str(e)}")
                self.current_xml_path = None
                self.current_tree = None
                self.tree_placeholder.grid()
                self.update_file_ui(False)

    def _on_context_reset(self):
        if not self.current_tree: return
        self.displayed_tree = None
        self.visualizer.draw_tree(self.current_tree)
        self.pending_modifications.append("Reset to Original")
        self.tree_modified = True
        self._update_stats_button_state()

    def run_panacea(self):
        if not self.current_xml_path: return
        use_time = self.time_analysis.get() == 1
        output_path = filedialog.asksaveasfilename(defaultextension=".prism", filetypes=[("PRISM files", "*.prism")])
        if not output_path: return

        try:
            tree = self.displayed_tree if self.displayed_tree else self.current_tree
            prism_model = tp.get_prism_model_time(tree) if use_time else tp.get_prism_model(tree)
            tp.save_prism_model(prism_model, output_path)
            props_path = os.path.join(os.path.dirname(output_path), "properties.props")
            tp.save_prism_properties(props_path)
            self.write_to_console(f"[SUCCESS] Saved to {output_path}")
            self._execute_prism(output_path, props_path)
        except Exception as e:
            self.write_to_console(f"[ERROR] Conversion failed: {str(e)}")

    # ... [Helper methods for UI (build_icons, write_to_console, clear_file, ecc.) rimangono invariati come prima] ...
    
    def build_icons(self):
        return {
            "upload": self.make_icon("upload", 28),
            "generate": self.make_icon("generate", 28),
            "file": self.make_icon("file", 22),
            "log": self.make_icon("log", 22),
            "clear": self.make_icon("clear", 20),
            "clock": self.make_icon("clock", 20),
            "remove": self.make_icon("remove", 20),
        }

    def make_icon(self, kind, size=24):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        c = self.palette["text"]
        a = self.palette["accent"]
        w = max(2, size // 10)

        if kind == "upload":
            draw.rounded_rectangle((3, 9, size - 3, size - 4), radius=4, outline=c, width=w)
            draw.rectangle((6, 6, size // 2 + 1, 11), fill=None, outline=c, width=w)
            draw.line((size // 2, 4, size // 2, size - 10), fill=a, width=w)
            draw.polygon([(size // 2, size - 5), (size // 2 - 5, size - 11), (size // 2 + 5, size - 11)], fill=a)
        elif kind == "generate":
            draw.rounded_rectangle((3, 3, size - 3, size - 3), radius=6, outline=c, width=w)
            draw.polygon([(size * 0.38, size * 0.28), (size * 0.74, size * 0.50), (size * 0.38, size * 0.72)], fill=a)
        elif kind == "file":
            draw.rounded_rectangle((4, 3, size - 5, size - 3), radius=4, outline=c, width=w)
            draw.line((size - 10, 3, size - 10, 10), fill=c, width=w)
            draw.line((size - 10, 10, size - 4, 10), fill=c, width=w)
        elif kind == "log":
            draw.rounded_rectangle((3, 3, size - 3, size - 3), radius=5, outline=c, width=w)
            draw.line((6, 8, size - 6, 8), fill=a, width=w)
            draw.line((6, 12, size - 10, 12), fill=c, width=w)
            draw.line((6, 16, size - 7, 16), fill=c, width=w)
        elif kind == "clear":
            draw.rectangle((7, 8, size - 7, size - 5), outline=c, width=w)
            draw.line((6, 8, size - 6, 8), fill=a, width=w)
            draw.line((9, 5, size - 9, 5), fill=c, width=w)
            draw.line((10, 11, 10, size - 8), fill=c, width=w)
            draw.line((size // 2, 11, size // 2, size - 8), fill=c, width=w)
            draw.line((size - 10, 11, size - 10, size - 8), fill=c, width=w)
        elif kind == "clock":
            draw.ellipse((3, 3, size - 3, size - 3), outline=c, width=w)
            draw.line((size // 2, size // 2, size // 2, 7), fill=a, width=w)
            draw.line((size // 2, size // 2, size - 8, size // 2 + 3), fill=a, width=w)
        elif kind == "remove":
            draw.line((6, 6, size - 6, size - 6), fill=self.palette["danger"], width=w)
            draw.line((size - 6, 6, 6, size - 6), fill=self.palette["danger"], width=w)

        return ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))

    def write_to_console(self, text):
        timestamp = time.strftime("%H:%M:%S")
        clean_text = text.rstrip("\n")
        final_text = f"\n{clean_text}\n" if clean_text.startswith("---") else f"[{timestamp}] {clean_text}\n" if clean_text else "\n"
        self.textbox.configure(state="normal")
        self.textbox.insert("end", final_text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear_console(self):
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.configure(state="disabled")
        self.write_to_console("Console cleared.")

    def clear_file(self):
        self.current_xml_path = None
        self.current_tree = None
        self.displayed_tree = None
        self.tree_modified = False
        self.pending_modifications.clear()
        self.visualizer.cleanup()
        self.tree_placeholder.grid()
        self.update_file_ui(False)
        self._update_stats_button_state()
        self.write_to_console("[INFO] XML file removed by the user.")

    def update_file_ui(self, is_loaded: bool, file_name: Optional[str] = None):
        if is_loaded and file_name:
            self.file_status_badge.configure(text="XML ready", fg_color=self.palette["status_ready_bg"], text_color=self.palette["status_ready_text"])
            self.file_name_label.configure(text=file_name, text_color=self.palette["text"])
            self.status_chip.configure(text=f"File selected: {file_name}", fg_color=self.palette["accent"])
            self.btn_convert.configure(state="normal", fg_color=self.palette["success"])
            self.btn_clear_file.configure(state="normal")
            self.btn_clear_file.grid()
        else:
            self.file_status_badge.configure(text="No XML", fg_color=self.palette["status_error_bg"], text_color=self.palette["status_error_text"])
            self.file_name_label.configure(text="Select an XML file from the left column.", text_color=self.palette["muted"])
            self.status_chip.configure(text="Waiting for XML file", fg_color=self.palette["surface"])
            self.btn_convert.configure(state="disabled", fg_color=self.palette["danger"])
            self.btn_clear_file.grid_remove()

    def on_closing(self):
        self.visualizer.cleanup()
        plt.close('all')
        self.quit()
        self.destroy()

    def setup_sidebar(self):
        self.setup_brand_card()
        self.setup_load_button()
        self.setup_file_card()
        self.setup_time_options_card()
        self.setup_footer()

    def setup_tabs(self):
        self.tabview = ctk.CTkTabview(self.main_content, corner_radius=self.ui_radius)
        self.tabview.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        self.tab_home = self.tabview.add("Home")
        self.tab_tree = self.tabview.add("Tree View")
        self.tab_stats = self.tabview.add("Statistics")
        self.tab_home.grid_columnconfigure(0, weight=1)
        self.tab_home.grid_rowconfigure(2, weight=1)
        self.setup_home_tab()
        self.setup_tree_view_tab()
        self.setup_stats_tab()

    def setup_brand_card(self):
        brand_card = ctk.CTkFrame(self.sidebar, fg_color=self.palette["card"], corner_radius=self.ui_radius, border_width=1, border_color=self.palette["border"])
        brand_card.pack(fill="x", padx=22, pady=(22, 18))
        ctk.CTkLabel(brand_card, text="PANACEA", font=ctk.CTkFont(size=30, weight="bold"), text_color=self.palette["text"]).pack(anchor="w", padx=20, pady=(18, 4))
        ctk.CTkLabel(brand_card, text="Desktop framework for XML → PRISM conversion", font=ctk.CTkFont(size=14), text_color=self.palette["muted"], justify="left", wraplength=240).pack(anchor="w", padx=20, pady=(0, 18))

    def setup_load_button(self):
        self.btn_load = ctk.CTkButton(self.sidebar, text="Import XML file", image=self.icons["upload"], compound="left", anchor="w", height=70, corner_radius=self.ui_radius, fg_color=self.palette["accent"], hover_color=self.palette["accent_hover"], text_color=self.palette["text"], font=ctk.CTkFont(size=18, weight="bold"), command=self.load_xml)
        self.btn_load.pack(fill="x", padx=22, pady=(4, 18))

    def setup_file_card(self):
        file_card = ctk.CTkFrame(self.sidebar, fg_color=self.palette["card_2"], corner_radius=self.ui_radius, border_width=1, border_color=self.palette["border"])
        file_card.pack(fill="x", padx=22, pady=(0, 18))
        top_file = ctk.CTkFrame(file_card, fg_color="transparent")
        top_file.pack(fill="x", padx=16, pady=(16, 6))
        top_file.grid_columnconfigure(0, weight=1)
        top_file.grid_columnconfigure(1, weight=0)
        ctk.CTkLabel(top_file, text="Loaded file", image=self.icons["file"], compound="left", font=ctk.CTkFont(size=15, weight="bold"), text_color=self.palette["text"]).grid(row=0, column=0, sticky="w")
        self.btn_clear_file = ctk.CTkButton(top_file, text="Remove", image=self.icons["remove"], compound="left", width=90, height=28, corner_radius=self.btn_radius, fg_color="transparent", hover_color=self.palette["danger"], state="disabled", command=self.clear_file)
        self.btn_clear_file.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self.btn_clear_file.grid_remove()
        self.file_status_badge = ctk.CTkLabel(file_card, text="No XML", fg_color=self.palette["status_error_bg"], text_color=self.palette["status_error_text"], corner_radius=999, padx=10, pady=6, font=ctk.CTkFont(size=12, weight="bold"))
        self.file_status_badge.pack(anchor="w", padx=16, pady=(0, 8))
        self.file_name_label = ctk.CTkLabel(file_card, text="Select an XML file from the left column.", wraplength=250, justify="left", text_color=self.palette["muted"], font=ctk.CTkFont(size=14))
        self.file_name_label.pack(anchor="w", padx=16, pady=(0, 16))

    def setup_time_options_card(self):
        time_card = ctk.CTkFrame(self.sidebar, fg_color=self.palette["card"], corner_radius=self.ui_radius, border_width=1, border_color=self.palette["border"])
        time_card.pack(fill="x", padx=22, pady=(0, 18))
        ctk.CTkLabel(time_card, text="Time Analysis", image=self.icons["clock"], compound="left", font=ctk.CTkFont(size=15, weight="bold"), text_color=self.palette["text"]).pack(anchor="w", padx=16, pady=(16, 6))
        ctk.CTkLabel(time_card, text="Enable the time variant of generation for R-ADT models.", wraplength=250, justify="left", text_color=self.palette["muted"], font=ctk.CTkFont(size=13)).pack(anchor="w", padx=16, pady=(0, 10))
        self.time_analysis = ctk.CTkCheckBox(time_card, text="Time Analysis (R-ADT)", font=ctk.CTkFont(size=14, weight="bold"), text_color=self.palette["text"], border_color=self.palette["accent"], fg_color=self.palette["accent"], hover_color=self.palette["accent_hover"], corner_radius=4)
        self.time_analysis.pack(anchor="w", padx=16, pady=(0, 16))

    def setup_footer(self):
        footer = ctk.CTkLabel(self.sidebar, text="Made by Mark8948 in year 2026", text_color=self.palette["muted"], font=ctk.CTkFont(size=12))
        footer.pack(side="bottom", pady=20)

    def setup_home_tab(self):
        header = ctk.CTkFrame(self.tab_home, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(header, text="Model Control Panel", font=ctk.CTkFont(size=30, weight="bold"), text_color=self.palette["text"]).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="Quick flow: import XML, choose options, generate PRISM.", font=ctk.CTkFont(size=15), text_color=self.palette["muted"]).grid(row=1, column=0, sticky="w", pady=(4, 0))
        hero = ctk.CTkFrame(self.tab_home, fg_color=self.palette["card"], corner_radius=self.ui_radius, border_width=1, border_color=self.palette["border"])
        hero.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)
        left_hero = ctk.CTkFrame(hero, fg_color="transparent")
        left_hero.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)
        ctk.CTkLabel(left_hero, text="Model generation", font=ctk.CTkFont(size=20, weight="bold"), text_color=self.palette["text"]).pack(anchor="w")
        ctk.CTkLabel(left_hero, text="The button remains disabled\nuntil you load a valid XML.", font=ctk.CTkFont(size=14), text_color=self.palette["muted"], justify="left").pack(anchor="w", pady=(6, 14))
        self.status_chip = ctk.CTkLabel(left_hero, text="Waiting for XML file", fg_color=self.palette["surface"], text_color=self.palette["text"], corner_radius=999, padx=12, pady=7, font=ctk.CTkFont(size=13, weight="bold"))
        self.status_chip.pack(anchor="w")
        self.btn_convert = ctk.CTkButton(hero, text="Generate PRISM model", image=self.icons["generate"], compound="left", width=300, height=70, corner_radius=self.inner_radius, fg_color=self.palette["danger"], hover_color=self.palette["success"], text_color=self.palette["text"], font=ctk.CTkFont(size=18, weight="bold"), state="disabled", command=self.run_panacea)
        self.btn_convert.grid(row=0, column=1, padx=22, pady=22, sticky="e")
        console_card = ctk.CTkFrame(self.tab_home, fg_color=self.palette["card_2"], corner_radius=self.ui_radius, border_width=1, border_color=self.palette["border"])
        console_card.grid(row=2, column=0, sticky="nsew")
        console_card.grid_rowconfigure(1, weight=1)
        console_card.grid_columnconfigure(0, weight=1)
        console_top = ctk.CTkFrame(console_card, fg_color="transparent")
        console_top.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        console_top.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(console_top, text="Output Console", image=self.icons["log"], compound="left", font=ctk.CTkFont(size=18, weight="bold"), text_color=self.palette["text"]).grid(row=0, column=0, sticky="w")
        clear_btn = ctk.CTkButton(console_top, text="Clear log", image=self.icons["clear"], compound="left", width=120, height=32, corner_radius=self.btn_radius, fg_color="transparent", hover_color=self.palette["button_hover_secondary"], border_width=1, border_color=self.palette["border"], text_color=self.palette["text"], font=ctk.CTkFont(size=13, weight="bold"), command=self.clear_console)
        clear_btn.grid(row=0, column=1, sticky="e")
        self.textbox = ctk.CTkTextbox(console_card, fg_color=self.palette["log_bg"], text_color=self.palette["text"], border_width=1, border_color=self.palette["border"], corner_radius=self.inner_radius, wrap="word", font=ctk.CTkFont(family="Consolas", size=14))
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.textbox.configure(state="disabled")

    def setup_tree_view_tab(self):
        self.tab_tree.grid_columnconfigure(0, weight=1)
        self.tab_tree.grid_rowconfigure(0, weight=0)
        self.tab_tree.grid_rowconfigure(1, weight=1)
        instructions = "🖱️ Left Click: Pan view   |   ⚙️ Scroll Wheel: Zoom   |   🎯 Ctrl + Left Click: Move Node   |   📋 Right Click: Node Menu"
        self.instruction_label = ctk.CTkLabel(self.tab_tree, text=instructions, font=ctk.CTkFont(size=13), text_color=self.palette["muted"])
        self.instruction_label.grid(row=0, column=0, pady=(10, 0), sticky="ew")
        self.graph_container = ctk.CTkFrame(self.tab_tree, fg_color="transparent")
        self.graph_container.grid(row=1, column=0, sticky="nsew")
        self.graph_container.grid_columnconfigure(0, weight=1)
        self.graph_container.grid_rowconfigure(0, weight=1)
        self.tree_placeholder = ctk.CTkLabel(self.graph_container, text="Please load a valid XML file to visualize the attack-defense tree.", font=ctk.CTkFont(size=16), text_color=self.palette["muted"])
        self.tree_placeholder.grid(row=0, column=0, padx=20, pady=20)
        self.visualizer = TreeVisualizer(self.graph_container, on_prune=self._on_context_prune, on_reset=self._on_context_reset, on_edit=self._on_context_edit)

if __name__ == "__main__":
    app = PanaceaApp()
    app.mainloop()