"""Limb thickness: fan models often have much thinner arms and legs than the chunky Disney Infinity figures, and the
game's skinning pinches thin limbs even more when they twist. The limbs can be inflated around their bone axis
(length unchanged), blended by the skinning weights so the shoulders and hips stay smooth."""
from __future__ import annotations

import numpy as np

ARM_SEGMENTS: tuple[tuple[str, str], ...] = (("Shoulder", "Elbow"), ("Elbow", "Hand"))
LEG_SEGMENTS: tuple[tuple[str, str], ...] = (("Thigh", "Knee"), ("Knee", "Ankle"))
SIDES: tuple[str, ...] = ("Left", "Right")
TORSO_SEGMENTS: tuple[tuple[str, str, float], ...] = (("Hips", "Spine2", 0.5), ("Spine2", "Spine3", 1.0), ("Spine3", "Neck", 1.0))
"""Torso bones (head, tail, share of the effect): the pelvis only follows halfway, the neck and head not at all."""
MAX_TORSO: float = 1.4
MAX_SUGGEST: float = 1.6
REACH: float = 0.6
"""Vertices farther from the axis than REACH x segment length (capes, wings) are left alone."""


def _segment_offsets(verts: np.ndarray, a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, float]:
    ab = b - a
    length = float(np.linalg.norm(ab))
    t = np.clip((verts - a) @ ab / max(length * length, 1e-12), 0.0, 1.0)
    perp = verts - (a + np.outer(t, ab))
    return perp, length


V_RANGE: tuple[float, float, float, float] = (0.25, 0.6, 0.82, 0.95)
"""Where the V-shape acts along the spine (0 = hips, 1 = neck): fades in from 0.25 to full at 0.6 (chest, armpits),
stays full up to the shoulders (0.82) and is gone below the neck base (0.95): waist, neck and head keep their width."""
MAX_V: float = 2.5
"""Strongest sideways widening of the chest at any height."""


def torso_mask(verts: np.ndarray, anchors: dict[str, np.ndarray]) -> np.ndarray:
    """Vertices that belong to the torso (rough skeleton weights): wide sleeves and arms are left out."""
    weights, names = preview_weights(verts, anchors)
    torso = [i for i, n in enumerate(names) if n in ("Hips", "Spine2", "Spine3", "Neck") or n.startswith("_Clavicle")]
    return weights[:, torso].sum(axis=1) > 0.5


def v_scales(
    verts: np.ndarray,
    anchors: dict[str, np.ndarray],
    target: float,
    slabs: int = 14,
) -> tuple[np.ndarray, np.ndarray]:
    """(heights, factor) of the sideways scaling that brings the torso's half width up to `target` at each height of
    the chest (1 where it is already that wide, e.g. a flared jacket), smoothed along the height."""
    lo, hi = anchors["Hips"][1], anchors["Neck"][1]
    ys = np.linspace(lo, hi, slabs)
    band = 1.5 * (hi - lo) / slabs
    mask = torso_mask(verts, anchors)
    factors = np.ones(slabs)
    for i, y in enumerate(ys):
        sel = mask & (np.abs(verts[:, 1] - y) < band)
        if sel.sum() >= 4:
            half = float(np.percentile(np.abs(verts[sel, 0]), 90))
            factors[i] = np.clip(target / max(half, 1e-6), 1.0, MAX_V)
    kernel = np.array([0.25, 0.5, 0.25])
    padded = np.r_[factors[0], factors, factors[-1]]
    return ys, np.convolve(padded, kernel, mode="valid")


def _smooth(x: np.ndarray | float, a: float, b: float) -> np.ndarray | float:
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def v_profile(y: np.ndarray, anchors: dict[str, np.ndarray]) -> np.ndarray:
    """0-1 along the height: how much of the V-shape widening applies at each height. It stops at the armpits
    (shoulder joint height): above, the base of the neck and the collar keep their width."""
    span = max(anchors["Neck"][1] - anchors["Hips"][1], 1e-9)
    t = (y - anchors["Hips"][1]) / span
    a, b, c, d = V_RANGE
    if "Shoulder_Left" in anchors:
        top = (anchors["Shoulder_Left"][1] - anchors["Hips"][1]) / span
        c, d = min(c, top - 0.08), min(d, top)
    return _smooth(t, a, b) * (1 - _smooth(t, c, d))


MAX_HEAD: float = 1.4
NECK_SHARE: float = 0.5
"""The neck widens by half the head scaling (never stretched in height)."""


