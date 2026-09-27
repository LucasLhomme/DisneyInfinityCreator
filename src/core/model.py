"""Loading a downloaded 3D model and placing it the way the engine expects (Y up, facing +Z, feet on the ground)."""
import tempfile
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import trimesh
from PIL import Image

MODEL_EXTENSIONS = (".glb", ".gltf", ".obj", ".dae", ".ply", ".stl", ".off")
MAX_TEXTURE = 2048
_extracted_dirs: list[tempfile.TemporaryDirectory] = []


@dataclass
class SourceModel:
    name: str
    vertices: np.ndarray
    faces: np.ndarray
    uvs: np.ndarray
    """Texture coordinates with a top-left origin (the engine's and PIL's convention)."""
    texture: Image.Image
    winding_sign: float
    """+1 when the triangle winding agrees with the file's normals, -1 when it is reversed."""


@dataclass
class Placement:
    upright_fix: bool = False
    """True for Z-up files: rotate them so +Y is up."""
    quarter_turns: int = 0
    """Yaw in 90 degree steps, so that the character faces +Z with its left hand on +X."""
    height: float = 2.13


@dataclass
class CharacterModel:
    source: SourceModel
    placement: Placement = field(default_factory=Placement)

    @property
    def faces(self) -> np.ndarray:
        return self.source.faces

    @property
    def uvs(self) -> np.ndarray:
        return self.source.uvs

    @property
    def texture(self) -> Image.Image:
        return self.source.texture

    def vertices(self) -> np.ndarray:
        return place(self.source.vertices, self.placement)


def pick_model_file(folder: Path) -> Path | None:
    candidates = [p for p in folder.rglob("*") if p.suffix.lower() in MODEL_EXTENSIONS]
    candidates.sort(key=lambda p: (MODEL_EXTENSIONS.index(p.suffix.lower()), -p.stat().st_size))
    return candidates[0] if candidates else None


def load_source(path: str | Path) -> SourceModel:
    path = Path(path)
    model_file = path
    if path.suffix.lower() == ".zip":
        tmp = tempfile.TemporaryDirectory(prefix="dic_model_")
        _extracted_dirs.append(tmp)
        with zipfile.ZipFile(path) as archive:
            archive.extractall(tmp.name)
        model_file = pick_model_file(Path(tmp.name))
        if model_file is None:
            raise ValueError(f"no 3D model ({', '.join(MODEL_EXTENSIONS)}) in {path.name}")
    elif path.suffix.lower() not in MODEL_EXTENSIONS:
        raise ValueError(f"unsupported format: {path.suffix} (accepted: .zip {' '.join(MODEL_EXTENSIONS)})")

    loaded = trimesh.load(model_file, process=False)
    parts = loaded.dump(concatenate=False) if isinstance(loaded, trimesh.Scene) else [loaded]
    parts = [p for p in parts if isinstance(p, trimesh.Trimesh) and len(p.faces)]
    if not parts:
        raise ValueError(f"{model_file.name} contains no triangles")

    pieces = [_piece(p) for p in parts]
    atlas, rects = _pack_atlas([piece[3] for piece in pieces])
    vertices, faces, uvs, windings = [], [], [], []
    base = 0
    for (v, f, uv, _, winding), (rx, ry, rw, rh, pad) in zip(pieces, rects):
        u = (rx + pad + np.clip(uv[:, 0], 0, 1) * (rw - 2 * pad)) / atlas.width
        w = (ry + pad + np.clip(uv[:, 1], 0, 1) * (rh - 2 * pad)) / atlas.height
        vertices.append(v)
        faces.append(f + base)
        uvs.append(np.c_[u, w])
        windings.append((winding, len(f)))
        base += len(v)
    winding = float(np.sign(sum(s * n for s, n in windings))) or 1.0
    return SourceModel(model_file.stem, np.vstack(vertices), np.vstack(faces), np.vstack(uvs), atlas, winding)


def _piece(mesh: trimesh.Trimesh):
    """One material's worth of geometry: vertices, faces, top-left UVs, its texture tile and winding sign."""
    vertices = np.asarray(mesh.vertices, float)
    faces = np.asarray(mesh.faces, int)
    face_n = np.cross(vertices[faces[:, 1]] - vertices[faces[:, 0]], vertices[faces[:, 2]] - vertices[faces[:, 0]])
    normals = np.asarray(mesh.vertex_normals, float)
    winding = float(np.sign(np.median((face_n * normals[faces].mean(1)).sum(1)))) or 1.0
    visual = mesh.visual
    if visual.kind == "texture" and visual.uv is not None and len(visual.uv) == len(vertices):
        image = _material_image(visual.material)
        if image is not None:
            uv = np.asarray(visual.uv, float)
            return vertices, faces, np.c_[uv[:, 0], 1.0 - uv[:, 1]], image, winding
        color = _material_color(visual.material)
    elif visual.kind in ("vertex", "face"):
        vertices, faces, uvs, image = _palette_texture(mesh, vertices, faces)
        return vertices, faces, uvs, image, winding
    else:
        color = _material_color(getattr(visual, "material", None))
    return vertices, faces, np.full((len(vertices), 2), 0.5), Image.new("RGB", (8, 8), color), winding


