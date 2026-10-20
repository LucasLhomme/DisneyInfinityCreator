"""Clean a model with Blender (merge pieces, fix scale/orientation, recover textures, FBX support) before import.

Runs src/scripts/blender_clean.py in a background Blender. Intermediate files are cleaned up immediately via context
managers, and the final result goes to a managed temporary folder that is cleaned up on exit or next run."""
from __future__ import annotations

import atexit
import struct
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from src.core.paths import SCRIPTS_DIR

CLEAN_SCRIPT = SCRIPTS_DIR / "blender_clean.py"
BAKE_SCRIPT = SCRIPTS_DIR / "bake_skinned_glb.py"
NEEDS_BLENDER = (".fbx",)
"""Formats the built-in loader cannot read reliably: they always go through Blender."""

_last_clean_dir: tempfile.TemporaryDirectory | None = None


def cleanup_clean_dir() -> None:
    """Clean up any temporary directory holding the last cleaned model."""
    global _last_clean_dir
    if _last_clean_dir is not None:
        _last_clean_dir.cleanup()
        _last_clean_dir = None


atexit.register(cleanup_clean_dir)


def is_skinned_glb(path: Path) -> bool:
    """True when the .glb holds a skeleton: it must be frozen in rest pose before Blender sees it."""
    try:
        with open(path, "rb") as f:
            head = f.read(20)
            if head[:4] != b"glTF" or head[16:20] != b"JSON":
                return False
            f.seek(12)
            length = struct.unpack("<I", f.read(4))[0]
            f.read(4)
            return b'"skins"' in f.read(length)
    except OSError:
        return False


def dae_to_glb(path: Path, out: Path) -> Path:
    """Blender 5 dropped its COLLADA importer: the built-in loader reads the .dae (pieces merged, textures packed
    into one atlas) and hands Blender an equivalent .glb. The material is written as plain PBR (white factor, no
    metal) so the colours come back unchanged."""
    import numpy as np
    import trimesh

    from src.core.model import load_source
    src = load_source(path)
    mat = trimesh.visual.material.PBRMaterial(baseColorTexture=src.texture, baseColorFactor=[255, 255, 255, 255],
                                              metallicFactor=0.0, roughnessFactor=1.0)
    uv = np.c_[src.uvs[:, 0], 1 - src.uvs[:, 1]]
    trimesh.Trimesh(src.vertices, src.faces, visual=trimesh.visual.TextureVisuals(uv=uv, material=mat),
                    process=False).export(out)
    return out


