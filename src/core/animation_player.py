"""Animation playback controller and pose generator for OpenGL viewport."""
from __future__ import annotations

import math
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from src.core.base_character import BaseCharacter
from src.core.blender_rig import AnimationTrack
from src.core.paths import BMS_SCRIPT, QUICKBMS
from src.core.rig import RigResult, skin
from src.core.skeleton import SIDES

_NO_WINDOW: int = getattr(subprocess, "CREATE_NO_WINDOW", 0)


@dataclass
class AnimationClip:
    name: str
    duration: float
    fps: float = 30.0
    evaluate_world: Callable[[BaseCharacter, np.ndarray, float], np.ndarray] | None = None
    custom_track: AnimationTrack | None = None

    @property
    def total_frames(self) -> int:
        return max(1, int(round(self.duration * self.fps)))


def _rot_x(angle_rad: float) -> np.ndarray:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, s], [0.0, -s, c]], dtype=np.float32)


def _rot_y(angle_rad: float) -> np.ndarray:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]], dtype=np.float32)


def _rot_z(angle_rad: float) -> np.ndarray:
    c, s = math.cos(angle_rad), math.sin(angle_rad)
    return np.array([[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float32)


def _find_bone(base: BaseCharacter, prefix: str, side: str = "") -> int:
    side_short = ("_L" if side == "Left" else "_R") if side else ""
    candidates: list[str] = []
    if side:
        candidates = [f"{prefix}_{side}", f"{prefix}{side_short}", f"{prefix}_{side.lower()}", f"{prefix}{side}"]
    else:
        candidates = [prefix, prefix.lower(), prefix.capitalize()]
    for candidate in candidates:
        try:
            return base.bone_index(candidate)
        except (KeyError, ValueError, AttributeError):
            pass
    for i, n in enumerate(base.bone_names):
        nl = n.lower()
        if side and any(nl == c.lower() for c in candidates):
            return i
        if not side and nl.startswith(prefix.lower()):
            return i
    return 0


def _make_transform(rot: np.ndarray, pivot: np.ndarray, offset: np.ndarray | None = None) -> np.ndarray:
    """Create a 4x4 affine matrix rotating around `pivot` with an optional translation offset."""
    mat = np.eye(4, dtype=np.float32)
    mat[:3, :3] = rot
    t = pivot - pivot @ rot
    if offset is not None:
        t = t + offset
    mat[3, :3] = t
    return mat


def _matches_side(name: str, side: str) -> bool:
    """Check if bone `name` belongs to `side` ('Left' or 'Right')."""
    if not side:
        return True
    side_suffix = (side, "_L" if side == "Left" else "_R")
    nl = name.lower()
    return any(nl.endswith(sfx.lower()) for sfx in side_suffix)


def _apply_bone_transform(
    base: BaseCharacter,
    posed: np.ndarray,
    prefixes: tuple[str, ...],
    mat: np.ndarray,
    side: str = "",
    source: np.ndarray | None = None,
) -> None:
    """Apply transformation matrix `mat` to all bones matching `prefixes` and optional `side`."""
    src = posed if source is None else source
    for i, name in enumerate(base.bone_names):
        if not name.startswith(prefixes):
            continue
        if side and not _matches_side(name, side):
            continue
        posed[i] = src[i] @ mat


def _transform_bone_group(
    base: BaseCharacter,
    posed: np.ndarray,
    pivot_bone: str,
    prefixes: tuple[str, ...],
    rot: np.ndarray,
    side: str = "",
    source: np.ndarray | None = None,
    offset: np.ndarray | None = None,
) -> np.ndarray:
    """Rotate a group of bones around a pivot bone, optionally translating."""
    src = posed if source is None else source
    idx = _find_bone(base, pivot_bone, side)
    pivot = src[idx][3, :3]
    mat = _make_transform(rot, pivot, offset)
    _apply_bone_transform(base, posed, prefixes, mat, side=side, source=src)
    return mat


# =============================================================================
# PROCEDURAL MOTION EVALUATORS
# =============================================================================

def evaluate_procedural_roll(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate a dynamic 360-degree tumbling dive roll (forward roll)."""
    cycle = 1.2
    u = (t % cycle) / cycle  # 0.0 to 1.0

    hips_idx = _find_bone(base, "Hips")
    pivot_hips = world[hips_idx][3, :3]

    roll_angle = 2.0 * math.pi * u
    drop_y = math.sin(u * math.pi) * 0.55
    fwd_z = math.sin(u * math.pi) * 0.40

    rx = _rot_x(roll_angle)
    offset = np.array([0.0, -drop_y, fwd_z], dtype=np.float32)
    rot_all = _make_transform(rx, pivot_hips, offset)
    posed = world @ rot_all

    tuck = math.sin(u * math.pi) ** 2
    if tuck <= 0.04:
        return posed

    r_thigh = _rot_x(math.radians(65.0 * tuck))
    r_knee = _rot_x(math.radians(-90.0 * tuck))
    r_arm = _rot_x(math.radians(45.0 * tuck))

    for side, _ in SIDES:
        _transform_bone_group(base, posed, "Knee", ("Knee", "Ankle", "Ball", "Toes"), r_knee, side=side)
        _transform_bone_group(base, posed, "Thigh", ("Thigh",), r_thigh, side=side)
        _transform_bone_group(base, posed, "Shoulder", ("Shoulder", "Elbow", "Hand"), r_arm, side=side)

    return posed


def _jump_phase_params(u: float) -> tuple[float, float, float]:
    """Return (h_offset, knee_angle, arm_factor) for phase u in [0, 1)."""
    if u < 0.2:
        crouch = math.sin((u / 0.2) * math.pi * 0.5) * 0.22
        return -crouch, crouch * 2.2, 1.0
    if u < 0.8:
        p = (u - 0.2) / 0.6
        s = math.sin(p * math.pi)
        return s * 0.85, s * 0.7, 1.0
    crouch = math.sin((1.0 - (u - 0.8) / 0.2) * math.pi * 0.5) * 0.2
    return -crouch, crouch * 1.8, 0.2


def evaluate_procedural_jump(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate athletic vertical jump with crouch, launch, mid-air tuck and landing."""
    cycle = 1.4
    u = (t % cycle) / cycle
    h_offset, knee_angle, arm_factor = _jump_phase_params(u)

    t_mat = np.eye(4, dtype=np.float32)
    t_mat[3, 1] = h_offset
    posed = world @ t_mat

    r_knee = _rot_x(-knee_angle)
    arm_out = math.radians(25.0 * arm_factor)

    for side, _ in SIDES:
        _transform_bone_group(base, posed, "Knee", ("Knee", "Ankle", "Ball", "Toes"), r_knee, side=side)
        r_sh = _rot_z(arm_out if side == "Left" else -arm_out)
        _transform_bone_group(base, posed, "Shoulder", ("Shoulder", "Elbow", "Hand"), r_sh, side=side)

    return posed


def evaluate_procedural_combat_stance(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate athletic combat guard stance (Saber On / ready posture)."""
    posed = world.copy()
    breathe = math.sin(2.0 * math.pi * 0.5 * t)
    spine_sway = breathe * math.radians(1.5)
    r_spine = _rot_y(math.radians(-12.0)) @ _rot_x(spine_sway)

    _transform_bone_group(base, posed, "Hips", ("Spine", "Neck", "Head"), r_spine, source=world)

    for side, _ in SIDES:
        arm_y = math.radians(-20.0 if side == "Right" else 20.0)
        r_arm = _rot_x(math.radians(-35.0)) @ _rot_y(arm_y)
        _transform_bone_group(
            base, posed, "Shoulder",
            ("Shoulder", "Elbow", "Hand", "Thumb", "Index", "Middle"),
            r_arm, side=side, source=world,
        )

    return posed


def _combo_1_angles(u: float) -> tuple[float, float, float]:
    """Return (arm_z, arm_x, spine_y) in radians for phase u in [0, 1)."""
    if u < 0.35:
        p = u / 0.35
        return math.radians(80.0 * p), math.radians(-30.0 * p), math.radians(-20.0 * p)
    if u < 0.65:
        p = (u - 0.35) / 0.3
        return math.radians(80.0 - 130.0 * p), math.radians(-30.0 + 75.0 * p), math.radians(-20.0 + 45.0 * p)
    p = (u - 0.65) / 0.35
    inv_p = 1.0 - p
    return math.radians(-50.0 * inv_p), math.radians(45.0 * inv_p), math.radians(25.0 * inv_p)


def evaluate_procedural_combo_1(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate rapid horizontal slash attack (Combo Y)."""
    posed = world.copy()
    u = (t % 0.8) / 0.8
    arm_z, arm_x, spine_y = _combo_1_angles(u)

    _transform_bone_group(base, posed, "Hips", ("Spine", "Neck", "Head"), _rot_y(spine_y), source=world)

    r_arm = _rot_z(-arm_z) @ _rot_x(arm_x)
    _transform_bone_group(
        base, posed, "Shoulder",
        ("Shoulder", "Elbow", "Forearm", "Hand", "Thumb", "Index", "Middle"),
        r_arm, side="Right", source=world,
    )
    return posed


evaluate_procedural_attack = evaluate_procedural_combo_1


def _combo_2_angles(u: float) -> tuple[float, float]:
    """Return (arm_x, arm_y) in radians for phase u in [0, 1)."""
    if u < 0.3:
        p = u / 0.3
        return math.radians(60.0 * p), math.radians(-40.0 * p)
    if u < 0.6:
        p = (u - 0.3) / 0.3
        return math.radians(60.0 - 110.0 * p), math.radians(-40.0 + 80.0 * p)
    p = (u - 0.6) / 0.3
    inv_p = 1.0 - p
    return math.radians(-50.0 * inv_p), math.radians(40.0 * inv_p)


def evaluate_procedural_combo_2(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate reverse cross slash combo (Combo YY)."""
    posed = world.copy()
    u = (t % 0.9) / 0.9
    arm_x, arm_y = _combo_2_angles(u)

    r_arm = _rot_x(arm_x) @ _rot_y(arm_y)
    _transform_bone_group(
        base, posed, "Shoulder",
        ("Shoulder", "Elbow", "Forearm", "Hand", "Thumb", "Index", "Middle"),
        r_arm, side="Right", source=world,
    )
    return posed


def _helmbreaker_params(u: float) -> tuple[float, float]:
    """Return (h_off, arm_lift) for phase u in [0, 1)."""
    if u < 0.4:
        p = u / 0.4
        return math.sin(p * math.pi * 0.5) * 0.65, math.radians(-110.0 * p)
    if u < 0.65:
        p = (u - 0.4) / 0.25
        h = 0.65 * (1.0 - p) - 0.25 * math.sin(p * math.pi * 0.5)
        return h, math.radians(-110.0 + 160.0 * p)
    p = (u - 0.65) / 0.35
    inv_p = 1.0 - p
    return -0.25 * inv_p, math.radians(50.0 * inv_p)


def evaluate_procedural_helmbreaker(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate heavy jumping overhead smash (Helmbreaker / Ground Slam)."""
    cycle = 1.4
    u = (t % cycle) / cycle
    h_off, arm_lift = _helmbreaker_params(u)

    t_mat = np.eye(4, dtype=np.float32)
    t_mat[3, 1] = h_off
    posed = world @ t_mat

    r_arm = _rot_x(arm_lift)
    for side, _ in SIDES:
        _transform_bone_group(base, posed, "Shoulder", ("Shoulder", "Elbow", "Hand"), r_arm, side=side)

    return posed


def evaluate_procedural_sprint(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate aggressive high-speed sprint cycle."""
    cycle = 0.65
    phase = 2.0 * math.pi * (1.0 / cycle) * t
    posed = world.copy()

    r_lean = _rot_x(math.radians(16.0))
    _transform_bone_group(base, posed, "Hips", ("Spine", "Neck", "Head"), r_lean, source=world)

    leg_amp = math.radians(52.0)
    arm_amp = math.radians(50.0)

    for side, sx in SIDES:
        leg_phase = phase if sx > 0 else (phase + math.pi)
        r_thigh = _rot_x(math.sin(leg_phase) * leg_amp)
        _transform_bone_group(
            base, posed, "Thigh",
            ("Thigh", "Knee", "Ankle", "Ball", "Toes"),
            r_thigh, side=side, source=world,
        )

        arm_phase = leg_phase + math.pi
        r_shoulder = _rot_x(math.sin(arm_phase) * arm_amp)
        _transform_bone_group(
            base, posed, "Shoulder",
            ("Shoulder", "Elbow", "Forearm", "Hand"),
            r_shoulder, side=side, source=world,
        )

    return posed


def evaluate_procedural_walk(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate a dynamic, continuous walk cycle."""
    posed = world.copy()
    phase = 2.0 * math.pi * 1.0 * t

    leg_amp = math.radians(35.0)
    arm_amp = math.radians(30.0)

    for side, sx in SIDES:
        leg_phase = phase if sx > 0 else (phase + math.pi)
        r_thigh = _rot_x(math.sin(leg_phase) * leg_amp)
        _transform_bone_group(
            base, posed, "Thigh",
            ("Thigh", "Knee", "Ankle", "Ball", "Toes"),
            r_thigh, side=side, source=world,
        )

        arm_phase = leg_phase + math.pi
        r_shoulder = _rot_x(math.sin(arm_phase) * arm_amp)
        _transform_bone_group(
            base, posed, "Shoulder",
            ("Shoulder", "Elbow", "Forearm", "Hand", "Thumb", "Index", "Middle"),
            r_shoulder, side=side, source=world,
        )

    return posed


def evaluate_procedural_idle(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate natural breathing / idle posture."""
    posed = world.copy()
    breathe = math.sin(2.0 * math.pi * 0.4 * t)
    spine_angle = breathe * math.radians(2.0)
    r_spine = _rot_x(spine_angle)

    for i, n in enumerate(base.bone_names):
        if n.startswith(("Spine", "Neck", "Head", "Clavicle")):
            rot = _make_transform(r_spine, world[i][3, :3])
            posed[i] = world[i] @ rot

    return posed


def evaluate_procedural_celebrate(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate victory celebration (arms raised high in triumph)."""
    posed = world.copy()
    cycle = 2.0
    u = (t % cycle) / cycle
    sway = math.sin(u * 2.0 * math.pi) * math.radians(4.0)

    r_sp = _rot_x(math.radians(-6.0)) @ _rot_z(sway)
    _transform_bone_group(base, posed, "Hips", ("Spine", "Neck", "Head"), r_sp, source=world)

    for side, _ in SIDES:
        arm_z = math.radians(-30.0 if side == "Right" else 30.0)
        r_sh = _rot_x(math.radians(-125.0)) @ _rot_z(arm_z)
        _transform_bone_group(base, posed, "Shoulder", ("Shoulder", "Elbow", "Hand"), r_sh, side=side, source=world)

    return posed


def evaluate_procedural_hit_react(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate damage recoil / hit react."""
    cycle = 0.7
    u = (t % cycle) / cycle
    posed = world.copy()

    p = u / 0.25 if u < 0.25 else (1.0 - (u - 0.25) / 0.75)
    recoil = math.radians(-22.0 * p)
    _transform_bone_group(base, posed, "Hips", ("Spine", "Neck", "Head"), _rot_x(recoil), source=world)

    return posed


def evaluate_procedural_death(base: BaseCharacter, world: np.ndarray, t: float) -> np.ndarray:
    """Evaluate knockout / defeat collapse."""
    cycle = 1.6
    u = min(1.0, (t % cycle) / (cycle * 0.8))  # settle at end

    drop = math.sin(u * math.pi * 0.5) * 0.85
    fall_back = math.radians(-75.0 * u)
    hips_idx = _find_bone(base, "Hips")
    p_hips = world[hips_idx][3, :3]
    offset = np.array([0.0, -drop, -0.3 * u], dtype=np.float32)
    m_fall = _make_transform(_rot_x(fall_back), p_hips, offset)

    return world @ m_fall


# =============================================================================
# CHARACTER MOVESET SCANNING & RESOLUTION
# =============================================================================

def scan_game_motions(base: BaseCharacter, game_dir: Path | None = None) -> list[str]:
    """Scan the base character's game archive for real motion files (.oct)."""
    if not game_dir:
        return []
    archive = base.game_model_zip(game_dir)
    if not archive.exists():
        archive = archive.with_name(archive.name + ".orig")
    if not archive.exists() or not QUICKBMS.exists() or not BMS_SCRIPT.exists():
        return []
    try:
        out = subprocess.run([str(QUICKBMS), "-l", str(BMS_SCRIPT), str(archive)],
                             capture_output=True, text=True, creationflags=_NO_WINDOW).stdout
        motions = [line.split()[2].split("\\")[-1] for line in out.splitlines()
                   if len(line.split()) >= 3 and line.split()[2].lower().endswith(".oct")
                   and "motions" in line.split()[2].lower()]
        return sorted(set(motions))
    except (subprocess.SubprocessError, OSError, ValueError):
        return []


def _map_motion_evaluator(stem: str) -> Callable[[BaseCharacter, np.ndarray, float], np.ndarray]:
    """Map motion file stem to the closest procedural motion evaluator."""
    sl = stem.lower()
    if any(k in sl for k in ("roll", "diveroll", "dodge")):
        return evaluate_procedural_roll
    if any(k in sl for k in ("jump", "air", "fall", "land")):
        return evaluate_procedural_jump
    if any(k in sl for k in ("run", "sprint")):
        return evaluate_procedural_sprint
    if any(k in sl for k in ("walk", "patrol")):
        return evaluate_procedural_walk
    if any(k in sl for k in ("combo", "atk", "slash", "swing", "strike")):
        return evaluate_procedural_combo_1
    if any(k in sl for k in ("smash", "helmbreaker", "slam")):
        return evaluate_procedural_helmbreaker
    if any(k in sl for k in ("stance", "guard", "block")):
        return evaluate_procedural_combat_stance
    if any(k in sl for k in ("rct", "hit", "stmb")):
        return evaluate_procedural_hit_react
    if any(k in sl for k in ("death", "fail", "ko")):
        return evaluate_procedural_death
    if any(k in sl for k in ("celebrate", "taunt", "cheer")):
        return evaluate_procedural_celebrate
    return evaluate_procedural_idle


def get_character_animation_clips(base: BaseCharacter, game_dir: Path | None = None) -> dict[str, AnimationClip]:
    """Build the comprehensive, character-specific animation suite for the selected base figure."""
    prefix = base.actor.split("_")[-1].lower() if "_" in base.actor else base.actor.lower()

    # Core canonical moveset tailored to the character
    clips: dict[str, AnimationClip] = {
        f"Roll / Dive Roll (Rouler) [{prefix}_atk_diveroll]": AnimationClip(
            name=f"Roll / Dive Roll (Rouler) [{prefix}_atk_diveroll]",
            duration=1.2, fps=30.0, evaluate_world=evaluate_procedural_roll
        ),
        f"Jump & Aerial (Saut) [{prefix}_bm_jump]": AnimationClip(
            name=f"Jump & Aerial (Saut) [{prefix}_bm_jump]",
            duration=1.4, fps=30.0, evaluate_world=evaluate_procedural_jump
        ),
        f"Combat Guard (Garde) [{prefix}_bm_idle_stance]": AnimationClip(
            name=f"Combat Guard (Garde) [{prefix}_bm_idle_stance]",
            duration=2.0, fps=30.0, evaluate_world=evaluate_procedural_combat_stance
        ),
        f"Combo Attack 1 (Attaque 1) [{prefix}_atk_combo_y]": AnimationClip(
            name=f"Combo Attack 1 (Attaque 1) [{prefix}_atk_combo_y]",
            duration=0.8, fps=30.0, evaluate_world=evaluate_procedural_combo_1
        ),
        f"Combo Attack 2 (Attaque 2) [{prefix}_atk_combo_yy]": AnimationClip(
            name=f"Combo Attack 2 (Attaque 2) [{prefix}_atk_combo_yy]",
            duration=0.9, fps=30.0, evaluate_world=evaluate_procedural_combo_2
        ),
        f"Heavy Smash / Helmbreaker [{prefix}_atk_helmbreaker]": AnimationClip(
            name=f"Heavy Smash / Helmbreaker [{prefix}_atk_helmbreaker]",
            duration=1.4, fps=30.0, evaluate_world=evaluate_procedural_helmbreaker
        ),
        f"Sprint / Fast Run (Course) [{prefix}_bm_run]": AnimationClip(
            name=f"Sprint / Fast Run (Course) [{prefix}_bm_run]",
            duration=0.65, fps=30.0, evaluate_world=evaluate_procedural_sprint
        ),
        f"Walk (Marche) [{prefix}_bm_walk]": AnimationClip(
            name=f"Walk (Marche) [{prefix}_bm_walk]",
            duration=1.0, fps=30.0, evaluate_world=evaluate_procedural_walk
        ),
        f"Idle Breathing (Attente) [{prefix}_bm_idle]": AnimationClip(
            name=f"Idle Breathing (Attente) [{prefix}_bm_idle]",
            duration=2.5, fps=30.0, evaluate_world=evaluate_procedural_idle
        ),
        f"Victory Celebrate (Victoire) [{prefix}_mnt_celebrate]": AnimationClip(
            name=f"Victory Celebrate (Victoire) [{prefix}_mnt_celebrate]",
            duration=2.0, fps=30.0, evaluate_world=evaluate_procedural_celebrate
        ),
        f"Hit React (Dégâts) [{prefix}_rct_hit]": AnimationClip(
            name=f"Hit React (Dégâts) [{prefix}_rct_hit]",
            duration=0.7, fps=30.0, evaluate_world=evaluate_procedural_hit_react
        ),
        f"Knockout / Defeat (K.O.) [{prefix}_rct_death]": AnimationClip(
            name=f"Knockout / Defeat (K.O.) [{prefix}_rct_death]",
            duration=1.6, fps=30.0, evaluate_world=evaluate_procedural_death
        ),
    }

    # Optional: scan real motion names from game archive and map key motions
    scanned = scan_game_motions(base, game_dir)
    for m in scanned[:30]:  # Register top game motion clips
        stem = m[:-4] if m.endswith(".oct") else m
        if any(stem in k for k in clips):
            continue
        evaluator = _map_motion_evaluator(stem)
        name = f"Game Motion: {stem}"
        clips[name] = AnimationClip(name=name, duration=1.2, fps=30.0, evaluate_world=evaluator)

    return clips


BUILTIN_CLIPS: dict[str, AnimationClip] = {
    "Roll / Dive Roll (Rouler)": AnimationClip(
        name="Roll / Dive Roll (Rouler)", duration=1.2, fps=30.0, evaluate_world=evaluate_procedural_roll
    ),
    "Walk": AnimationClip(name="Walk", duration=1.0, fps=30.0, evaluate_world=evaluate_procedural_walk),
    "Idle": AnimationClip(name="Idle", duration=2.5, fps=30.0, evaluate_world=evaluate_procedural_idle),
    "Attack Combo": AnimationClip(name="Attack Combo", duration=0.8, fps=30.0, evaluate_world=evaluate_procedural_combo_1),
    "Jump": AnimationClip(name="Jump", duration=1.4, fps=30.0, evaluate_world=evaluate_procedural_jump),
    "Sprint": AnimationClip(name="Sprint", duration=0.65, fps=30.0, evaluate_world=evaluate_procedural_sprint),
}


FINGER_PREFIXES: tuple[str, ...] = ("Thumb", "Index", "Middle")


def follow_hands(base: BaseCharacter, world: np.ndarray, posed: np.ndarray) -> np.ndarray:
    """The procedural clips move the hands but not the finger bones: left alone, the fingers stay behind at the bind
    pose and tear the hands. Each finger bone takes the motion of its hand (no clip curls the fingers)."""
    out = posed.copy()
    for i, name in enumerate(base.bone_names):
        if not name.startswith(FINGER_PREFIXES) or "_" not in name:
            continue
        try:
            hand = base.bone_index("Hand_" + name.rsplit("_", 1)[1])
        except ValueError:
            continue
        out[i] = world[i] @ (np.linalg.inv(world[hand]) @ posed[hand])
    return out


class AnimationPlayer:
    """Controls animation playback, scrubbing, and frame evaluation."""

    def __init__(self, fps: float = 30.0) -> None:
        self.fps: float = fps
        self.is_playing: bool = False
        self.loop: bool = True
        self.speed: float = 1.0
        self.current_time: float = 0.0
        self._last_perf_time: float | None = None
        self.active_clip: AnimationClip | None = BUILTIN_CLIPS["Roll / Dive Roll (Rouler)"]

    @property
    def duration(self) -> float:
        return self.active_clip.duration if self.active_clip else 1.0

    @property
    def total_frames(self) -> int:
        return max(1, int(round(self.duration * self.fps)))

    @property
    def current_frame(self) -> int:
        f = int(round(self.current_time * self.fps))
        return min(max(0, f), self.total_frames - 1)

    def set_clip(self, clip: AnimationClip | None) -> None:
        self.active_clip = clip
        self.current_time = 0.0
        self._last_perf_time = None

    def play(self) -> None:
        self.is_playing = True
        self._last_perf_time = time.perf_counter()

    def pause(self) -> None:
        self.is_playing = False
        self._last_perf_time = None

    def toggle_play(self) -> None:
        if self.is_playing:
            self.pause()
        else:
            self.play()

    def stop(self) -> None:
        self.is_playing = False
        self.current_time = 0.0
        self._last_perf_time = None

    def seek_frame(self, frame: int) -> None:
        target = max(0, min(frame, self.total_frames - 1))
        self.current_time = float(target) / self.fps
        if self.current_time > self.duration:
            self.current_time = self.duration

    def seek_time(self, t: float) -> None:
        if self.duration <= 0:
            self.current_time = 0.0
            return
        if self.loop:
            self.current_time = t % self.duration
        else:
            self.current_time = max(0.0, min(t, self.duration))

    def tick(self) -> bool:
        """Step playback based on real time clock. Returns True if time changed."""
        if not self.is_playing:
            return False

        now = time.perf_counter()
        if self._last_perf_time is None:
            self._last_perf_time = now
            return False

        dt = (now - self._last_perf_time) * self.speed
        self._last_perf_time = now

        new_t = self.current_time + dt
        if new_t >= self.duration:
            if self.loop:
                self.current_time = new_t % self.duration
            else:
                self.current_time = self.duration
                self.pause()
        else:
            self.current_time = new_t
        return True

    def get_current_posed_world(self, base: BaseCharacter) -> np.ndarray:
        """Return the current posed bone-to-world matrices (B, 4, 4) for the active animation."""
        world = base.bind_world
        if self.active_clip is None:
            return world

        if self.active_clip.evaluate_world is not None:
            return follow_hands(base, world, self.active_clip.evaluate_world(base, world, self.current_time))

        if self.active_clip.custom_track is None:
            return world

        bone_poses = self.active_clip.custom_track.sample(self.current_time)
        posed_world = world.copy()
        for bone_name, (pos, rot) in bone_poses.items():
            try:
                idx = base.bone_index(bone_name)
                m = _make_transform(rot, world[idx][3, :3], pos)
                posed_world[idx] = world[idx] @ m
            except (KeyError, ValueError):
                pass
        return posed_world

    def evaluate_pose_and_world(self, rig: RigResult) -> tuple[np.ndarray, np.ndarray]:
        """Compute deformed mesh vertex positions and posed_world for the current frame."""
        posed_world = self.get_current_posed_world(rig.base)
        posed_verts = skin(rig.baked, rig.bone_idx, rig.bone_w, rig.base.bind_world, posed_world)
        return posed_verts, posed_world

    def evaluate_pose(self, rig: RigResult) -> np.ndarray:
        """Compute deformed mesh vertex positions for the current playback frame."""
        verts, _ = self.evaluate_pose_and_world(rig)
        return verts
