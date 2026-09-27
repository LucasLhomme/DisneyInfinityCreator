"""Skinning weights for the custom mesh against the fitted joints."""
import subprocess
from pathlib import Path
from typing import Callable

import numpy as np
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import connected_components
from scipy.spatial import cKDTree

from src.core.paths import HEAT_SCRIPT
from src.core.skeleton import SIDES, heat_bones

Log = Callable[[str], None]


def weld(positions: np.ndarray, faces: np.ndarray, tolerance: float = 1e-5):
    """Merge coincident corners (UV seams) so weights are computed on one connected surface."""
    keys = np.round(positions / tolerance).astype(np.int64)
    _, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
    inverse = inverse.reshape(-1)
    wfaces = inverse[faces]
    ok = (wfaces[:, 0] != wfaces[:, 1]) & (wfaces[:, 1] != wfaces[:, 2]) & (wfaces[:, 0] != wfaces[:, 2])
    return positions[first], wfaces, inverse, ok


def blender_heat(wverts, wfaces, anchors, blender: Path, work: Path, log: Log) -> np.ndarray:
    bones = heat_bones()
    work.mkdir(parents=True, exist_ok=True)
    src, dst = work / "heat_in.npz", work / "heat_out.npz"
    dst.unlink(missing_ok=True)
    np.savez(src, verts=wverts, faces=wfaces,
             bone_names=np.array([b[0] for b in bones]),
             heads=np.array([anchors[b[1]] for b in bones]),
             tails=np.array([anchors[b[2]] for b in bones]),
             parents=np.array([b[3] for b in bones]))
    res = subprocess.run([str(blender), "-b", "--factory-startup", "--python", str(HEAT_SCRIPT), "--", str(src), str(dst)],
                         capture_output=True, text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    for line in (res.stdout + res.stderr).splitlines():
        if "[heat]" in line or "failed" in line.lower() or "Error" in line:
            log(f"  blender: {line.strip()}")
    if res.returncode != 0 or not dst.exists():
        raise RuntimeError(f"Blender failed (exit code {res.returncode})")
    return np.load(dst)["weights"].astype(float)


def distance_weights(wverts, anchors) -> np.ndarray:
    """Fallback without Blender: each vertex follows the bones closest to it (inverse distance to the segment)."""
    bones = heat_bones()
    d = np.zeros((len(wverts), len(bones)))
    for j, (_, head, tail, _) in enumerate(bones):
        a, b = anchors[head], anchors[tail]
        ab = b - a
        t = np.clip(((wverts - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
        d[:, j] = np.linalg.norm(wverts - (a + t[:, None] * ab), axis=1)
    nearest = d.min(1, keepdims=True)
    w = np.where(d <= nearest * 1.6 + 1e-6, 1.0 / (d + 1e-4) ** 4, 0.0)
    return w / w.sum(1, keepdims=True)


def fill_islands(wverts, weights, log: Log) -> np.ndarray:
    empty = weights.sum(1) <= 1e-6
    if empty.any() and (~empty).any():
        _, nearest = cKDTree(wverts[~empty]).query(wverts[empty])
        weights[empty] = weights[~empty][nearest]
        log(f"  {empty.sum()} isolated vertices (eyes, accessories) copied from the nearest weighted surface")
    return weights


def rigid_head(wverts, weights, names, anchors, log: Log) -> np.ndarray:
    shoulder_x = abs(anchors["Shoulder_Left"][0])
    above = (wverts[:, 1] >= anchors["Head"][1]) & (np.abs(wverts[:, 0]) < shoulder_x * 1.5)
    weights[above] = 0.0
    weights[above, names.index("Head")] = 1.0
    log(f"  {above.sum()} vertices above the head joint made rigid (eyes stay in place)")
    return weights


def isolate_sides_and_feet(verts, faces, weights, names, anchors, log: Log) -> np.ndarray:
    """Loose pieces below the knees follow one ankle rigidly; everything else drops opposite-side bones."""
    n = len(verts)
    rows = np.concatenate([faces[:, 0], faces[:, 1], faces[:, 2]])
    cols = np.concatenate([faces[:, 1], faces[:, 2], faces[:, 0]])
    _, label = connected_components(coo_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n)), directed=False)
    original = weights.copy()
    margin = 0.01 * verts[:, 1].max()
    side_of = np.where(verts[:, 0] > margin, "Left", np.where(verts[:, 0] < -margin, "Right", ""))
    knee_y = min(anchors["Knee_Left"][1], anchors["Knee_Right"][1])
    rigid = np.zeros(n, bool)
    for comp in np.unique(label):
        members = label == comp
        if verts[members, 1].max() >= knee_y:
            continue
        side = "Left" if verts[members, 0].mean() > 0 else "Right"
        side_of[members] = side
        weights[members] = 0.0
        weights[members, names.index(f"Ankle_{side}")] = 1.0
        rigid |= members
    for side, _ in SIDES:
        other = "Right" if side == "Left" else "Left"
        mask = (side_of == side) & ~rigid
        weights[np.ix_(mask, [j for j, name in enumerate(names) if name.endswith(other)])] = 0.0
    totals = weights.sum(1, keepdims=True)
    weights = np.where(totals > 1e-6, weights / np.maximum(totals, 1e-6), original)
    log(f"  {rigid.sum()} vertices of loose pieces below the knees bound to their ankle; cross-side weights removed")
    return weights


def compute_weights(wverts, wfaces, anchors, blender: Path | None, work: Path, log: Log) -> tuple[list[str], np.ndarray, str]:
    names = [b[0] for b in heat_bones()]
    method = "distance"
    weights = None
    if blender and Path(blender).is_file():
        try:
            log("Computing bone-heat weights in Blender...")
            weights = blender_heat(wverts, wfaces, anchors, Path(blender), work, log)
            method = "blender"
        except (RuntimeError, OSError) as exc:
            log(f"  {exc} -> falling back to distance weights")
    else:
        log("Blender not found: using distance-to-bone weights (less accurate)")
    if weights is None:
        weights = distance_weights(wverts, anchors)
    weights = fill_islands(wverts, weights, log)
    weights = rigid_head(wverts, weights, names, anchors, log)
    weights = isolate_sides_and_feet(wverts, wfaces, weights, names, anchors, log)
    return names, weights, method


def quantize_weights(weights: np.ndarray, bone_cols: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Top 4 influences per vertex as bone indices + weights summing to exactly 255."""
    order = np.argsort(-weights, axis=1)[:, :4]
    top = np.take_along_axis(weights, order, 1)
    top = top / np.maximum(top.sum(1, keepdims=True), 1e-12)
    q = np.floor(top * 255).astype(int)
    rem = 255 - q.sum(1)
    frac = top * 255 - q
    for i in np.nonzero(rem)[0]:
        for j in np.argsort(-frac[i])[:rem[i]]:
            q[i, j] += 1
    idx = bone_cols[order]
    idx[q == 0] = idx[:, :1].repeat(4, 1)[q == 0]
    return idx.astype(np.uint8), q.astype(np.uint8)