def head_pivot(verts: np.ndarray, head_weight: np.ndarray, anchors: dict[str, np.ndarray]) -> np.ndarray:
    """Point the head grows from: the head joint (jaw / skull base height) on the neck's axis. Above it the head
    grows up and out; below it (chin, neck) it only widens, so the chin does not sink into the collar and the neck
    keeps its length."""
    return np.asarray(anchors.get("Head", anchors.get("Neck")), float)


def inflate(
    verts: np.ndarray,
    weights: np.ndarray,
    names: list[str],
    anchors: dict[str, np.ndarray],
    arm_scale: float = 1.0,
    leg_scale: float = 1.0,
    torso_scale: float = 1.0,
    head_scale: float = 1.0,
    forearm_scale: float | None = None,
    v_shape: float = 0.0,
    v_target: float | None = None,
) -> np.ndarray:
    """T-pose vertices pushed away from their limb (or spine) axes by (scale - 1), weighted by each bone's weight.
    The head is scaled as a whole from its bottom (see head_pivot). `forearm_scale` defaults to `arm_scale`. `v_shape` (0-1) widens
    the chest sideways, height by height, until it is `v_target` wide (half width); the waist and whatever is already
    that wide are left alone: a V-shaped torso that fills the gap under the arms once they hang down."""
    out = verts.copy()
    if v_shape > 1e-3 and v_target and "Hips" in anchors and "Neck" in anchors:
        w = np.zeros(len(verts))
        for bone, share in (("Spine3", 1.0), ("Spine2", 1.0), ("Clavicle_Left", 1.0), ("Clavicle_Right", 1.0),
                            ("Hips", 0.5)):
            if bone in names:
                w += share * weights[:, names.index(bone)]
        ys, factors = v_scales(verts, anchors, v_target)
        factor = np.interp(verts[:, 1], ys, factors)
        blend = np.clip(w, 0, 1) * v_profile(verts[:, 1], anchors) * float(np.clip(v_shape, 0, 1))
        out[:, 0] += blend * (factor - 1.0) * verts[:, 0]  # sideways only, from the body's mid-plane

    if abs(head_scale - 1.0) >= 1e-3 and "Head" in names:
        w = np.clip(weights[:, names.index("Head")], 0, 1)
        neck = np.clip(weights[:, names.index("Neck")], 0, 1) if "Neck" in names else np.zeros(len(verts))
        pivot = head_pivot(verts, w, anchors)
        offset = verts - pivot
        offset[:, 1] = np.maximum(offset[:, 1], 0.0)  # below the jaw (neck) only widen, never push down
        out += ((head_scale - 1.0) * w)[:, None] * offset
        # The neck thickens with the head (halfway) so a big head does not sit on a thin stalk.
        axis = verts - np.array([pivot[0], 0.0, pivot[2]])
        axis[:, 1] = 0.0
        out += ((head_scale - 1.0) * NECK_SHARE * neck)[:, None] * axis

    if abs(torso_scale - 1.0) >= 1e-3:
        for head, tail, share in TORSO_SEGMENTS:
            if head not in names or head not in anchors or tail not in anchors:
                continue
            w = weights[:, names.index(head)]
            perp, length = _segment_offsets(verts, anchors[head], anchors[tail])
            out += ((torso_scale - 1.0) * share * w)[:, None] * perp

    forearm = arm_scale if forearm_scale is None else forearm_scale
    limb_specs = (
        (ARM_SEGMENTS[:1], arm_scale),
        (ARM_SEGMENTS[1:], forearm),
        (LEG_SEGMENTS, leg_scale),
    )
    limb_configs = [
        (head, tail, side, scale)
        for segments, scale in limb_specs
        if abs(scale - 1.0) >= 1e-3
        for side in SIDES
        for head, tail in segments
    ]
    for head, tail, side, scale in limb_configs:
        bone = f"{head}_{side}"
        tail_bone = f"{tail}_{side}"
        if bone not in names or bone not in anchors or tail_bone not in anchors:
            continue
        w = weights[:, names.index(bone)]
        if not w.any():
            continue
        perp, length = _segment_offsets(verts, anchors[bone], anchors[tail_bone])
        near = np.linalg.norm(perp, axis=1) < REACH * length
        out += ((scale - 1.0) * w * near)[:, None] * perp

    return out


