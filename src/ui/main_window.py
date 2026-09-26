import customtkinter as ctk
import json
from tkinter import filedialog
import os
from src.render.gl_widget import GLRenderer
from src.components.load_model_3D import open_file_dialog, load_3d_model, scale_model, export_model
from src.components.config import load_settings, save_settings

class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        self.settings = load_settings()
        
        # Gestion des langues
        try:
            with open("src/config/lang_fr.json", "r", encoding="utf-8") as f:
                self.lang = json.load(f)
        except Exception:
            self.lang = {
                "import_model": "Importer Modèle",
                "export_character": "Auto-Rig & Exporter",
                "blender_path": "Chemin Blender.exe :"
            }
            
        self.current_mesh = None
        self.title("Disney Infinity Creator")
        self.geometry("1280x720")
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.configure(fg_color="#09090b")
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        # === SIDEBAR ===
        self.sidebar_frame = ctk.CTkFrame(self, width=320, corner_radius=0, fg_color="#121316", border_width=1, border_color="#27272a")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1)
        
        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Disney Infinity\nCreator", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 30))
        
        # Settings: Blender Path
        self.blender_label = ctk.CTkLabel(self.sidebar_frame, text=self.lang.get("blender_path", "Chemin Blender :"), anchor="w")
        self.blender_label.grid(row=1, column=0, padx=20, pady=(0, 5), sticky="w")
        
        self.blender_entry = ctk.CTkEntry(self.sidebar_frame, fg_color="#27272a", border_width=0, text_color="#e4e4e7")
        self.blender_entry.grid(row=2, column=0, padx=20, pady=(0, 20), sticky="ew")
        self.blender_entry.insert(0, self.settings.get("blender_path", ""))
        self.blender_entry.bind("<FocusOut>", self.save_blender_path)
        
        # Bouton Import
        self.import_button = ctk.CTkButton(self.sidebar_frame, text=self.lang.get("import_model", "Importer Modèle"), fg_color="#ffffff", text_color="#09090b", hover_color="#e4e4e7", font=ctk.CTkFont(size=13, weight="bold"), command=self.on_import)
        self.import_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        # Zone options de taille
        self.size_var = ctk.StringVar(value="medium")
        self.size_menu = ctk.CTkOptionMenu(
            self.sidebar_frame, 
            values=["Petit (Yoda)", "Moyen (Luke)", "Grand (Hulkbuster)"],
            command=self.on_size_change,
            fg_color="#27272a", button_color="#3f3f46", button_hover_color="#52525b"
        )
        self.size_menu.grid(row=4, column=0, padx=20, pady=(5, 20), sticky="ew")
        self.size_menu.set("Moyen (Luke)")
        
        # Bouton Export
        self.export_button = ctk.CTkButton(self.sidebar_frame, text=self.lang.get("export_character", "Auto-Rig & Exporter"), fg_color="transparent", border_width=1, border_color="#27272a", text_color="#e4e4e7", hover_color="#27272a", command=self.on_export)
        self.export_button.grid(row=5, column=0, padx=20, pady=10, sticky="ew")
        
        # === VIEWPORT 3D ===
        self.viewport_frame = ctk.CTkFrame(self, fg_color="#09090b", corner_radius=0)
        self.viewport_frame.grid(row=0, column=1, sticky="nsew")
        self.viewport_frame.grid_rowconfigure(0, weight=1)
        self.viewport_frame.grid_columnconfigure(0, weight=1)
        
        self.image_label = ctk.CTkLabel(self.viewport_frame, text="Rendu 3D")
        self.image_label.grid(row=0, column=0, sticky="nsew")
        
        self.renderer = GLRenderer(self.image_label)
        self.bind("<Configure>", self.on_resize)

    def save_blender_path(self, event=None):
        self.settings["blender_path"] = self.blender_entry.get()
        save_settings(self.settings)
        print("Chemin Blender sauvegardé :", self.settings["blender_path"])

    def on_import(self):
        filepath = open_file_dialog()
        if filepath:
            self.current_mesh = load_3d_model(filepath)
            self.on_size_change(self.size_menu.get())
            print(f"Modèle chargé: {filepath}")

    def on_size_change(self, choice):
        if not self.current_mesh:
            return
        archetype = "medium"
        if "Yoda" in choice or "Petit" in choice: archetype = "small"
        elif "Hulkbuster" in choice or "Grand" in choice: archetype = "large"
        self.current_mesh = scale_model(self.current_mesh, archetype)
        print(f"Echelle ajustée sur l'archetype : {archetype}"); self.renderer.set_mesh(self.current_mesh)
        
    def on_export(self):
        if not self.current_mesh:
            print("Aucun modèle à exporter.")
            return
            
        print("Lancement de l'Auto-Rigger via Blender...")
        # TODO: Appeler auto_rigger.py
        
    def on_resize(self, event):
        if event.widget == self.viewport_frame:
            self.renderer.resize(event.width, event.height)
