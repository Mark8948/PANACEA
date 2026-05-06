import customtkinter as ctk
from tkinter import filedialog
import os
import time
from PIL import Image, ImageDraw
from typing import Optional
import matplotlib.pyplot as plt
from gui.visualizer import TreeVisualizer
from gui.palette import PALETTE

import tree_to_prism as tp


class PanaceaApp(ctk.CTk):
    """
    Main application class for the PANACEA Framework GUI.

    This class provides a desktop interface for converting XML files to PRISM models,
    with options for time analysis in R-ADT (Refinement Attack-Defense Trees).
    """

    def __init__(self):
        """
        Initializes the PANACEA GUI application.
        """
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.palette = PALETTE
        
        # --- UI DESIGN METRICS ---
        self.ui_radius = 16      # Main containers, cards, and tabview
        self.inner_radius = 12   # Large inner elements (textbox, primary action buttons)
        self.btn_radius = 8      # Small secondary buttons

        self.title("PANACEA Desktop GUI")
        self.geometry("1500x800")
        self.minsize(1080, 680)
        self.configure(fg_color=self.palette["bg"])

        self.current_xml_path: Optional[str] = None
        self.current_tree = None
        self.displayed_tree = None
        self.icons = self.build_icons()

        self.grid_columnconfigure(0, weight=0)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar = ctk.CTkFrame(
            self,
            width=330,
            corner_radius=0,
            fg_color=self.palette["panel"]
        )
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        self.main_content = ctk.CTkFrame(
            self,
            fg_color="transparent"
        )
        self.main_content.grid(row=0, column=1, padx=24, pady=24, sticky="nsew")
        self.main_content.grid_columnconfigure(0, weight=1)
        self.main_content.grid_rowconfigure(0, weight=1)

        self.setup_sidebar()
        self.setup_tabs()
        self.write_to_console("Interface ready. Import an XML file to start.")

        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def build_icons(self):
        """Builds a dictionary of custom icons used throughout the GUI."""
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
        """Generates a custom icon image based on the specified kind and size."""
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        c = self.palette["text"]
        a = self.palette["accent"]
        w = max(2, size // 10)

        if kind == "upload":
            draw.rounded_rectangle((3, 9, size - 3, size - 4), radius=4, outline=c, width=w)
            draw.rectangle((6, 6, size // 2 + 1, 11), fill=None, outline=c, width=w)
            draw.line((size // 2, 4, size // 2, size - 10), fill=a, width=w)
            draw.polygon(
                [(size // 2, size - 5), (size // 2 - 5, size - 11), (size // 2 + 5, size - 11)],
                fill=a
            )

        elif kind == "generate":
            draw.rounded_rectangle((3, 3, size - 3, size - 3), radius=6, outline=c, width=w)
            draw.polygon(
                [(size * 0.38, size * 0.28), (size * 0.74, size * 0.50), (size * 0.38, size * 0.72)],
                fill=a
            )

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
        """Writes a timestamped message to the console textbox."""
        timestamp = time.strftime("%H:%M:%S")
        clean_text = text.rstrip("\n")

        if not clean_text:
            final_text = "\n"
        elif clean_text.startswith("---"):
            final_text = f"\n{clean_text}\n"
        else:
            final_text = f"[{timestamp}] {clean_text}\n"

        self.textbox.configure(state="normal")
        self.textbox.insert("end", final_text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")

    def clear_console(self):
        """Clears all text from the console textbox and logs the action."""
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.configure(state="disabled")
        self.write_to_console("Console cleared.")

    def clear_file(self):
        """Clears the currently loaded XML file and resets the UI state."""
        self.current_xml_path = None
        self.current_tree = None
        self.displayed_tree = None

        self.visualizer.cleanup()
        self.tree_placeholder.grid()

        self.update_file_ui(False)
        self.write_to_console("[INFO] XML file removed by the user.")

    def update_file_ui(self, is_loaded: bool, file_name: Optional[str] = None):
        """Updates file-related UI elements based on the current load state."""
        if is_loaded and file_name:
            self.file_status_badge.configure(
                text="XML ready",
                fg_color=self.palette["status_ready_bg"],
                text_color=self.palette["status_ready_text"]
            )
            self.file_name_label.configure(
                text=file_name,
                text_color=self.palette["text"]
            )
            self.status_chip.configure(
                text=f"File selected: {file_name}",
                fg_color=self.palette["accent"]
            )
            self.btn_convert.configure(state="normal", fg_color=self.palette["success"])
            self.btn_clear_file.configure(state="normal")
            self.btn_clear_file.grid()
        else:
            self.file_status_badge.configure(
                text="No XML",
                fg_color=self.palette["status_error_bg"],
                text_color=self.palette["status_error_text"]
            )
            self.file_name_label.configure(
                text="Select an XML file from the left column.",
                text_color=self.palette["muted"]
            )
            self.status_chip.configure(
                text="Waiting for XML file",
                fg_color=self.palette["surface"]
            )
            self.btn_convert.configure(state="disabled", fg_color=self.palette["danger"])
            self.btn_clear_file.grid_remove()

    def on_closing(self):
        """Handles the window close event and performs cleanup."""
        self.visualizer.cleanup()
        plt.close('all')
        self.quit()
        self.destroy()

    def setup_sidebar(self):
        """Sets up the sidebar UI components including brand card and controls."""
        self.setup_brand_card()
        self.setup_load_button()
        self.setup_file_card()
        self.setup_time_options_card()
        self.setup_footer()

    def setup_tabs(self):
        """Sets up the tabbed content area holding Home and Tree View sections."""

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
        """Sets up the brand card with the PANACEA title and description."""
        brand_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.palette["card"],
            corner_radius=self.ui_radius,
            border_width=1,
            border_color=self.palette["border"]
        )
        brand_card.pack(fill="x", padx=22, pady=(22, 18))

        ctk.CTkLabel(
            brand_card,
            text="PANACEA",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=self.palette["text"]
        ).pack(anchor="w", padx=20, pady=(18, 4))

        ctk.CTkLabel(
            brand_card,
            text="Desktop framework for XML → PRISM conversion",
            font=ctk.CTkFont(size=14),
            text_color=self.palette["muted"],
            justify="left",
            wraplength=240
        ).pack(anchor="w", padx=20, pady=(0, 18))

    def setup_load_button(self):
        """Sets up the 'Import XML file' button in the sidebar."""
        self.btn_load = ctk.CTkButton(
            self.sidebar,
            text="Import XML file",
            image=self.icons["upload"],
            compound="left",
            anchor="w",
            height=70,
            corner_radius=self.ui_radius,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_hover"],
            text_color=self.palette["text"],
            font=ctk.CTkFont(size=18, weight="bold"),
            command=self.load_xml
        )
        self.btn_load.pack(fill="x", padx=22, pady=(4, 18))

    def setup_file_card(self):
        """Sets up the file status display card showing currently loaded XML data."""
        file_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.palette["card_2"],
            corner_radius=self.ui_radius,
            border_width=1,
            border_color=self.palette["border"]
        )
        file_card.pack(fill="x", padx=22, pady=(0, 18))

        top_file = ctk.CTkFrame(file_card, fg_color="transparent")
        top_file.pack(fill="x", padx=16, pady=(16, 6))
        top_file.grid_columnconfigure(0, weight=1)
        top_file.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(
            top_file,
            text="Loaded file",
            image=self.icons["file"],
            compound="left",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.palette["text"]
        ).grid(row=0, column=0, sticky="w")

        self.btn_clear_file = ctk.CTkButton(
            top_file,
            text="Remove",
            image=self.icons["remove"],
            compound="left",
            width=90,
            height=28,
            corner_radius=self.btn_radius,
            fg_color="transparent",
            hover_color=self.palette["danger"],
            state="disabled",
            command=self.clear_file
        )
        self.btn_clear_file.grid(row=0, column=1, sticky="e", padx=(10, 0))
        self.btn_clear_file.grid_remove()

        self.file_status_badge = ctk.CTkLabel(
            file_card,
            text="No XML",
            fg_color=self.palette["status_error_bg"],
            text_color=self.palette["status_error_text"],
            corner_radius=999, # Manteniamo la forma a pillola per i badge
            padx=10,
            pady=6,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.file_status_badge.pack(anchor="w", padx=16, pady=(0, 8))

        self.file_name_label = ctk.CTkLabel(
            file_card,
            text="Select an XML file from the left column.",
            wraplength=250,
            justify="left",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=14)
        )
        self.file_name_label.pack(anchor="w", padx=16, pady=(0, 16))

    def setup_time_options_card(self):
        """Sets up the time analysis configuration card."""
        time_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.palette["card"],
            corner_radius=self.ui_radius,
            border_width=1,
            border_color=self.palette["border"]
        )
        time_card.pack(fill="x", padx=22, pady=(0, 18))

        ctk.CTkLabel(
            time_card,
            text="Time Analysis",
            image=self.icons["clock"],
            compound="left",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.palette["text"]
        ).pack(anchor="w", padx=16, pady=(16, 6))

        ctk.CTkLabel(
            time_card,
            text="Enable the time variant of generation for R-ADT models.",
            wraplength=250,
            justify="left",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=16, pady=(0, 10))

        self.time_analysis = ctk.CTkCheckBox(
            time_card,
            text="Time Analysis (R-ADT)",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=self.palette["text"],
            border_color=self.palette["accent"],
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_hover"],
            corner_radius=4 # Angoli leggermente smussati per la checkbox
        )
        self.time_analysis.pack(anchor="w", padx=16, pady=(0, 16))

    def setup_footer(self):
        """Sets up the footer label with application metadata."""
        footer = ctk.CTkLabel(
            self.sidebar,
            text="Made by Mark8948 in year 2026",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=12)
        )
        footer.pack(side="bottom", pady=20)

    def setup_home_tab(self):
        """Sets up the Home tab content area including control panels and output console."""
        header = ctk.CTkFrame(self.tab_home, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="Model Control Panel",
            font=ctk.CTkFont(size=30, weight="bold"),
            text_color=self.palette["text"]
        ).grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header,
            text="Quick flow: import XML, choose options, generate PRISM.",
            font=ctk.CTkFont(size=15),
            text_color=self.palette["muted"]
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        hero = ctk.CTkFrame(
            self.tab_home,
            fg_color=self.palette["card"],
            corner_radius=self.ui_radius,
            border_width=1,
            border_color=self.palette["border"]
        )
        hero.grid(row=1, column=0, sticky="ew", pady=(0, 18))
        hero.grid_columnconfigure(0, weight=1)
        hero.grid_columnconfigure(1, weight=0)

        left_hero = ctk.CTkFrame(hero, fg_color="transparent")
        left_hero.grid(row=0, column=0, sticky="nsew", padx=22, pady=22)

        ctk.CTkLabel(
            left_hero,
            text="Model generation",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=self.palette["text"]
        ).pack(anchor="w")

        ctk.CTkLabel(
            left_hero,
            text="The button remains disabled\nuntil you load a valid XML.",
            font=ctk.CTkFont(size=14),
            text_color=self.palette["muted"],
            justify="left"
        ).pack(anchor="w", pady=(6, 14))

        self.status_chip = ctk.CTkLabel(
            left_hero,
            text="Waiting for XML file",
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
            corner_radius=999, # Forma a pillola
            padx=12,
            pady=7,
            font=ctk.CTkFont(size=13, weight="bold")
        )
        self.status_chip.pack(anchor="w")

        self.btn_convert = ctk.CTkButton(
            hero,
            text="Generate PRISM model",
            image=self.icons["generate"],
            compound="left",
            width=300,
            height=70,
            corner_radius=self.inner_radius,
            fg_color=self.palette["danger"],
            hover_color=self.palette["success"],
            text_color=self.palette["text"],
            font=ctk.CTkFont(size=18, weight="bold"),
            state="disabled",
            command=self.run_panacea
        )
        self.btn_convert.grid(row=0, column=1, padx=22, pady=22, sticky="e")

        console_card = ctk.CTkFrame(
            self.tab_home,
            fg_color=self.palette["card_2"],
            corner_radius=self.ui_radius,
            border_width=1,
            border_color=self.palette["border"]
        )
        console_card.grid(row=2, column=0, sticky="nsew")
        console_card.grid_rowconfigure(1, weight=1)
        console_card.grid_columnconfigure(0, weight=1)

        console_top = ctk.CTkFrame(console_card, fg_color="transparent")
        console_top.grid(row=0, column=0, sticky="ew", padx=18, pady=(18, 10))
        console_top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            console_top,
            text="Output Console",
            image=self.icons["log"],
            compound="left",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=self.palette["text"]
        ).grid(row=0, column=0, sticky="w")

        clear_btn = ctk.CTkButton(
            console_top,
            text="Clear log",
            image=self.icons["clear"],
            compound="left",
            width=120,
            height=32,
            corner_radius=self.btn_radius,
            fg_color="transparent",
            hover_color=self.palette["button_hover_secondary"],
            border_width=1,
            border_color=self.palette["border"],
            text_color=self.palette["text"],
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.clear_console
        )
        clear_btn.grid(row=0, column=1, sticky="e")

        self.textbox = ctk.CTkTextbox(
            console_card,
            fg_color=self.palette["log_bg"],
            text_color=self.palette["text"],
            border_width=1,
            border_color=self.palette["border"],
            corner_radius=self.inner_radius,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=14)
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.textbox.configure(state="disabled")

    def setup_tree_view_tab(self):
        """Sets up the Tree View tab content area."""
        self.tab_tree.grid_columnconfigure(0, weight=1)
        self.tab_tree.grid_rowconfigure(0, weight=0)
        self.tab_tree.grid_rowconfigure(1, weight=1)

        instructions = (
            "🖱️ Left Click: Pan view   |   "
            "⚙️ Scroll Wheel: Zoom   |   "
            "🎯 Ctrl + Left Click: Move Node   |   "
            "📋 Right Click: Node Menu"
        )
        self.instruction_label = ctk.CTkLabel(
            self.tab_tree,
            text=instructions,
            font=ctk.CTkFont(size=13),
            text_color=self.palette["muted"]
        )
        self.instruction_label.grid(row=0, column=0, pady=(10, 0), sticky="ew")

        self.graph_container = ctk.CTkFrame(self.tab_tree, fg_color="transparent")
        self.graph_container.grid(row=1, column=0, sticky="nsew")
        self.graph_container.grid_columnconfigure(0, weight=1)
        self.graph_container.grid_rowconfigure(0, weight=1)

        self.tree_placeholder = ctk.CTkLabel(
            self.graph_container,
            text="Please load a valid XML file to visualize the attack-defense tree.",
            font=ctk.CTkFont(size=16),
            text_color=self.palette["muted"]
        )
        self.tree_placeholder.grid(row=0, column=0, padx=20, pady=20)

        self.visualizer = TreeVisualizer(
            self.graph_container,
            on_prune=self._on_context_prune,
            on_reset=self._on_context_reset
        )

    def setup_stats_tab(self):
        """Set up the Statistics tab content area."""
        self.tab_stats.grid_columnconfigure(0, weight=1)
        self.tab_stats.grid_rowconfigure(0, weight=1)

        placeholder = ctk.CTkLabel(
            self.tab_stats,
            text="Statistics and metrics are currently under development.\nComing soon ...",
            font=ctk.CTkFont(size=16),
            text_color=self.palette["muted"]
        )
        placeholder.grid(row=0, column=0, padx=20, pady=20)

    def _on_context_prune(self, node_label: str):
        """Callback invoked when the user selects 'Prune from here' from the context menu."""
        if not self.current_tree:
            self.write_to_console("[WARNING] No tree loaded.")
            return
        try:
            tree_to_prune = self.displayed_tree if self.displayed_tree else self.current_tree
            self.write_to_console(f"[PRUNING] Applying pruning at node: {node_label}")
            pruned_tree = tree_to_prune.prune(node_label)
            self.displayed_tree = pruned_tree
            self.visualizer.draw_tree(pruned_tree)
            self.write_to_console("[SUCCESS] Pruned tree displayed. Right-click again to prune further.")
        except Exception as e:
            self.write_to_console(f"[ERROR] Pruning failed: {str(e)}")

    def _on_context_reset(self):
        """Callback invoked when the user selects 'Reset tree' from the context menu."""
        if not self.current_tree:
            self.write_to_console("[WARNING] No tree loaded.")
            return
        self.displayed_tree = None
        self.write_to_console("[RESET] Displaying original tree...")
        self.visualizer.draw_tree(self.current_tree)
        self.write_to_console("[SUCCESS] Tree reset to original.")

    def load_xml(self):
        """Opens a file dialog to select and load an XML file."""
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])

        if file_path:
            try:
                self.current_xml_path = file_path
                file_name = os.path.basename(file_path)

                self.write_to_console(f"[INFO] XML loaded successfully: {file_name}")
                self.write_to_console("[PARSING] Building tree structure...")
                self.current_tree = tp.parse_file(file_path)
                self.displayed_tree = None

                self.write_to_console("[VISUALIZATION] Rendering tree in Tree View tab...")
            
                self.tree_placeholder.grid_remove()
                self.visualizer.draw_tree(self.current_tree)

                self.update_file_ui(True, file_name)
                self.write_to_console("[SUCCESS] Tree visualization complete.")

            except Exception as e:
                self.write_to_console(f"[ERROR] Failed to load XML: {str(e)}")
                self.current_xml_path = None
                self.current_tree = None
                self.tree_placeholder.grid()
                self.update_file_ui(False)

    def run_panacea(self):
        """Executes the PANACEA conversion process."""
        if not self.current_xml_path:
            return

        use_time = self.time_analysis.get() == 1

        output_path = filedialog.asksaveasfilename(
            defaultextension=".prism",
            filetypes=[("PRISM files", "*.prism")],
            title="Save PRISM model as..."
        )

        if not output_path:
            self.write_to_console("[WARNING] Save operation cancelled.")
            return

        self.write_to_console("--- GENERATION STARTED ---")
        self.write_to_console(f"[PARAM] Time Analysis enabled: {use_time}")

        try:
            self.write_to_console("[1/3] Extracting data from R-ADT tree...")

            if self.displayed_tree:
                tree = self.displayed_tree
                self.write_to_console("[INFO] Using pruned tree for conversion.")
            elif self.current_tree:
                tree = self.current_tree
                self.write_to_console("[INFO] Using original tree from file load.")
            else:
                tree = tp.parse_file(self.current_xml_path)

            self.write_to_console("[2/3] Translating to Stochastic Game...")
            if use_time:
                prism_model = tp.get_prism_model_time(tree)
            else:
                prism_model = tp.get_prism_model(tree)

            self.write_to_console("[3/3] Writing PRISM file...")
            tp.save_prism_model(prism_model, output_path)

            props_path = os.path.join(os.path.dirname(output_path), "properties.props")
            tp.save_prism_properties(props_path)

            self.write_to_console(f"[SUCCESS] Model saved to: {os.path.basename(output_path)}")
            self.write_to_console(f"[SUCCESS] PRISM properties saved to: {os.path.basename(props_path)}")
            self.write_to_console("--- GENERATION COMPLETED ---")

        except Exception as e:
            self.write_to_console(f"[CRITICAL ERROR] Conversion failed: {str(e)}")


if __name__ == "__main__":
    app = PanaceaApp()
    app.mainloop()