@contextmanager
def cleaned_model(
    path: str | Path,
    blender: str | Path,
    max_vertices: int = 65000,
    max_triangles: int = 0,
) -> Iterator[tuple[Path, list[str]]]:
    """Context manager for running Blender cleaning, yielding (cleaned_glb_path, report)
    and cleaning up the entire work directory on exit."""
    blender_path = Path(blender)
    if not blender_path.is_file():
        raise RuntimeError("Blender not found: set blender.exe in the Rig & Export tab.")
    with tempfile.TemporaryDirectory(prefix="di_clean_") as tmp_dir:
        work = Path(tmp_dir)
        flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        report: list[str] = []
        source = Path(path)
        suffix = source.suffix.lower()
        if suffix == ".glb" and is_skinned_glb(source):
            baked = work / "baked.glb"
            proc = subprocess.run([sys.executable, str(BAKE_SCRIPT), str(source), str(baked)], capture_output=True,
                                  text=True, errors="replace", creationflags=flags)
            if proc.returncode != 0 or not baked.is_file():
                raise RuntimeError("Freezing the skeleton failed:\n" + (proc.stdout + proc.stderr)[-800:])
            report.append("Rigged model: skeleton frozen in rest pose.")
            source = baked
        elif suffix == ".dae":
            try:
                source = dae_to_glb(source, work / "from_dae.glb")
            except (ValueError, OSError, KeyError, ET.ParseError) as exc:
                raise RuntimeError(f"Reading the .dae failed: {exc}") from exc
            report.append("COLLADA (.dae): converted to .glb for Blender.")
        out = work / "clean.glb"
        proc = subprocess.run([str(blender_path), "--background", "--factory-startup", "--python-exit-code", "1",
                               "--python", str(CLEAN_SCRIPT), "--", str(source), str(out), str(max_vertices),
                               str(max_triangles)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=flags)
        lines = (proc.stdout + "\n" + proc.stderr).splitlines()
        clean_lines = [ln[len("[clean] "):] for ln in lines if ln.startswith("[clean]")]
        if proc.returncode != 0 or not out.is_file():
            tail = [ln for ln in lines if ln.strip()][-10:]
            raise RuntimeError("Blender could not clean this model:\n" + "\n".join(clean_lines[-8:] + tail))
        shown = ("ATTENTION", "Texture", "Aucune texture", "  autres", "Décimation")
        ignored = ("Modèle debout", "Pose non évaluée")
        report += [ln for ln in clean_lines if ln.startswith(shown) and not any(word in ln for word in ignored)]
        yield out, report


def clean_model(
    path: str | Path,
    blender: str | Path,
    max_vertices: int = 65000,
    max_triangles: int = 0,
) -> tuple[Path, list[str]]:
    """Return (cleaned .glb path in a temp folder, list of report lines). Raises RuntimeError with details on failure."""
    path_obj, blender_obj = Path(path), Path(blender)
    if not blender_obj.is_file():
        raise RuntimeError("Blender not found: set blender.exe in the Rig & Export tab.")

    global _last_clean_dir
    cleanup_clean_dir()
    clean_dir = tempfile.TemporaryDirectory(prefix="di_clean_out_")
    _last_clean_dir = clean_dir
    out = Path(clean_dir.name) / "clean.glb"

    flags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
    report: list[str] = []
    source = path_obj
    suffix = path_obj.suffix.lower()

    with tempfile.TemporaryDirectory(prefix="di_clean_inter_") as inter_dir:
        inter_work = Path(inter_dir)
        if suffix == ".glb" and is_skinned_glb(path_obj):
            baked = inter_work / "baked.glb"
            proc = subprocess.run([sys.executable, str(BAKE_SCRIPT), str(path_obj), str(baked)], capture_output=True,
                                  text=True, errors="replace", creationflags=flags)
            if proc.returncode != 0 or not baked.is_file():
                raise RuntimeError("Freezing the skeleton failed:\n" + (proc.stdout + proc.stderr)[-800:])
            report.append("Rigged model: skeleton frozen in rest pose.")
            source = baked
        elif suffix == ".dae":
            try:
                source = dae_to_glb(path_obj, inter_work / "from_dae.glb")
            except (ValueError, OSError, KeyError, ET.ParseError) as exc:
                raise RuntimeError(f"Reading the .dae failed: {exc}") from exc
            report.append("COLLADA (.dae): converted to .glb for Blender.")

        proc = subprocess.run([str(blender_obj), "--background", "--factory-startup", "--python-exit-code", "1",
                               "--python", str(CLEAN_SCRIPT), "--", str(source), str(out), str(max_vertices),
                               str(max_triangles)],
                              capture_output=True, text=True, encoding="utf-8", errors="replace", creationflags=flags)

    lines = (proc.stdout + "\n" + proc.stderr).splitlines()
    clean_lines = [ln[len("[clean] "):] for ln in lines if ln.startswith("[clean]")]
    if proc.returncode != 0 or not out.is_file():
        tail = [ln for ln in lines if ln.strip()][-10:]
        raise RuntimeError("Blender could not clean this model:\n" + "\n".join(clean_lines[-8:] + tail))
    shown = ("ATTENTION", "Texture", "Aucune texture", "  autres", "Décimation")
    ignored = ("Modèle debout", "Pose non évaluée")  # the Creator stands Z-up files up by itself
    report += [ln for ln in clean_lines if ln.startswith(shown) and not any(word in ln for word in ignored)]
    return out, report