def limb_radius(verts: np.ndarray, a: np.ndarray, b: np.ndarray) -> float | None:
    """Median distance to the axis of the vertices around the middle of a segment (0 when nothing is there)."""
    ab = b - a
    length = float(np.linalg.norm(ab))
    if length < 1e-6:
        return None
    t = (verts - a) @ ab / (length * length)
    perp = np.linalg.norm(verts - a - np.outer(t, ab), axis=1)
    sel = (t > 0.2) & (t < 0.8) & (perp < 0.3 * length)
    if sel.sum() < 8:
        return None
    return float(np.median(perp[sel]))


def torso_radius(verts: np.ndarray, joints: dict[str, np.ndarray]) -> float | None:
    """Median distance to the spine of the chest/belly vertices, arms left out (they hang or stick out sideways)."""
    if "Hips" not in joints or "Neck" not in joints or "Shoulder_Left" not in joints or "Shoulder_Right" not in joints:
        return None
    a, b = joints["Hips"], joints["Neck"]
    ab = b - a
    length = float(np.linalg.norm(ab))
    reach = 0.8 * abs(joints["Shoulder_Left"][0] - joints["Shoulder_Right"][0]) / 2
    if length < 1e-6 or reach < 1e-6:
        return None
    t = (verts - a) @ ab / (length * length)
    perp = np.linalg.norm(verts - a - np.outer(t, ab), axis=1)
    sel = (t > 0.25) & (t < 0.75) & (perp < reach)
    if sel.sum() < 8:
        return None
    return float(np.median(perp[sel]))


def suggest_torso(
    model_verts: np.ndarray,
    anchors: dict[str, np.ndarray],
    base_verts: np.ndarray,
    base_joints: dict[str, np.ndarray],
) -> float:
    m = torso_radius(model_verts, anchors)
    b = torso_radius(base_verts, base_joints)
    value = b / m if m and b else 1.0
    return round(float(np.clip(value, 1.0, MAX_TORSO)) * 20) / 20


def _segment_group_ratio(
    model_verts: np.ndarray,
    anchors: dict[str, np.ndarray],
    base_verts: np.ndarray,
    base_joints: dict[str, np.ndarray],
    segments: tuple[tuple[str, str], ...],
) -> float:
    ratios: list[float] = []
    for side in SIDES:
        for head, tail in segments:
            head_key = f"{head}_{side}"
            tail_key = f"{tail}_{side}"
            if head_key not in anchors or tail_key not in anchors:
                continue
            if head_key not in base_joints or tail_key not in base_joints:
                continue
            m = limb_radius(model_verts, anchors[head_key], anchors[tail_key])
            b = limb_radius(base_verts, base_joints[head_key], base_joints[tail_key])
            if m and b:
                ratios.append(b / m)
    if not ratios:
        return 1.0
    value = float(np.median(ratios))
    return round(float(np.clip(value, 1.0, MAX_SUGGEST)) * 20) / 20


def suggest(
    model_verts: np.ndarray,
    anchors: dict[str, np.ndarray],
    base_verts: np.ndarray,
    base_joints: dict[str, np.ndarray],
) -> tuple[float, float, float]:
    """(arm, forearm, leg) scales that bring the model's limbs to the base figure's thickness (never thinner, at
    most 1.6)."""
    arm = _segment_group_ratio(model_verts, anchors, base_verts, base_joints, ARM_SEGMENTS[:1])
    forearm = _segment_group_ratio(model_verts, anchors, base_verts, base_joints, ARM_SEGMENTS[1:])
    leg = _segment_group_ratio(model_verts, anchors, base_verts, base_joints, LEG_SEGMENTS)
    return arm, forearm, leg


_OTHER: tuple[tuple[str, str], ...] = (
    ("Hips", "Spine2"), ("Spine2", "Spine3"), ("Spine3", "Neck"), ("Neck", "Head"), ("Head", "HeadTop"),
)
_OTHER_SIDED: tuple[tuple[str, str], ...] = (
    ("Clavicle", "Shoulder"), ("Hand", "HandTip"), ("Ankle", "ToeTip"), ("Hips", "Thigh"),
)


