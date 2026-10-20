"""Nettoyage automatique d'un modèle 3D pour Disney Infinity Creator.

Lancé par Blender en arrière-plan :
    blender --background --python blender_clean.py -- entrée sortie.glb [max_sommets]
Formats acceptés en entrée : .glb .gltf .obj .fbx .dae, ou un .zip qui en contient un.
"""
from __future__ import annotations

import atexit
import math
import os
import shutil
import sys
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import bmesh
import bpy
from mathutils import Matrix, Vector

MODEL_EXT: tuple[str, ...] = (".glb", ".gltf", ".obj", ".fbx", ".dae")
IMAGE_EXT: tuple[str, ...] = (".png", ".jpg", ".jpeg", ".tga", ".bmp", ".webp")
fatal_errors: list[str] = []
_temp_dirs: list[str] = []


def _cleanup_temp_dirs() -> None:
    for d in _temp_dirs:
        shutil.rmtree(d, ignore_errors=True)


atexit.register(_cleanup_temp_dirs)


def log(msg: str) -> None:
    print(f"[clean] {msg}", flush=True)


def check(ok: bool, label: str, detail: str = "", fatal: bool = False) -> None:
    """Une ligne de rapport : OK / ATTENTION / ÉCHEC."""
    tag = "OK       " if ok else ("ÉCHEC    " if fatal else "ATTENTION")
    log(f"{tag} {label}" + (f" - {detail}" if detail else ""))
    if not ok and fatal:
        fatal_errors.append(label)


def parse_args() -> tuple[str, str, int, int]:
    argv = sys.argv
    args = argv[argv.index("--") + 1:] if "--" in argv else []
    if len(args) < 2:
        raise SystemExit("Usage : -- entrée sortie.glb [max_sommets] [max_tris]")
    return args[0], args[1], int(args[2]) if len(args) > 2 else 65000, int(args[3]) if len(args) > 3 else 0


def find_model(path: str) -> str:
    """Renvoie le fichier de modèle à importer (extrait le .zip si besoin avec nettoyage garanti)."""
    if not path.lower().endswith(".zip"):
        return path
    folder = tempfile.mkdtemp(prefix="di_clean_")
    _temp_dirs.append(folder)
    with zipfile.ZipFile(path) as z:
        z.extractall(folder)
    found: list[str] = []
    for root, _, files in os.walk(folder):
        found.extend(os.path.join(root, f) for f in files if f.lower().endswith(MODEL_EXT))
    if not found:
        raise SystemExit("Aucun .glb/.gltf/.obj/.fbx trouvé dans ce .zip.")
    found.sort(key=lambda p: (MODEL_EXT.index(os.path.splitext(p)[1].lower()), -os.path.getsize(p)))
    return found[0]


def import_model(path: str) -> None:
    ext = os.path.splitext(path)[1].lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".dae":
        bpy.ops.wm.collada_import(filepath=path)
    else:
        raise SystemExit(f"Format non pris en charge : {ext}")


def usable_image(image: bpy.types.Image | None) -> bool:
    if image is None:
        return False
    return bool(image.has_data or (image.filepath and os.path.isfile(bpy.path.abspath(image.filepath))))


def find_images(folder: str) -> list[str]:
    found: list[str] = []
    for root, _, files in os.walk(folder):
        found.extend(os.path.join(root, f) for f in files if f.lower().endswith(IMAGE_EXT))
    return found


def _relink_material_texture(mat: bpy.types.Material, by_name: dict[str, str]) -> None:
    if not mat.node_tree:
        return
    for node in mat.node_tree.nodes:
        if node.type != "TEX_IMAGE" or not getattr(node, "image", None):
            continue
        if usable_image(node.image):
            continue
        raw_name = node.image.filepath.replace("\\", "/") if node.image.filepath else ""
        name = os.path.basename(raw_name).lower() or node.image.name.lower()
        if name in by_name:
            node.image.filepath = by_name[name]
            node.image.reload()
            log(f"Texture retrouvée à côté du modèle : {name}")


