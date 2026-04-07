import customtkinter as ctk
from tkinter import messagebox, filedialog
import os
from PIL import Image

import tree_to_prism as tp

class PanaceaApp(ctk.CTk):
    def write_to_console(self, text):
        """
        Write text to the read-only output console.
        
        This method temporarily enables the textbox, inserts the text, disables it again,
        and auto-scrolls to the bottom to maintain a read-only state while allowing
        programmatic output updates.
        
        Args:
            text (str): The text message to be displayed in the console.
        
        Returns:
            None
        """
        self.textbox.configure(state="normal")
        self.textbox.insert("end", text)
        self.textbox.see("end")
        self.textbox.configure(state="disabled")
        self.update()

    def __init__(self):
        """
        Initialize the PANACEA Framework Desktop GUI application.
        
        Sets up the main window with dark theme, configures the grid layout,
        creates sidebar with controls, and initializes the main content area
        with log console and model generation button.
        
        Returns:
            None
        """
        super().__init__()

        # 1. Window Configuration
        self.title("PANACEA Framework - Desktop GUI")
        self.geometry("900x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Variable to store the loaded file path
        self.current_xml_path = None

        # 2. Grid Layout
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # 3. Sidebar (Controls)
        self.sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.setup_sidebar()

        # 4. Main Area (Log and Results)
        self.main_content = ctk.CTkFrame(self, fg_color="transparent")
        self.main_content.grid(row=0, column=1, padx=20, pady=20, sticky="nsew")
        self.setup_main_area()

    def setup_sidebar(self):
        """
        Configure the left sidebar with logo, import button, and options.
        
        Creates the PANACEA branding label, XML import button with icon handling,
        and the time analysis checkbox for model configuration options.
        
        Returns:
            None
        """
        self.logo_label = ctk.CTkLabel(self.sidebar, text="PANACEA", font=ctk.CTkFont(size=24, weight="bold"))
        self.logo_label.pack(pady=(30, 20), padx=10)

        # Safe icon handling (if you don't place it in 'assets/upload.png', the program will continue anyway)
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "upload.png")
            img = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(20, 20))
        except:
            img = None

        self.btn_load = ctk.CTkButton(
            self.sidebar, 
            text=" Import XML", 
            image=img,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold"),
            command=self.load_xml
        )
        self.btn_load.pack(pady=20, padx=20, fill="x")

        self.time_analysis = ctk.CTkCheckBox(self.sidebar, text="Time Analysis (R-ADT)")
        self.time_analysis.pack(pady=10, padx=20, anchor="w")

    def setup_main_area(self):
        """
        Configure the main content area with title, generate button, and console.
        
        Creates the model control panel title, the PRISM model generation button,
        and the read-only output console for displaying processing logs and results.
        
        Returns:
            None
        """
        self.title_label = ctk.CTkLabel(self.main_content, text="Model Control Panel", font=ctk.CTkFont(size=18, weight="bold"))
        self.title_label.pack(pady=(0, 20), anchor="w")

        self.btn_convert = ctk.CTkButton(self.main_content, text="Generate PRISM Model", state="disabled", command=self.run_panacea)
        self.btn_convert.pack(pady=(0, 20), anchor="w")

        self.log_label = ctk.CTkLabel(self.main_content, text="Output Console:", font=ctk.CTkFont(size=14))
        self.log_label.pack(pady=(10, 5), anchor="w")

        self.textbox = ctk.CTkTextbox(self.main_content, width=600, height=200, fg_color="#1e1e1e", state="disabled")
        self.textbox.pack(padx=0, pady=0, fill="x")

    def load_xml(self):
        """
        Open a file dialog to load an XML attack-defense tree definition.
        
        Prompts the user to select an XML file, stores the path, updates the console
        with confirmation message, and enables the model generation button with updated label.
        
        Returns:
            None
        """
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
        if file_path:
            self.current_xml_path = file_path
            file_name = os.path.basename(file_path)
            self.write_to_console(f"[INFO] XML loaded successfully: {file_name}\n")
            
            self.btn_convert.configure(state="normal")
            self.btn_convert.configure(text=f"Generate Model for '{file_name}'")

    def run_panacea(self):
        """
        Execute the PANACEA model generation pipeline.
        
        Orchestrates the complete workflow: prompts for output file location,
        parses the input XML tree, translates to a stochastic game model,
        generates PRISM model and properties files. Handles time analysis variant
        based on checkbox configuration. Logs all steps and errors to the console.
        
        Raises:
            Displays error messages in console if XML parsing or model generation fails.
        
        Returns:
            None
        """
        if not self.current_xml_path:
            return

        use_time = self.time_analysis.get() == 1
        
        # Ask the user where to save the file (equivalent to the --output argument of main.py)
        output_path = filedialog.asksaveasfilename(
            defaultextension=".prism",
            filetypes=[("PRISM files", "*.prism")],
            title="Save PRISM model as..."
        )

        if not output_path:
            self.write_to_console("[WARNING] Save operation cancelled.\n")
            return

        self.write_to_console(f"\n--- GENERATION START ---\n")
        self.write_to_console(f"[PARAM] Time Analysis enabled: {use_time}\n")

        try:
            # 1. Tree parsing (as main.py does at line 16)
            self.write_to_console("[1/3] Extracting data from R-ADT tree...\n")
            tree = tp.parse_file(self.current_xml_path)

            # 2. Model Generation (lines 19-22 of main.py)
            self.write_to_console("[2/3] Translation to Stochastic Game...\n")
            if use_time:
                prism_model = tp.get_prism_model_time(tree)
            else:
                prism_model = tp.get_prism_model(tree)

            # 3. Saving to disk (line 24 of main.py)
            self.write_to_console("[3/3] Writing PRISM file...\n")
            tp.save_prism_model(prism_model, output_path)

            # 4. Properties file generation (--props in main.py, line 26)
            # Saved in the same folder where the user chose to save the .prism file
            props_path = os.path.join(os.path.dirname(output_path), "properties.props")
            tp.save_prism_properties(props_path)

            self.write_to_console(f"\n[SUCCESS] Model saved to: {os.path.basename(output_path)}\n")
            self.write_to_console(f"[SUCCESS] PRISM properties saved to: {os.path.basename(props_path)}\n")

        except Exception as e:
            # In case of malformed trees or missing XML tags
            self.write_to_console(f"\n[CRITICAL ERROR] Conversion failed: {str(e)}\n")

if __name__ == "__main__":
    app = PanaceaApp()
    app.mainloop()