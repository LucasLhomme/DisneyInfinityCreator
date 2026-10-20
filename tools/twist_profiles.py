"""Developer script: measure how the official figures share limb weights with their helper bones.

Usage: python tools/twist_profiles.py (needs src/assets/bases); prints the median share of each bone along each limb.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.base_character import S1_STRIDE, BaseCharacter
from src.core.roster import find_entry

INDEX_PATH = PROJECT_ROOT / "src" / "assets" / "bases" / "index.json"
OUTPUT_PATH = PROJECT_ROOT / "build" / "twist_profiles.json"

GROUPS: dict[str, tuple[tuple[str, ...], str, str]] = {
    "upper_arm": (("Shoulder", "Shoulder_Spin", "Shoulder_OL"), "Shoulder", "Elbow"),
    "forearm": (("Elbow", "Forearm_OL", "Elbow_OL"), "Elbow", "Hand"),
    "thigh": (("Thigh", "Thigh_OL"), "Thigh", "Knee"),
}


def compute_twist_profiles() -> dict[str, Any]:
    if not INDEX_PATH.is_file():
        raise FileNotFoundError(f"{INDEX_PATH} not found: base assets required.")

    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_data = json.load(f)

    bins = np.linspace(-0.2, 1.0, 13)
    results: dict[str, list[np.ndarray]] = {group: [] for group in GROUPS}

    for actor, row in index_data.items():
        if row.get("status", {}).get("state") != "standard":
            continue

        entry = find_entry(actor)
        if entry is None:
            continue

        base = BaseCharacter.from_pack(entry)
        primitive = base.body_primitive
        vertex_count = primitive.vertex_count

        s1_data = np.frombuffer(
            base._vbuf[primitive.s1_offset:primitive.s1_offset + vertex_count * S1_STRIDE],
            dtype=np.uint8,
        ).reshape(vertex_count, S1_STRIDE)

        joint_indices = s1_data[:, 0:4].astype(int)
        weights = s1_data[:, 4:8] / 255.0
        vertices = base.body_mesh[0]
        bone_names = list(base.bone_names)
        joints = base.joints

        weight_matrix = np.zeros((vertex_count, len(bone_names)), dtype=float)
        for k in range(4):
            np.add.at(weight_matrix, (np.arange(vertex_count), joint_indices[:, k]), weights[:, k])

        for side, _ in (("Left", 1), ("Right", -1)):
            for group, (bones, start_joint, end_joint) in GROUPS.items():
                cols = [
                    bone_names.index(f"{b}_{side}") if f"{b}_{side}" in bone_names else None
                    for b in bones
                ]
                if cols[0] is None or cols[1] is None:
                    continue

                group_weights = np.stack(
                    [weight_matrix[:, c] if c is not None else np.zeros(vertex_count) for c in cols],
                    axis=1,
                )
                total_weight = group_weights.sum(axis=1)
                start_pos = joints[f"{start_joint}_{side}"]
                end_pos = joints[f"{end_joint}_{side}"]
                axis = end_pos - start_pos
                axis_length_sq = np.dot(axis, axis)
                if axis_length_sq < 1e-12:
                    continue

                t_param = ((vertices - start_pos) @ axis) / axis_length_sq
                valid_mask = total_weight > 0.3

                profile = np.full((len(bins) - 1, len(bones)), np.nan)
                for i, (lo, hi) in enumerate(zip(bins[:-1], bins[1:])):
                    in_bin = valid_mask & (t_param >= lo) & (t_param < hi)
                    if in_bin.sum() > 3:
                        norm_weights = group_weights[in_bin] / total_weight[in_bin, None]
                        profile[i] = norm_weights.mean(axis=0)

                results[group].append(profile)

    output: dict[str, Any] = {
        "t": list(np.round((bins[:-1] + bins[1:]) / 2.0, 3)),
    }

    for group, profiles in results.items():
        if not profiles:
            continue
        median_profile = np.nanmedian(np.array(profiles), axis=0)
        median_profile = np.nan_to_num(median_profile)
        output[group] = {
            "bones": GROUPS[group][0],
            "shares": np.round(median_profile, 3).tolist(),
            "n": len(profiles),
        }
        print(f"Group {group}: {len(profiles)} samples")
        print(np.round(median_profile, 2).T)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)

    return output


def main() -> None:
    compute_twist_profiles()


if __name__ == "__main__":
    main()