def repair_textures(meshes: list[bpy.types.Object], folder: str) -> None:
    """Textures perdues à l'import : les retrouve à côté du modèle."""
    candidates = find_images(folder)
    if not candidates:
        return
    by_name = {os.path.basename(p).lower(): p for p in candidates}
    for mat in bpy.data.materials:
        _relink_material_texture(mat, by_name)

    def is_slot_textured(slot: bpy.types.MaterialSlot) -> bool:
        if not slot.material or not slot.material.node_tree:
            return False
        return any(n.type == "TEX_IMAGE" and usable_image(getattr(n, "image", None)) for n in slot.material.node_tree.nodes)

    bare = [o for o in meshes if not any(is_slot_textured(s) for s in o.material_slots)]
    if not bare:
        return
    stem = os.path.splitext(os.path.basename(str(bpy.context.scene.get("model_name", ""))))[0].lower()
    candidates.sort(key=lambda p: (stem not in os.path.basename(p).lower() if stem else 0, -os.path.getsize(p)))
    chosen = candidates[0]
    image = bpy.data.images.load(chosen, check_existing=True)
    mat = bpy.data.materials.new("texture_retrouvee")
    mat.use_nodes = True
    tree = mat.node_tree
    if tree is None:
        return
    bsdf = next((n for n in tree.nodes if n.type == "BSDF_PRINCIPLED"), None) or tree.nodes.new("ShaderNodeBsdfPrincipled")
    tex = tree.nodes.new("ShaderNodeTexImage")
    tex.image = image
    tree.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    for o in bare:
        o.data.materials.clear()
        o.data.materials.append(mat)
    log(f"Aucune texture liée au modèle : {os.path.basename(chosen)} appliquée à {len(bare)} morceau(x)")
    if len(candidates) > 1:
        log("  autres images du dossier (non utilisées) : " + ", ".join(os.path.basename(p) for p in candidates[1:6]))


def count_textures(obj: bpy.types.Object) -> int:
    images: set[str] = set()
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.use_nodes and mat.node_tree:
            images |= {n.image.name for n in mat.node_tree.nodes if n.type == "TEX_IMAGE" and getattr(n, "image", None)}
    return len(images)


def world_bbox(o: bpy.types.Object) -> tuple[Vector, Vector]:
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
    hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    return lo, hi


def bake_rest_pose(meshes: list[bpy.types.Object]) -> tuple[int, int]:
    """Modèle déjà rigué : fige la pose de repos."""
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    for arm in armatures:
        arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    baked = 0
    for o in meshes:
        if o.modifiers:
            new_me = bpy.data.meshes.new_from_object(o.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            o.modifiers.clear()
            o.data = new_me
            baked += 1
    return len(armatures), baked


def drop_outliers(meshes: list[bpy.types.Object]) -> list[bpy.types.Object]:
    """Retire les morceaux très éloignés ou démesurés par rapport au plus gros morceau."""
    info: list[tuple[bpy.types.Object, Vector, Vector, int]] = []
    for o in meshes:
        lo, hi = world_bbox(o)
        info.append((o, (lo + hi) / 2, hi - lo, len(o.data.vertices)))
    main = max(info, key=lambda t: t[3])
    ref = max(main[2])
    kept: list[bpy.types.Object] = []
    for o, center, size, n in info:
        far = (center - main[1]).length > 4 * ref or max(size) > 6 * ref
        log(f"  {o.name} : {n} sommets, taille {size.x:.1f} x {size.y:.1f} x {size.z:.1f}"
            + (" -> RETIRÉ (hors de proportion)" if far else ""))
        if far:
            bpy.data.objects.remove(o, do_unlink=True)
        else:
            kept.append(o)
    return kept


def verify_export(dst: str, expected_textures: int) -> None:
    """Réimporte le .glb exporté pour vérifier qu'il est valide."""
    size = os.path.getsize(dst) if os.path.isfile(dst) else 0
    check(size > 0, "Fichier exporté créé", f"{size / 1e6:.1f} Mo", fatal=True)
    if size == 0:
        return
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=dst)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    verts = sum(len(o.data.vertices) for o in meshes)
    images = len(bpy.data.images)
    check(len(meshes) == 1 and verts > 0, "Le .glb se réimporte correctement",
          f"{len(meshes)} maillage(s), {verts} sommets", fatal=True)
    check(images >= expected_textures, "Textures présentes dans le .glb",
          f"{images} image(s) pour {expected_textures} attendue(s)")