def _pack_atlas(images: list[Image.Image]) -> tuple[Image.Image, list[tuple[int, int, int, int, int]]]:
    """Shelf-pack every tile (edge-padded against bleeding) into one power-of-two RGB texture."""
    if len(images) == 1:
        return _power_of_two(images[0]), [(0, 0, *_power_of_two(images[0]).size, 0)]
    area = sum(im.width * im.height for im in images)
    side = int(min(MAX_TEXTURE, 2 ** int(np.ceil(np.log2(max(64, np.sqrt(area) * 1.2))))))
    scale = min(1.0, np.sqrt(side * side / (area * 1.4)))
    while True:
        tiles = [im.resize((max(4, int(im.width * scale)), max(4, int(im.height * scale))), Image.LANCZOS)
                 for im in images]
        pad = max(2, int(8 * scale))
        order = sorted(range(len(tiles)), key=lambda i: -tiles[i].height)
        rects, x, y, shelf = [None] * len(tiles), 0, 0, 0
        fits = True
        for i in order:
            w, h = tiles[i].width + 2 * pad, tiles[i].height + 2 * pad
            if x + w > side:
                x, y, shelf = 0, y + shelf, 0
            if w > side or y + h > side:
                fits = False
                break
            rects[i] = (x, y, w, h, pad)
            x, shelf = x + w, max(shelf, h)
        if fits:
            break
        scale *= 0.85
    atlas = np.zeros((side, side, 3), np.uint8)
    for tile, (x, y, w, h, p) in zip(tiles, rects):
        atlas[y:y + h, x:x + w] = np.pad(np.asarray(tile), ((p, p), (p, p), (0, 0)), mode="edge")
    used = max(r[1] + r[3] for r in rects)
    height = int(2 ** int(np.ceil(np.log2(max(used, 4)))))
    return Image.fromarray(atlas[:height]), rects


def _material_image(material):
    for attr in ("image", "baseColorTexture"):
        image = getattr(material, attr, None)
        if image is not None:
            return image.convert("RGB")
    return None


def _material_color(material):
    for attr in ("main_color", "baseColorFactor", "diffuse"):
        color = getattr(material, attr, None)
        if color is not None:
            c = np.asarray(color, float).ravel()[:3]
            return tuple(int(v if c.max() > 1.0 else v * 255) for v in c)
    return (200, 200, 200)


def _palette_texture(mesh, vertices, faces):
    """Per-face colours become cells of a small tile, one UV per triangle corner."""
    colors = np.asarray(mesh.visual.face_colors, np.uint8)[:, :3]
    unique, face_cell = np.unique(colors, axis=0, return_inverse=True)
    face_cell = face_cell.reshape(-1)
    side = int(np.ceil(np.sqrt(len(unique))))
    cell = 8
    image = np.zeros((side * cell, side * cell, 3), np.uint8)
    for i, c in enumerate(unique):
        r, q = divmod(i, side)
        image[r * cell:(r + 1) * cell, q * cell:(q + 1) * cell] = c
    corner_uv = np.stack([(face_cell % side + 0.5) / side, (face_cell // side + 0.5) / side], 1)
    new_vertices = vertices[faces].reshape(-1, 3)
    new_faces = np.arange(len(new_vertices)).reshape(-1, 3)
    uvs = np.repeat(corner_uv, 3, axis=0)
    return new_vertices, new_faces, uvs, Image.fromarray(image)


def _power_of_two(image: Image.Image) -> Image.Image:
    def p2(n):
        return int(min(MAX_TEXTURE, max(4, 2 ** int(np.ceil(np.log2(max(n, 1)))))))
    size = (p2(image.width), p2(image.height))
    return image if image.size == size else image.resize(size, Image.LANCZOS)


def _rotation(placement: Placement) -> np.ndarray:
    m = np.eye(3)
    if placement.upright_fix:
        m = m @ np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)
    a = np.radians(90 * (placement.quarter_turns % 4))
    yaw = np.array([[np.cos(a), 0, -np.sin(a)], [0, 1, 0], [np.sin(a), 0, np.cos(a)]])
    return m @ yaw


def place(vertices: np.ndarray, placement: Placement) -> np.ndarray:
    v = vertices @ _rotation(placement)
    span = np.ptp(v[:, 1])
    if span > 0:
        v = v * (placement.height / span)
    v[:, 1] -= v[:, 1].min()
    v[:, 0] -= (v[:, 0].min() + v[:, 0].max()) / 2
    h = v[:, 1].max()
    torso = (v[:, 1] > 0.3 * h) & (v[:, 1] < 0.7 * h) & (np.abs(v[:, 0]) < 0.15 * h)
    zs = v[torso, 2] if torso.sum() > 10 else v[:, 2]
    v[:, 2] -= (zs.min() + zs.max()) / 2
    return v


def auto_placement(source: SourceModel, height: float) -> Placement:
    ext = np.ptp(source.vertices, axis=0)
    placement = Placement(upright_fix=bool(ext[1] < min(ext[0], ext[2]) * 0.8), height=height)
    v = place(source.vertices, placement)
    ext = np.ptp(v, axis=0)
    if ext[0] < ext[2]:
        placement.quarter_turns = 1
        v = place(source.vertices, placement)
    if not faces_forward(v):
        placement.quarter_turns += 2
    return placement


def faces_forward(v: np.ndarray) -> bool:
    """Feet stick out towards the front: compare how far the soles reach past the shins in +Z and -Z."""
    h = v[:, 1].max()
    soles = v[:, 1] < 0.06 * h
    shins = (v[:, 1] > 0.15 * h) & (v[:, 1] < 0.3 * h)
    if soles.sum() < 5 or shins.sum() < 5:
        return True
    forward = v[soles, 2].max() - v[shins, 2].max()
    backward = v[shins, 2].min() - v[soles, 2].min()
    return forward >= backward
