# Disney Infinity Creator

Turn any 3D model into a playable character for **Disney Infinity 3.0 Gold Edition (PC)**.

Import a model (a Sketchfab download, your own Blender work…) and pick one of the game's figures to build it on.
Creator fits a skeleton to your model and rigs it. You then preview it in motion, and it installs as a mod.
Your character then shows up in the game as a **new figure of its own**: it plays with the moves, animations and
abilities of the figure you picked, and no original character is replaced.

> Fan-made tool, not affiliated with or endorsed by Disney, Avalanche Software or any rights holder.
> You need your own copy of the game.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Creating a character, step by step](#creating-a-character-step-by-step)
- [Playing your character](#playing-your-character)
- [Tips for good results](#tips-for-good-results)
- [How it works](#how-it-works)
- [Limitations](#limitations)
- [Troubleshooting](#troubleshooting)
- [For developers](#for-developers)
- [The DIM2 Modding Ecosystem](#the-dim2-modding-ecosystem)
- [Credits](#credits)
- [Support & Sponsor](#support--sponsor)

---

## Features

- **99 base figures to choose from.** All the playable figures of Disney Infinity 3.0: Marvel, Star Wars, Disney
  and Pixar characters, including the 1.0 and 2.0 figures. The list is searchable, and each figure comes with a
  textured 3D preview.
- **Nothing is overwritten.** Each character you make is a brand-new figure with its own tile in the character grid.
  Luke, Thor or Elsa stay exactly as they were, and you can install as many creations as you like side by side.
- **Automatic rigging.** Creator finds the shoulders, elbows, wrists, neck, hips, knees and ankles of your model.
  You can fine-tune each joint with a slider.
- **High-quality skin weights** through Blender, when it is installed. Without Blender, Creator falls back to a
  simpler built-in method.
- **Live preview** of the result in the in-game pose, arms raised and walking, before anything is written.
- **Self-contained.** The base figures ship with Creator: browsing, previewing and rigging never read your game
  files. The game folder is only used when you install.
- **Checked output.** Every install is verified (buffers, skin weights, file links) and any previous version of
  the mod is backed up first.

## Requirements

| What                                  | Notes                                                                                                                                       |
| :------------------------------------ | :------------------------------------------------------------------------------------------------------------------------------------------ |
| Windows 10 or 11                      |                                                                                                                                             |
| Disney Infinity 3.0 Gold Edition (PC) | Your own installed copy                                                                                                                     |
| [CrabeLoader](https://github.com/LucasLhomme/CrabeLoader) & [CrabeMenu](https://github.com/LucasLhomme/CrabeMenu) | The mod loader that loads your character into the game. **CrabeMenu** (in-game `F5` menu) is recommended to switch to your character |
| Python 3.12 or newer                  | Tested with Python 3.14. Tick "Add python.exe to PATH" when installing                                                                      |
| Blender 4.x *(optional, recommended)*  | Only for better skin weights: Creator runs it in the background, you never have to open it                                                  |

## Installation

1. Download or clone this repository.
2. Double-click `run.ps1`, or run it from PowerShell:

   ```powershell
   .\run.ps1
   ```

   The first launch creates a Python virtual environment (`.venv`) and installs the dependencies
   (`customtkinter`, `moderngl`, `numpy`, `Pillow`, `trimesh`, `scipy`). Later launches start right away.

> If PowerShell refuses to run the script, allow local scripts once with
> `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

## Creating a character, step by step

The left panel has four tabs; go through them in order.

### 0. Base: choose the figure to build on

Pick the figure whose skeleton, animations and moveset your character will use. Search by name or franchise; the
viewport shows the figure in 3D.

| Mark | Meaning                                                                                                                                                                              |
| :--: | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
|  ●  | Standard skeleton: every joint Creator needs is there                                                                                                                                |
|  ◐  | Adapted skeleton: a few bones stand in for missing ones (for example the ball of the foot for an ankle, an overlay bone under a dress for a thigh). Works, with small approximations |
|  ✕  | Not humanoid (Olaf, Randall…): cannot take a humanoid mesh                                                                                                                          |

**Pick a figure with a similar build.** A slim hero fits Spider-Man better than Hulk, and a long dress fits Elsa
better than Captain America. Your character moves like its base: Thor's hammer attacks, Elsa's ice powers,
Luke's lightsaber, and so on.

### 1. Model: import your 3D model

Click **Import a 3D model** and choose an `.obj`, `.glb`, `.gltf` (also `.dae`, `.ply`, `.stl`, `.off`), or a `.zip`
containing one of them with its textures.

- The model should stand in a **T-pose** (arms out to the sides); an A-pose also works.
- Creator detects the orientation. If the model faces the wrong way or lies down, use **↻ 90°**, **↻ 180°** and
  **Stand up**.
- **Model height** is preset to the base figure's size. Tick **Show … alongside** to compare them side by side.
- All the model's textures are packed into a single texture atlas.

### 2. Skeleton: check the joints

Yellow dots are joints, green lines are bones. Creator places them automatically; the text above the sliders tells
you what it **detected** and what it only **estimated** (check those first).

Use the sliders to line the joints up with your model: arm height, shoulder width, wrists, neck, head, hips, leg
spacing, knees and ankles. **Auto fit** starts over from the automatic placement.

### 3. Rig & Export: build and install

1. **Character name**: shown in the menus (for example `Mario`). It also names the mod folder.
2. **Internal actor name**: the engine's name for the new figure (for example `MAR_Mari`): 3 to 32 letters, digits
   or `_`, starting with a letter. It is filled in for you from the character name.
3. **Game folder**: your Disney Infinity 3.0 folder, for example
   `C:\Program Files (x86)\Steam\steamapps\common\Disney Infinity 3.0 Gold Edition`.
4. **Blender**: path to `blender.exe`, optional.
5. Click **1. Build the rig**, then check the **In-game pose**, **Arms up** and **Walk** previews. If something looks
   wrong (an arm bending in the middle, a foot dragging), go back to tab 2, adjust, and build again.
6. Click **2. Install into the game**. The log lists every check; all of them should read `OK`.

The mod is written to `<game>/mods/<character name>/`. Installing again under the same name replaces it and moves
the previous version to Creator's `backups/` folder.

## Playing your character

1. **Restart the game**: new characters are only picked up at startup.
2. In the game, either:
   - press **F5** (CrabeMenu), open **Heroes › ★ Modded Characters** and pick your character; or
   - open the character grid (**My collection › Characters**): your character has its own tile.

## Tips for good results

- **Polygon count:** keep the model under about 65,000 vertices (a 16-bit engine limit). If it is too detailed,
  add a *Decimate* modifier in Blender and export again.
- **One mesh, closed and clean:** loose bits (eyes, buttons, accessories) are fine, since Creator attaches them to the
  nearest part of the body, but a model split into dozens of separate pieces rigs less cleanly.
- **Real T-pose:** arms straight and horizontal, legs slightly apart, facing forward. Joints are much easier to find.
- **Install Blender** for the skin weights: bends at the shoulders, elbows and knees come out noticeably smoother.
- **Similar proportions:** limbs are stretched to match the base figure's bone lengths (within limits). A model
  with very different proportions from its base looks stretched in game, so pick a base that looks alike.

## How it works

Every playable figure of the game is an **actor**: a skeleton, a mesh skinned to it, materials and textures, plus
the animations and abilities that drive it. Creator makes a **clone actor**: a copy of the base figure whose mesh is
replaced by yours, under a new name.

1. **Skeleton fitting.** Creator measures your model with horizontal cross-sections to find the arm line, the neck,
   the crotch, the knees and the ankles, and places Creator's standard set of joints on it.
2. **Bone mapping.** Figures name their bones mostly the same way, but not always: a dress replaces the thighs, a
   boot has no ankle bone, and so on. Each of Creator's joints is mapped onto the closest bone the base actually
   has. When a joint position is missing, it is rebuilt from the proportions of a reference figure.
3. **Skinning.** Weights are computed with Blender's bone-heat method (or, without Blender, from the distance to
   each bone). The head is kept rigid so the eyes do not slide, and each loose piece below the knees follows a single
   ankle.
4. **Baking into the bind pose.** Your mesh is not rigged to a new skeleton. Each body part is rotated and stretched
   from your model's joint onto the base figure's matching joint, so the mesh fits the base's rest pose exactly. The
   base's skeleton and its bind matrices are left untouched, so **every animation of the game plays on your mesh
   unchanged**.
5. **Writing the files.** Creator reads and writes the game's formats directly: Octane scenes (`.oct`, `.bent`),
   compiled Lua (`.dnax`) and material bundles (`.mtb`). All three are handled losslessly: re-writing an untouched
   file of the game gives back the exact same bytes. Your mesh takes the place of the base's body; every other part
   of the base (eyes, capes, accessories) is emptied.

### What a character mod contains

| File                                                                   | Role                                                     |
| :--------------------------------------------------------------------- | :------------------------------------------------------- |
| `characters/<actor>/<actor>.oct`, `_0.vbuf`, `_0.ibuf`           | The mesh: vertices, skin weights, triangles, bounds      |
| `characters/<actor>/<actor>.mtb`                                     | The materials, with textures and a cache id of their own |
| `characters/<actor>/<actor>.dnax`, `.bent`, `.animtreeoverrides` | The actor definition, pointing at the new mesh           |
| `textures/<xx>.zip`                                                  | The texture archive, carrying your character's textures  |
| `skilltrees/ActorList.patch`, `skilltrees/DataMap.patch`           | Register the new actor in the game's databases           |
| `characters/<Actor>.lua`                                             | Adds the figure to the character grid                    |
| `<name>.lua`, `mod.json`                                           | CrabeLoader entry point and CrabeMenu entry              |

## Limitations

- **Moveset:** your character uses its base figure's moves, voice, abilities and skill tree; custom animations are
  not supported.
- **Normal maps:** your character gets a flat normal map, and only the base colour texture of the model is used.
- **Non-humanoid figures** (Olaf, Randall, Maleficent, Elastigirl) cannot be used as a base.
- **Adapted skeletons** (◐) rebuild a few joints approximately: feet or dress areas can deform slightly less
  accurately than on a standard skeleton.
- **Figure icon:** the character grid shows a generic icon for your character.
- **Maturity:** characters built on Luke Skywalker have been played in game; other bases use the same pipeline but
  have seen less in-game testing. Please report what you find.

## Troubleshooting

| Problem                                      | What to try                                                                                                       |
| :------------------------------------------- | :---------------------------------------------------------------------------------------------------------------- |
| The character does not appear in the game    | Restart the game. Check that CrabeLoader is installed, and look for errors in `loader.log` in the game folder    |
| "model too detailed"                         | Decimate the model under ~65,000 vertices                                                                         |
| The model is lying down or facing away       | Tab 1:**Stand up**, **↻ 90°** / **↻ 180°**                                                  |
| Elbows or knees bend in the wrong place      | Tab 2: move the matching slider, then build the rig again                                                         |
| Stiff or blocky bends                        | Set the Blender path in tab 3, then build the rig again                                                           |
| The character slides without moving its legs | The base figure's animations are missing from the game install. Reinstall, or verify the game files through Steam |
| "already a figure of the game"               | Pick another internal actor name                                                                                  |
| The textures look wrong                      | Import the model as a`.zip` with its texture files next to it, or as a `.glb` with embedded textures          |

## For developers

```
src/
  core/       pure logic, no UI
    octane_scene.py, luac.py, material_bundle.py    lossless .oct/.bent, .dnax and .mtb readers/writers
    base_character.py, base_pack.py, roster.py      base figures
    skeleton_map.py                                  Creator's joints -> each figure's bones
    model.py, skeleton.py, rig.py, rigging.py        imported model, joint fitting, skinning
    octane.py, exporter.py, mod_writer.py, textures.py   the mod output
  render/     offscreen OpenGL viewport
  ui/         customtkinter interface
  scripts/    headless Blender step (bone-heat weights)
  assets/     bases/ (the base figure pack), roster.json, shader_layouts.json, templates/
  tools/      QuickBMS and the archive re-encrypter
tools/        scripts that regenerate src/assets from a game install
```

The assets under `src/assets/` are generated once from a game install; the app itself never reads the game to
browse or rig:

| Script                                                                   | Produces                                                                                                        |
| :----------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------- |
| `tools/build_roster.py <virtualreaderpc_data.lua> <toybox_actors.lua>` | `roster.json`: every playable figure, from the decompiled character grid and Toy Box actor list               |
| `tools/build_shader_table.py <decrypted game root>`                    | `shader_layouts.json`: where each shader keeps its texture slots, learnt from the game's own material bundles |
| `tools/build_base_pack.py <game folder>`                               | `bases/`: every figure's model, `.dnax`, animation overrides and preview textures                           |

## Credits

- **QuickBMS** by Luigi Auriemma, with the Disney Infinity BMS script from the community, to read the game's
  encrypted archives.
- The Disney Infinity modding community for the archive re-encrypter and years of format research.
- [trimesh](https://trimesh.org), [ModernGL](https://github.com/moderngl/moderngl),
  [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), NumPy, SciPy, Pillow and
  [Blender](https://www.blender.org).

Disney Infinity and all related characters are trademarks of their respective owners. This project is meant for
owners of the game.

---

## The DIM2 Modding Ecosystem

Disney Infinity Creator is part of the **DIM2** open-source modding suite for Disney Infinity 3.0:

| Project | Description | Link |
| :--- | :--- | :---: |
| **CrabeLoader** | Next-generation C++23 modloader, ASI bootstrap, and low-level engine hook framework. | [GitHub](https://github.com/LucasLhomme/CrabeLoader) |
| **CrabeMenu** | Autonomous in-game mod menu (`F5`) with full gamepad and keyboard navigation. | [GitHub](https://github.com/LucasLhomme/CrabeMenu) |
| **DisneyInfinityPortal** | Physical Disney Infinity Base (Portal) support & figure progress gateway. | [GitHub](https://github.com/LucasLhomme/DisneyInfinityPortal) |

---

## Support & Sponsor

If you find Disney Infinity Creator helpful and want to support ongoing tools and reverse-engineering:

☕ **[Buy Me a Coffee](https://buymeacoffee.com/crabecrabe)** (`buymeacoffee.com/crabecrabe`)


