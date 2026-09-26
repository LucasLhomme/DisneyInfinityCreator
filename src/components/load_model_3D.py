import customtkinter as ctk
from tkinter import filedialog
import trimesh
import numpy as np
import zipfile
import tempfile
import os
import shutil

def open_file_dialog():
    filepath = filedialog.askopenfilename(
        title="Importer un modele 3D ou une archive ZIP",
        filetypes=[
            ("Fichiers 3D et ZIP", "*.zip *.obj *.stl *.ply *.gltf *.glb"), 
            ("Tous les fichiers", "*.*")
        ]
    )
    return filepath

def extract_and_find_model(zip_path):
    # Créer un dossier temporaire pour l'extraction
    temp_dir = tempfile.mkdtemp(prefix="dim_creator_")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(temp_dir)
        
    # Chercher le modèle 3D dans le dossier
    valid_exts = ['.obj', '.gltf', '.glb', '.stl', '.ply']
    for root, dirs, files in os.walk(temp_dir):
        for file in files:
            if any(file.lower().endswith(ext) for ext in valid_exts):
                return os.path.join(root, file), temp_dir
                
    return None, temp_dir

def load_3d_model(filepath):
    if not filepath:
        return None
        
    extracted_dir = None
    try:
        model_path = filepath
        if filepath.lower().endswith('.zip'):
            print("Archive ZIP détectée, extraction en cours...")
            model_path, extracted_dir = extract_and_find_model(filepath)
            if not model_path:
                print("Aucun modèle 3D trouvé dans l'archive ZIP.")
                return None
            print(f"Modèle trouvé dans le ZIP : {os.path.basename(model_path)}")
            
        mesh_or_scene = trimesh.load(model_path, force='mesh')
        mesh_or_scene.apply_translation(-mesh_or_scene.centroid)
        return mesh_or_scene
        
    except Exception as e:
        print(f"Erreur lors du chargement : {e}")
        return None
    finally:
        # On ne supprime pas le dossier temporaire tout de suite si on veut garder l'accès aux textures
        # L'OS nettoiera le dossier temp au redémarrage, ou on peut le gérer manuellement plus tard.
        pass

def scale_model(mesh, character_type):
    if not mesh:
        return
        
    target_heights = {
        "small": 1.2,
        "medium": 1.8,
        "large": 2.5
    }
    
    target_h = target_heights.get(character_type, 1.8)
    extents = mesh.extents
    current_h = extents[1]
    
    if current_h > 0:
        scale_factor = target_h / current_h
        scale_matrix = trimesh.transformations.scale_matrix(scale_factor, [0, 0, 0])
        mesh.apply_transform(scale_matrix)
        
        min_y = mesh.bounds[0][1]
        mesh.apply_translation([0, -min_y, 0])
        
    return mesh

def export_model(mesh, export_path):
    if not mesh:
        return False
    try:
        mesh.export(export_path)
        return True
    except Exception as e:
        print(f"Erreur lors de l'exportation : {e}")
        return False