def preview_weights(verts: np.ndarray, anchors: dict[str, np.ndarray]) -> tuple[np.ndarray, list[str]]:
    """Rough limb weights from the skeleton alone (no rig needed), for showing the thickness live.

    Every vertex is shared between the bone segments by inverse distance (power 6), so it is close to 1 in the middle
    of a limb and fades out around the shoulders, hips, hands and feet like real weights do."""
    segments: list[tuple[np.ndarray, np.ndarray]] = []
    names: list[str] = []
    for head, tail in _OTHER:
        if head in anchors and tail in anchors:
            segments.append((anchors[head], anchors[tail]))
            names.append(head)  # Hips, Spine2, Spine3: the torso thickness reads these
    for side in SIDES:
        for head, tail in ARM_SEGMENTS + LEG_SEGMENTS:
            head_side = f"{head}_{side}"
            tail_side = f"{tail}_{side}"
            if head_side in anchors and tail_side in anchors:
                segments.append((anchors[head_side], anchors[tail_side]))
                names.append(head_side)
        for head, tail in _OTHER_SIDED:
            a = anchors.get(f"{head}_{side}", anchors.get(head))
            b = anchors.get(f"{tail}_{side}")
            if a is not None and b is not None:
                segments.append((a, b))
                names.append(f"_{head}_{side}")
    dist = np.stack([np.linalg.norm(_segment_offsets(verts, a, b)[0], axis=1) for a, b in segments], axis=1)
    inv = 1.0 / np.maximum(dist, 1e-4) ** 6
    weights = inv / inv.sum(axis=1, keepdims=True)
    if "Head" in names and "Head" in anchors and "Shoulder_Left" in anchors:
        # The rig makes the head rigid: do the same, or the face gets dragged by the neck and shoulders.
        head = (verts[:, 1] > anchors["Head"][1]) & (np.abs(verts[:, 0]) < 0.6 * abs(anchors["Shoulder_Left"][0]))
        weights[head] = 0.0
        weights[head, names.index("Head")] = 1.0
    return weights, names


def preview(
    verts: np.ndarray,
    anchors: dict[str, np.ndarray],
    arm_scale: float,
    leg_scale: float,
    torso_scale: float = 1.0,
    head_scale: float = 1.0,
    forearm_scale: float | None = None,
    v_shape: float = 0.0,
    v_target: float | None = None,
) -> np.ndarray:
    forearm = arm_scale if forearm_scale is None else forearm_scale
    if max(abs(arm_scale - 1), abs(leg_scale - 1), abs(torso_scale - 1), abs(head_scale - 1), abs(forearm - 1),
           v_shape if v_target else 0.0) < 1e-3:
        return verts
    weights, names = preview_weights(verts, anchors)
    return inflate(verts, weights, names, anchors, arm_scale, leg_scale, torso_scale, head_scale, forearm, v_shape,
                   v_target)


def chest_half_width(verts: np.ndarray, anchors: dict[str, np.ndarray], at: float = 0.8) -> float | None:
    """Half width of the chest at `at` (0 hips - 1 neck): the 95th percentile of |x| in a thin slab, among the
    vertices that belong to the torso (rough skeleton weights), so wide sleeves and arms are left out."""
    if "Hips" not in anchors or "Neck" not in anchors:
        return None
    y = anchors["Hips"][1] + at * (anchors["Neck"][1] - anchors["Hips"][1])
    height = float(np.ptp(verts[:, 1]))
    sl = np.flatnonzero(np.abs(verts[:, 1] - y) < 0.012 * height)
    if len(sl) < 6:
        return None
    weights, names = preview_weights(verts[sl], anchors)
    torso = [i for i, n in enumerate(names) if n in ("Hips", "Spine2", "Spine3", "Neck") or n.startswith("_Clavicle")]
    keep = weights[:, torso].sum(axis=1) > 0.5
    if keep.sum() < 6:
        return None
    return float(np.percentile(np.abs(verts[sl[keep], 0]), 95))


def v_target(
    verts: np.ndarray,
    anchors: dict[str, np.ndarray],
    base_joints: dict[str, np.ndarray],
    arm_scale: float = 1.0,
) -> float | None:
    """Chest half width that reaches the inner side of the hanging arm in the game pose: the upper arm hangs from the
    base figure's shoulder joint, its inner side one arm radius closer to the body; 2 % of the height is kept free."""
    if "Shoulder_Left" not in anchors or "Elbow_Left" not in anchors or "Shoulder_Left" not in base_joints:
        return None
    radius = limb_radius(verts, anchors["Shoulder_Left"], anchors["Elbow_Left"])
    if not radius:
        return None
    height = float(np.ptp(verts[:, 1]))
    return float(abs(base_joints["Shoulder_Left"][0]) - radius * arm_scale - 0.02 * height)


DISNEY_STYLE: dict[str, float] = {"head": 0.212, "arm": 0.030, "forearm": 0.033, "thigh": 0.046, "torso": 0.076}
"""Median proportions of 30 humanoid figures of the game, as a share of the figure's height: head (neck to top),
upper arm, forearm and thigh radius, torso radius around the spine. Measured with the functions of this module."""


