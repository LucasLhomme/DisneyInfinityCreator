# Disney Infinity Creator

Desktop app (Python) that turns a downloaded 3D model (Sketchfab, etc.) into a playable character for
*Disney Infinity 3.0 Gold Edition*, shipped as a self-contained CrabeLoader mod.

## Run

```powershell
.\run.ps1
```

Creates `.venv` on first launch and installs `requirements.txt`. Blender (4.x) is recommended for good skinning
weights; without it the tool falls back to distance-to-bone weights.

## Usage

0. **Base**: pick the figure your character is built on, among the 99 playable figures of the game (searchable,
   3D preview). ● standard skeleton, ◐ adapted (some bones stand in for others), ✕ not humanoid (cannot be used).
   The character keeps that figure's skeleton, animations and moveset.
1. **Model**: import a `.zip`, `.obj`, `.glb` or `.gltf` in T-pose. All textures are packed into one atlas. The
   orientation is detected automatically (use the ↻ buttons to correct it).
2. **Skeleton**: joints are placed on the model automatically; the sliders adjust shoulders, wrists, neck, head,
   hips, legs, knees and ankles.
3. **Rig & Export**: "Build the rig", preview the poses (in-game pose, arms up, walk), then "Install into the game".
   The mod is written to `<game>/mods/<name>/` (any previous version is moved to `backups/`) and checked.
   In game: F5 > Heroes > ★ Modded Characters.

The base figures ship with Creator (`src/assets/bases/`, about 57 MB): browsing, previewing and rigging never read
the game. Only the install step uses the game folder, as its destination and for the texture archive it rebuilds.

## How it works

The character becomes a new actor (e.g. `MAR_Mari`), a clone of the base figure: same skeleton, animations and
moveset, new mesh; the base itself is left untouched and the clone gets a tile of its own in the character grid.
The mesh is baked into the base's bind pose (joints lined up), then skinned on the base's own bones, whose matrices
are left untouched. Joints a figure lacks (no ankle bone, a dress instead of thighs) are mapped onto the nearest
bone it has (`src/core/skeleton_map.py`).

| Mod file | Role |
| :--- | :--- |
| `characters/<actor>/*.oct .vbuf .ibuf` | Mesh, skinning, bounds; every other primitive of the base is emptied |
| `characters/<actor>/*.mtb` | One skinned material per slot, with a cache hash and textures of its own |
| `characters/<actor>/*.dnax .bent .animtreeoverrides` | Actor definition, repointed at the clone |
| `textures/<xx>.zip` | Rebuilt encrypted texture archive (vanilla + diffuse + normal map) |
| `skilltrees/ActorList.patch`, `DataMap.patch` | Declare the actor in the game databases |
| `characters/<Actor>.lua` | Virtual figure (Virtual Reader), with the base's progression tree |
| `<name>.lua`, `mod.json` | CrabeLoader entry point, CrabeMenu registration |

## Layout

- `src/core/`: pure logic
  - `octane_scene.py`, `luac.py`, `material_bundle.py`: lossless readers/writers for the game's .oct/.bent,
    compiled Lua (.dnax) and material bundles (byte-identical round trip on every shipped file)
  - `base_character.py`, `base_pack.py`, `roster.py`, `skeleton_map.py`: base figures and their skeletons
  - `model.py`, `skeleton.py`, `rig.py`, `rigging.py`: the imported model, its joints and skinning
  - `octane.py`, `exporter.py`, `mod_writer.py`, `textures.py`: the mod output
- `src/render/`: offscreen OpenGL viewport
- `src/ui/`: customtkinter interface
- `src/scripts/blender_heat_weights.py`: headless Blender step (bone-heat weights)
- `src/assets/`: `bases/` (the base pack), `roster.json`, `shader_layouts.json`, `templates/skinned_body.mtb`
- `src/tools/`: QuickBMS and the archive re-encrypter

## Regenerating the assets (developers)

Each script reads a game install or its decrypted files once; the app itself never does.

| Script | Output |
| :--- | :--- |
| `tools/build_roster.py <vr.lua> <actors.lua>` | `roster.json`, from decompiled `virtualreaderpc_data.lua` and `toybox_actors.lua` |
| `tools/build_shader_table.py <decrypted root>` | `shader_layouts.json`, texture slot layout of each shader |
| `tools/build_base_pack.py <game folder>` | `bases/`, every figure's model, .dnax, animtree and preview textures |
