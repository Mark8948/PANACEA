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
        Initialize the PANACEA GUI application.

        Sets up the main window, color palette, icons, and UI components including
        sidebar, tabbed content areas (Home, Tree View, Statistics), and visualization.
        Initializes the tree visualizer and configures the initial state and console output.
        """
        super().__init__()

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.palette = PALETTE

        self.title("PANACEA Desktop GUI")
        self.geometry("1500x800")
        self.minsize(1080, 680)
        self.configure(fg_color=self.palette["bg"])

        self.current_xml_path: Optional[str] = None
        self.current_tree = None
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

        # Handle window close event
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

    def build_icons(self):
        """
        Build and return a dictionary of custom icons used in the GUI.

        Creates CTkImage objects for various UI elements like upload, generate, file, etc.
        Each icon is generated programmatically using PIL.

        Returns:
            dict: A dictionary mapping icon names (str) to CTkImage objects.
        """
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
        """
        Generate a custom icon image based on the specified kind and size.

        Uses PIL to draw vector-style icons programmatically. Supports various icon types
        like upload, generate, file, log, clear, and clock.

        Args:
            kind (str): The type of icon to generate (e.g., "upload", "generate").
            size (int, optional): The size of the icon in pixels. Defaults to 24.

        Returns:
            CTkImage: A CustomTkinter image object ready for use in widgets.
        """
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
        """
        Write a timestamped message to the console textbox.

        Formats the input text with a timestamp and special handling for separator lines
        (starting with "---"). Updates the UI to show the new text and scroll to the end.

        Args:
            text (str): The message to write to the console.
        """
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
        """
        Clear all text from the console textbox and log the action.

        Resets the console to an empty state and writes a confirmation message.
        """
        self.textbox.configure(state="normal")
        self.textbox.delete("0.0", "end")
        self.textbox.configure(state="disabled")
        self.write_to_console("Console cleared.")

    def clear_file(self):
        """
        Clear the currently loaded XML file.

        Resets the file status, disables the convert button, and updates the UI.
        """
        self.current_xml_path = None

        self.update_file_ui(False)

        self.write_to_console("[INFO] XML file removed by the user.")

    def update_file_ui(self, is_loaded: bool, file_name: str = None):
        """
        Update the file-related UI elements based on whether a file is loaded.

        Args:
            is_loaded (bool): True if a file is loaded, False otherwise.
            file_name (str, optional): The name of the loaded file, required if is_loaded is True.
        """
        if is_loaded and file_name:
            self.file_status_badge.configure(
                text="XML ready",
                fg_color="#1E3B32",
                text_color="#A8F0D2"
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
                fg_color="#3A2A2A",
                text_color="#FFB4B4"
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
        """
        Handle the window close event.

        Properly terminates the application when the user closes the window.
        Cleans up Matplotlib resources and callbacks before destroying the window.
        """
        self.visualizer.cleanup()
        plt.close('all')
        self.quit()
        self.destroy()

    def setup_sidebar(self):
        """
        Set up the sidebar UI components.

        Creates and configures the brand card, load button, file status display,
        options cards with time analysis and pruning options, and footer label.
        """
        self.setup_brand_card()
        self.setup_load_button()
        self.setup_file_card()
        self.setup_time_options_card()
        self.setup_prune_options_card()
        self.setup_footer()

    def setup_tabs(self):
        """
        Set up the tabbed content area with three main sections.

        Creates a CTkTabview with three tabs: Home (main flow), Tree View (visualization),
        and Statistics. Initializes the tree visualizer for the Tree View tab and
        configures each tab for proper layout and functionality.
        """
        self.tabview = ctk.CTkTabview(self.main_content)
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
        """Set up the brand card with PANACEA title and description."""
        brand_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.palette["card"],
            corner_radius=24,
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
            justify="left"
        ).pack(anchor="w", padx=20, pady=(0, 18))

    def setup_load_button(self):
        """Set up the load XML button."""
        self.btn_load = ctk.CTkButton(
            self.sidebar,
            text="Import XML file",
            image=self.icons["upload"],
            compound="left",
            anchor="w",
            height=76,
            corner_radius=22,
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_hover"],
            text_color=self.palette["text"],
            font=ctk.CTkFont(size=20, weight="bold"),
            command=self.load_xml
        )
        self.btn_load.pack(fill="x", padx=22, pady=(4, 18))

    def setup_file_card(self):
        """Set up the file status display card."""
        file_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.palette["card_2"],
            corner_radius=22,
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
            width=100,
            height=30,
            corner_radius=8,
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
            fg_color="#3A2A2A",
            text_color="#FFB4B4",
            corner_radius=999,
            padx=10,
            pady=6,
            font=ctk.CTkFont(size=12, weight="bold")
        )
        self.file_status_badge.pack(anchor="w", padx=16, pady=(0, 8))

        self.file_name_label = ctk.CTkLabel(
            file_card,
            text="Select an XML file from the left column.",
            wraplength=260,
            justify="left",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=14)
        )
        self.file_name_label.pack(anchor="w", padx=16, pady=(0, 16))

    def setup_time_options_card(self):
        """Set up the time analysis options card."""
        time_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.palette["card"],
            corner_radius=22,
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
            wraplength=260,
            justify="left",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=16, pady=(0, 10))

        self.time_analysis = ctk.CTkCheckBox(
            time_card,
            text="Time Analysis (R-ADT)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.palette["text"],
            border_color=self.palette["accent"],
            fg_color=self.palette["accent"],
            hover_color=self.palette["accent_hover"]
        )
        self.time_analysis.pack(anchor="w", padx=16, pady=(0, 16))

    def setup_prune_options_card(self):
        """Set up the pruning options card."""
        prune_card = ctk.CTkFrame(
            self.sidebar,
            fg_color=self.palette["card"],
            corner_radius=22,
            border_width=1,
            border_color=self.palette["border"]
        )
        prune_card.pack(fill="x", padx=22, pady=(0, 18))

        ctk.CTkLabel(
            prune_card,
            text="Pruning Options",
            image=self.icons["remove"],
            compound="left",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=self.palette["text"]
        ).pack(anchor="w", padx=16, pady=(16, 6))

        ctk.CTkLabel(
            prune_card,
            text="Optionally prune the tree at a specific node label to focus on a subtree.",
            wraplength=260,
            justify="left",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=13)
        ).pack(anchor="w", padx=16, pady=(0, 10))

        ctk.CTkLabel(
            prune_card,
            text="Prune Label (optional):",
            font=ctk.CTkFont(size=14),
            text_color=self.palette["muted"]
        ).pack(anchor="w", padx=16, pady=(0, 5))

        self.prune_entry = ctk.CTkEntry(
            prune_card,
            placeholder_text="Enter node label to prune",
            font=ctk.CTkFont(size=14),
            fg_color=self.palette["surface"],
            border_color=self.palette["border"],
            text_color=self.palette["text"]
        )
        self.prune_entry.pack(fill="x", padx=16, pady=(0, 16))

    def setup_footer(self):
        """Set up the footer label."""
        footer = ctk.CTkLabel(
            self.sidebar,
            text="Made by Mark8948 in year 2026",
            text_color=self.palette["muted"],
            font=ctk.CTkFont(size=12)
        )
        footer.pack(side="bottom", pady=20)

    def setup_home_tab(self):
        """
        Set up the Home tab content area.

        Creates the header, hero section with generation button, and console area
        with output textbox and clear button. This is the main workflow tab for
        converting XML files to PRISM models.
        """
        header = ctk.CTkFrame(
            self.tab_home,
            fg_color="transparent"
        )
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
            corner_radius=26,
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
            text_color=self.palette["muted"]
        ).pack(anchor="w", pady=(6, 14))

        self.status_chip = ctk.CTkLabel(
            left_hero,
            text="Waiting for XML file",
            fg_color=self.palette["surface"],
            text_color=self.palette["text"],
            corner_radius=999,
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
            width=340,
            height=86,
            corner_radius=24,
            fg_color=self.palette["danger"],
            hover_color=self.palette["success"],
            text_color=self.palette["text"],
            font=ctk.CTkFont(size=22, weight="bold"),
            state="disabled",
            command=self.run_panacea
        )
        self.btn_convert.grid(row=0, column=1, padx=22, pady=22, sticky="e")
        self.btn_convert.configure(text_color=self.palette["text"])

        console_card = ctk.CTkFrame(
            self.tab_home,
            fg_color=self.palette["card_2"],
            corner_radius=26,
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
            width=145,
            height=42,
            corner_radius=14,
            fg_color="transparent",
            hover_color="#2A3A4E",
            border_width=1,
            border_color=self.palette["border"],
            text_color=self.palette["text"],
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.clear_console
        )
        clear_btn.grid(row=0, column=1, sticky="e")

        self.textbox = ctk.CTkTextbox(
            console_card,
            fg_color=self.palette["log_bg"],
            text_color=self.palette["text"],
            border_width=1,
            border_color=self.palette["border"],
            corner_radius=20,
            wrap="word",
            font=ctk.CTkFont(family="Consolas", size=14)
        )
        self.textbox.grid(row=1, column=0, sticky="nsew", padx=18, pady=(0, 18))
        self.textbox.configure(state="disabled")

    def setup_tree_view_tab(self):
        """
        Set up the Tree View tab content area.

        Initializes the TreeVisualizer component to display the hierarchical structure
        of the loaded attack-defense tree with node coloring based on player roles.
        """
        self.visualizer = TreeVisualizer(self.tab_tree)

    def setup_stats_tab(self):
        """
        Set up the Statistics tab content area.

        Reserved for future statistical analysis and metrics visualization of the model.
        Currently provides a placeholder for extending the application.
        """
        self.tab_stats.grid_columnconfigure(0, weight=1)
        self.tab_stats.grid_rowconfigure(0, weight=1)
        
        placeholder = ctk.CTkLabel(
            self.tab_stats,
            text="Statistics and metrics are currently under development.\nComing soon ...",
            font=ctk.CTkFont(size=16),
            text_color=self.palette["muted"]
        )
        placeholder.grid(row=0, column=0, padx=20, pady=20)

    def load_xml(self):
        """
        Open a file dialog to select and load an XML file.

        Parses the XML file, displays the tree visualization in the Tree View tab,
        updates the UI to reflect the loaded file status, enables the convert button,
        and logs the action to the console.
        """
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])

        if file_path:
            try:
                self.current_xml_path = file_path
                file_name = os.path.basename(file_path)

                self.write_to_console(f"[INFO] XML loaded successfully: {file_name}")

                self.write_to_console("[PARSING] Building tree structure...")
                self.current_tree = tp.parse_file(file_path)

                self.write_to_console("[VISUALIZATION] Rendering tree in Tree View tab...")
                self.visualizer.draw_tree(self.current_tree)

                self.update_file_ui(True, file_name)
                self.write_to_console("[SUCCESS] Tree visualization complete.")

            except Exception as e:
                self.write_to_console(f"[ERROR] Failed to load XML: {str(e)}")
                self.current_xml_path = None
                self.current_tree = None
                self.update_file_ui(False)

    def run_panacea(self):
        """
        Execute the PANACEA conversion process.

        Parses the loaded XML file, generates a PRISM model (with or without time analysis
        based on the checkbox), saves the model and properties files, and logs progress.
        Handles errors gracefully and provides user feedback.

        Raises:
            Exception: If any step in the conversion process fails.
        """
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
            if self.current_tree:
                tree = self.current_tree
                self.write_to_console("[INFO] Using cached tree from file load.")
            else:
                tree = tp.parse_file(self.current_xml_path)

            prune_label = self.prune_entry.get()

            if prune_label:
                self.write_to_console(f"[INFO] Pruning tree at node: {prune_label}")
                tree = tree.prune(prune_label)
                self.write_to_console("[VISUALIZATION] Updating Tree View with pruned tree...")
                self.visualizer.draw_tree(tree)

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