def head_ratio(verts: np.ndarray, anchors: dict[str, np.ndarray]) -> float:
    if "Neck" not in anchors:
        return 0.0
    height = float(np.ptp(verts[:, 1]))
    return float((verts[:, 1].max() - anchors["Neck"][1]) / max(height, 1e-9))


def disney_style(verts: np.ndarray, anchors: dict[str, np.ndarray]) -> dict[str, float]:
    """Scales that bring a model to the game's average proportions (never smaller than the model, capped)."""
    height = float(np.ptp(verts[:, 1]))

    def ratio(target: float, current: float | None, cap: float) -> float:
        if not current:
            return 1.0
        return round(float(np.clip(target * height / current, 1.0, cap)) * 20) / 20

    def limb(head: str, tail: str) -> float | None:
        values: list[float] = []
        for s in SIDES:
            head_key = f"{head}_{s}"
            tail_key = f"{tail}_{s}"
            if head_key not in anchors or tail_key not in anchors:
                continue
            r = limb_radius(verts, anchors[head_key], anchors[tail_key])
            if r:
                values.append(r)
        if not values:
            return None
        return float(np.median(values))

    head_now = head_ratio(verts, anchors) * height
    return {
        "head_scale": ratio(DISNEY_STYLE["head"], head_now, MAX_HEAD),
        "arm_scale": ratio(DISNEY_STYLE["arm"], limb("Shoulder", "Elbow"), MAX_SUGGEST),
        "forearm_scale": ratio(DISNEY_STYLE["forearm"], limb("Elbow", "Hand"), MAX_SUGGEST),
        "leg_scale": ratio(DISNEY_STYLE["thigh"], limb("Thigh", "Knee"), MAX_SUGGEST),
        "torso_scale": ratio(DISNEY_STYLE["torso"], torso_radius(verts, anchors), MAX_TORSO),
    }


def quick_game_pose(
    verts: np.ndarray,
    anchors: dict[str, np.ndarray],
    base_joints: dict[str, np.ndarray],
) -> np.ndarray:
    """The model moved into the game's rest pose (arms down): a live preview of what "Build the rig" will bake,
    cheap enough to follow every skeleton slider. It uses the rig's own fallback weights (distance to the bones,
    body zones, rigid head) so the shoulders and the chin move as they will once rigged."""
    from src.core.rig import bake_transforms
    from src.core.rigging import distance_weights, rigid_head
    from src.core.skeleton import heat_bones
    bake = bake_transforms(anchors, base_joints)
    names = [b[0] for b in heat_bones()]
    weights = rigid_head(verts, distance_weights(verts, anchors), names, anchors, lambda text: None)
    out = np.zeros_like(verts)
    total = np.zeros(len(verts))
    for col, name in enumerate(names):
        if name not in bake:
            continue
        m, t = bake[name]
        out += weights[:, col:col + 1] * (verts @ m + t)
        total += weights[:, col]
    return out / np.maximum(total, 1e-9)[:, None]


_ANCHOR_BONE: dict[str, str] = {
    "Hips": "Hips", "HipsLow": "Hips", "Spine2": "Spine2", "Spine3": "Spine3", "Neck": "Neck",
    "Head": "Head", "HeadTop": "Head", "Clavicle": "Clavicle", "ClavicleHeat": "Clavicle",
    "Shoulder": "Shoulder", "Elbow": "Elbow", "Hand": "Hand", "HandTip": "Hand", "Thigh": "Thigh",
    "Knee": "Knee", "Ankle": "Ankle", "AnkleTrue": "Ankle", "Ball": "Ball", "ToeTip": "Ball",
}


def posed_anchors(
    anchors: dict[str, np.ndarray],
    base_joints: dict[str, np.ndarray],
) -> dict[str, np.ndarray]:
    """The skeleton points moved like the model into the game's rest pose (each by the bone it belongs to), so the
    points stay on the model while "Preview in game pose" is on."""
    from src.core.rig import bake_transforms
    bake = bake_transforms(anchors, base_joints)
    out: dict[str, np.ndarray] = {}
    for name, point in anchors.items():
        head, _, side = name.partition("_")
        bone = _ANCHOR_BONE.get(head)
        if bone is None:
            continue
        key = f"{bone}_{side}" if side else bone
        if key not in bake:
            continue
        m, t = bake[key]
        out[name] = np.asarray(point, float) @ m + t
    return out