def main() -> None:
    src, dst, max_verts, max_tris = parse_args()
    if os.path.isfile(dst):
        os.remove(dst)
    bpy.ops.wm.read_factory_settings(use_empty=True)

    model = find_model(src)
    log(f"Import de {os.path.basename(model)}")
    import_model(model)
    bpy.context.view_layer.update()
    scene = bpy.context.scene

    meshes = [o for o in scene.objects if o.type == "MESH"]
    scene["model_name"] = os.path.basename(model)
    repair_textures(meshes, os.path.dirname(os.path.abspath(model)))
    others = len(scene.objects) - len(meshes)
    if not meshes:
        raise SystemExit("Aucun maillage trouvé dans ce fichier.")
    log(f"{len(meshes)} morceau(x) de maillage, {others} objet(s) vide(s)/autre(s)")

    armatures, baked = bake_rest_pose(meshes)
    if armatures or baked:
        log(f"Modèle rigué : {armatures} squelette(s), {baked} maillage(s) figé(s) en pose de repos")
    if armatures:
        check(False, "Modèle déjà rigué",
              "le nettoyage peut le déformer : essaie d'abord de l'importer tel quel dans Creator")

    for o in meshes:
        world = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = world
        if o.data.users > 1:
            o.data = o.data.copy()
        o.vertex_groups.clear()
        if o.data.shape_keys:
            o.shape_key_clear()
    bpy.context.view_layer.update()

    for o in list(scene.objects):
        if o not in meshes:
            bpy.data.objects.remove(o, do_unlink=True)

    log("Morceaux :")
    meshes = drop_outliers(meshes)

    target = meshes[0]
    if len(meshes) > 1:
        with bpy.context.temp_override(active_object=target, object=target,
                                       selected_objects=meshes, selected_editable_objects=meshes):
            bpy.ops.object.join()
    target = [o for o in scene.objects if o.type == "MESH"][0]

    with bpy.context.temp_override(active_object=target, object=target,
                                   selected_objects=[target], selected_editable_objects=[target]):
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    me = target.data
    xs, ys, zs = ([v.co[i] for v in me.vertices] for i in range(3))
    diag = math.dist((min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs)))
    before = len(me.vertices)
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=max(diag * 2e-5, 1e-9))
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    bm.to_mesh(me)
    bm.free()
    me.update()
    log(f"Doublons : {before - len(me.vertices)} sommet(s) fusionné(s), {len(loose)} orphelin(s) retiré(s)")

    limit = int(max_verts * 0.75)
    count = len(me.vertices)
    if count > limit:
        dec = target.modifiers.new("Decimate", "DECIMATE")
        dec.ratio = limit / count
        with bpy.context.temp_override(active_object=target, object=target):
            bpy.ops.object.modifier_apply(modifier=dec.name)
        log(f"Décimation : {count} -> {len(target.data.vertices)} sommets (les détails fins peuvent s'adoucir)")

    if max_tris > 0:
        me.calc_loop_triangles()
        tris = len(me.loop_triangles)
        if tris > max_tris:
            dec = target.modifiers.new("DecimateBudget", "DECIMATE")
            dec.ratio = max_tris / tris
            dec.use_collapse_triangulate = True
            with bpy.context.temp_override(active_object=target, object=target):
                bpy.ops.object.modifier_apply(modifier=dec.name)
            me = target.data
            me.calc_loop_triangles()
            log(f"Décimation (budget) : {tris} -> {len(me.loop_triangles)} triangles")

    me = target.data
    xs, ys, zs = ([v.co[i] for v in me.vertices] for i in range(3))
    me.transform(Matrix.Translation(((-(min(xs) + max(xs)) / 2), (-(min(ys) + max(ys)) / 2), -min(zs))))
    me.update()
    width, depth, height = max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs)
    me.calc_loop_triangles()

    log("--- Rapport de vérification ---")
    textures = count_textures(target)
    check(len(scene.objects) == 1, "Un seul objet dans la scène", f"{len(scene.objects)} objet(s)")
    check(all(abs(s - 1) < 1e-6 for s in target.scale) and all(abs(r) < 1e-6 for r in target.rotation_euler),
          "Transformations appliquées (échelle 1, rotation 0)")
    check(len(me.vertices) <= max_verts, "Nombre de sommets sous la limite",
          f"{len(me.vertices)} / {max_verts} (les coutures UV en ajouteront au rig)")
    check(len(me.loop_triangles) > 0, "Triangles présents", f"{len(me.loop_triangles)} triangles", fatal=True)
    check(len(me.uv_layers) > 0, "Carte UV présente", "sans UV, les textures ne s'afficheront pas")
    check(len(target.material_slots) > 0, "Matériaux présents", f"{len(target.material_slots)} matériau(x)")
    check(textures > 0, "Textures détectées", f"{textures} image(s) - sinon le modèle sera gris")
    dims = sorted((width, depth, height), reverse=True)
    stretch = dims[0] / dims[1] if dims[1] else 99
    check(stretch <= 8, "Proportions plausibles pour un personnage",
          f"dimension max {dims[0]:.0f} contre {dims[1]:.0f} (rapport {stretch:.1f}, limite 8) "
          "- modèle étiré ou morceau parasite", fatal=True)
    check(height >= max(width, depth), "Modèle debout (la hauteur est la plus grande dimension)",
          f"largeur {width:.2f} / profondeur {depth:.2f} / hauteur {height:.2f}")
    ratio = max(width, depth) / height if height else 0
    if height >= max(width, depth):
        check(ratio >= 0.5, "Bras écartés (T-pose ou A-pose probable)",
              f"rapport largeur/hauteur {ratio:.2f} - sous 0,5 les bras sont sans doute le long du corps")
    else:
        check(False, "Pose non évaluée", "le modèle n'est pas debout, corrige d'abord son orientation")

    bpy.ops.object.select_all(action="DESELECT")
    bpy.ops.export_scene.gltf(filepath=dst, export_format="GLB")
    verify_export(dst, textures)

    if fatal_errors:
        if os.path.isfile(dst):
            os.remove(dst)
        log("ÉCHEC : " + " ; ".join(fatal_errors))
        sys.exit(1)
    log(f"Exporté : {dst}")


if __name__ == "__main__":
    main()
