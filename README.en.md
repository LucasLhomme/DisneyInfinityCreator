# Disney Infinity Creator

[Français](README.md) · **English**

Turn any 3D model into a **playable character** for **Disney Infinity 3.0 Gold Edition (PC)**.

You import a model (Sketchfab, The Models Resource, your own Blender work…), pick a figure of the game as its base,
and Creator fits a skeleton, computes the skinning, lets you preview the result in motion, then installs it as a mod.
The character shows up in the game as a **brand-new figure**: it uses the base figure's animations, attacks and
abilities, and no original character is replaced.

> Fan-made tool, not affiliated with Disney, Avalanche Software or any rights holder. You need your own copy of the game.

---

## Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation and launch](#installation-and-launch)
- [Creating a character](#creating-a-character)
- [Advanced settings](#advanced-settings)
- [Understanding the deformation score](#understanding-the-deformation-score)
- [Managing your characters](#managing-your-characters)
- [Playing your character](#playing-your-character)
- [Tips for a good result](#tips-for-a-good-result)
- [How it works](#how-it-works)
- [Known limitations](#known-limitations)
- [Troubleshooting](#troubleshooting)
- [Credits](#credits)

---

## Features

- **99 base figures**: every playable character of Disney Infinity 3.0 (Marvel, Star Wars, Disney, Pixar, including
  those from 1.0 and 2.0), with search and a textured 3D preview.
- **Nothing is overwritten**: each creation is a new figure with its own tile in the character grid. Luke, Thor or
  Elsa stay untouched, and you can install as many characters as you like.
- **Built-in cleanup**: Blender (in the background) merges the pieces, fixes scale and orientation, recovers lost
  textures and freezes any skeleton, without leaving files behind.
- **Automatic rigging**: shoulders, elbows, wrists, neck, hips, knees and ankles are detected, with one slider per
  joint to refine them and a 3-view layout (front, side, top).
- **Motion preview** and a **deformation score** out of 100, with over-stretched edges in red.
- **Base suggestions**: ranks the figures by how well they match your model.
- **In-game icons** and **relief** (normal map derived from the texture), like the official figures.
- **Lightweight shared mod**: textures and icons of all your characters in a single mod; `Manage_Mods.bat` lists,
  disables and cleanly deletes your characters.
- **Verified installation**: every install is checked and the previous version of the mod is backed up.

## Requirements

| What | Notes |
| :--- | :--- |
| Windows 10 or 11 | |
| Disney Infinity 3.0 Gold Edition (PC) | Your own installed copy |
| [CrabeLoader](https://github.com/LucasLhomme/CrabeLoader) and [CrabeMenu](https://github.com/LucasLhomme/CrabeMenu) | The mod loader that loads your character. CrabeMenu (`F5` menu in game) is recommended to switch to your character |
| Python 3.12 or newer | Tick "Add python.exe to PATH" during installation |
| Blender 4.x or 5.x | Recommended: model cleanup (required for `.fbx`) and better weights. Creator runs it in the background, you never have to open it |

## Installation and launch

1. Download or clone this repository.
2. Double-click **`Launch_Creator.bat`**. On first launch it installs the Python dependencies in a `.venv`
   environment (`customtkinter`, `moderngl`, `numpy`, `Pillow`, `trimesh`, `scipy`, `cryptography`), then opens
   Creator. After that, it starts right away.
3. If the app stops, the window stays open and points to `build\creator.log`. After updating Creator, `run.ps1`
(PowerShell) reinstalls the dependencies and starts the app.

## Creating a character

The left panel has five tabs; go through them in order.

### 0. Base: pick the figure

The figure whose skeleton, animations and moveset your character will use.

| Mark | Meaning |
| :---: | :--- |
| ● | Standard skeleton: every required joint exists |
| ◐ | Adapted skeleton: a few bones stand in for others (e.g. the ball of the foot for the ankle). Works, with small approximations |
| ✕ | Not humanoid (Olaf, Randall…): cannot take a humanoid mesh |

Pick a base with a similar build: a slim hero fits Spider-Man better than Hulk, a long dress fits Elsa better than
Captain America. The **"Suggest the best bases for my model"** button (Model tab) makes this choice for you (see
[Base suggestions](#base-suggestions)).

### 1. Model: import

Click **Import a 3D model** and choose an `.obj`, `.glb`, `.gltf`, `.fbx` (or `.dae`, `.ply`, `.stl`, `.off`), or a
`.zip` holding it with its textures.

- **"Clean with Blender while importing"** (ticked by default) runs the cleanup. Without Blender, `.glb`, `.obj` and
  `.zip` files are imported as they are; `.fbx` requires Blender.
- The model must be in **T-pose** (arms out); an A-pose works too.
- Creator detects the orientation. Otherwise: **↻ 90°**, **↻ 180°**, **Stand up**, **⇅ Flip**.
- **Model height** is preset to the base's size. Tick **Show … alongside** to compare side by side.
- **Position**: sliders and 1 cm buttons; **Recentre** goes back to automatic centring.
- **Pieces**: Ctrl+click a piece, **Grow** to include the small neighbouring pieces, pick the bone and **Lock**: the
  piece will follow that bone rigidly (e.g. hair strands on the head).
- **Preview the texture atlas** shows the texture the game will receive, with warnings (image too dark, missing or
  repeated texture…).

### 2. Skeleton: check the joints

Yellow dots = joints, green lines = bones. Creator places them on its own; the text above the sliders says what was
**detected** and what is only **estimated** (check those first).

- Each slider has a note (what to line the dot up with) and an **input box** for the exact value.
- The icon to the right of each dot: ✓ found on the mesh, yellow ⚠ estimated, orange ⚠ far from the base's
  proportions, ✎ set by you. Hover it to read why.
- ⚠ warnings point out proportions that differ from the base by 20 % or more.
- **Auto-Fit** starts again from the automatic placement; **"3 views"** (under the 3D view) shows front, side and top.

### 3. Abilities & Moveset

The character's abilities and moves, inherited from the base, which you can adjust.

### 4. Rig & Export: build and install

1. **Character name**: name shown in the menus (e.g. `Mario`); it also names the mod folder.
2. **Internal actor name**: the engine's internal name (e.g. `MAR_Mari`), 3 to 32 characters, letters/digits/`_`,
   starting with a letter; prefilled.
3. **Game folder** and **Blender**: remembered from one session to the next.
4. **1. Build the rig**, then check **In-game pose**, **Arms up**, **Walk** and the **deformation score**. If
   something looks wrong, go back to tab 1 or 2, adjust, rebuild.
5. **2. Install into the game**: the log lists the checks, all of them must show `OK`.

The mod is written to `<game>/mods/<character name>/`. Reinstalling under the same name replaces the mod and moves
the previous version to `backups/`. **Close the game before installing**: it keeps its archives open.

## Advanced settings

### Base suggestions

The button compares your model's silhouette with each figure's, keeps different body types, then builds the real rig
of the best ones and measures the stretch in the test poses and the deformation when going to the game pose. The whole
list stays visible: the top 12 are tested right away, **"Test the next 12 figures"** tests the next batch, and the
filter searches by name or franchise (Avengers, Star Wars…).

### Proportions and V-shape

Skeleton tab, sliders **Head** (×0.8 to ×1.5, the head grows from the jaw), **Torso**, **Arms**, **Forearms** and
**Legs** (×0.8 to ×1.8, inflated around their axis without changing length). Live preview.

- **Disney Infinity style**: moves the model towards the average proportions of the game's characters (head ≈ 21 %
  of the height, forearms thicker than upper arms…), never making it smaller.
- **Match the base**: copies the base's thickness (head untouched). **Reset** goes back to the model.
- **V-shape** (0 to 1): in the game pose the arms hang from the base's shoulders; a narrow chest then leaves a gap
  under the arms. V-shape widens the chest up to the arms, leaving the waist and neck alone.

### Game pose and shoulders

- **Preview in game pose** (Skeleton tab): the model arms down, as the game will show it, updated on every slider.
- **Shoulder roundness** (Rig & Export tab, once the rig is built): at 0 the chest/arm junction is folded in
  (jackets, wide sleeves); at 1 it keeps its volume (bare arms).
- **in T-pose** (under "Show the base figure alongside") puts the comparison figure back in T-pose.

### Accessories (cape, tail, wings, weapon)

A cape hanging behind the pelvis skews the measurements and gets torn by the legs. Model tab, "Accessories" box:
**Find** spots what sticks out behind the body (adjustable depth) and separate pieces (highlighted in magenta, or
Ctrl+click). **Ignore** keeps the part but makes it follow the torso; **Remove** takes it out; **✕** undoes.

### Textures: game look, relief, icons

- **Game look** (Model tab): softens noise and painted shadows, brightens and saturates, like the game's characters
  (0 = original texture). **Match the base figure's brightness** brings the brightness closer to the base's. Live
  preview, and this result is what gets exported.
- **Relief** (Rig & Export tab, on by default): normal map derived from the texture (seams, folds and colour edges
  slightly carved), in the game's format.
- **Character icons** (Model tab): HUD portrait and grid figure, captured from your model on install. The "Preview"
  button shows them.

### Fingers (experimental)

**Finger weights** makes the model's hand follow the base's finger bones. As long as the fingers do not line up with
the base's, the game's grips (saber, fist) crumple the hand: a rigid hand stays the default. The **Fist** pose shows
the result.

### Robust weight transfer

**Robust weight transfer** (Model tab) builds the rig twice (Blender weights, then weights copied from the base
figure) and keeps the one that deforms less. Useful for skirts, capes and long coats. Method: "Robust Skin Weights
Transfer via Weight Inpainting" (Abdrashitov, Raichstat, Monsen, Hill, SIGGRAPH Asia 2023).

### `.dae` format (COLLADA)

Creator reads it itself: geometry, UVs, textures (looked up next to the file), unit and up axis; a skinned model is
read in its rest pose. With the cleanup, it is converted to `.glb` before going through Blender.

## Understanding the deformation score

After "Build the rig", Creator measures how much the mesh stretches or squashes in six test poses (arms up, walk, arms
overhead, arms forward, elbows bent, torso twist; "Pose amount" changes the amplitude). The score (0 to 100) blends the
average edge stretch (50 %), the share of edges deformed more than 2× (30 %) and the share torn beyond 3× (20 %).

| Score | Level |
| :---: | :--- |
| 75 and above | Good |
| 50 to 74 | Acceptable |
| below 50 | Heavy deformation |

- Edges stretched more than 3× are drawn in **red**.
- "FAILED - the model is collapsed" means broken weights.
- The score measures geometry, **not appearance**: hair following the arms can still score well. Always check
  visually and lock troublesome pieces to the right bone.

## Managing your characters

The game reads textures and icons only from its own archives, which a mod has to ship whole. To avoid repeating these
archives in every character:

- each character (`mods/<name>/`) only keeps its own files;
- the **`mods/zz_creator_shared`** mod holds the archives rebuilt once for all enabled characters. Do not edit it by
  hand.

**`Manage_Mods.bat`** (game closed; its menu is in French):

| Choice | Effect |
| :--- | :--- |
| 1. Supprimer (delete) | Sends the character to the recycle bin and rebuilds the archives: nothing of it is left in the game |
| 2. Désactiver / réactiver (disable / enable) | `_` prefix on the folder (skipped by CrabeLoader), then rebuilds the archives |
| 3. Nettoyer (clean up) | Tidies characters made with an older version and offers to send the `backups/` copies to the recycle bin |
| 4. Reconstruire (rebuild) | Rebuilds the shared archives |

Run it to delete or disable a character (rather than deleting its folder), after deleting a folder by hand, or when
the install reports "shared archives NOT rebuilt" (game was open). Command line: `--list`, `--rebuild`, `--clean`.

## Playing your character

1. **Restart the game**: new characters are only loaded at startup.
2. In game, either **F5** (CrabeMenu) → **Heroes › ★ Modded Characters**, or the **My collection › Characters** grid,
   where your character has its own tile.

## Tips for a good result

- **Under about 65,000 vertices** (engine limit). The cleanup decimates if needed.
- **A clean mesh**: a model cut into dozens of pieces rigs less well.
- **A true T-pose**: straight horizontal arms, legs slightly apart, facing front.
- **Install Blender**: softer bends at shoulders, elbows and knees.
- **Proportions close to the base**: limbs are stretched to match the base's bones.
- **Textures**: import a `.zip` with the images next to the model, or a `.glb` with embedded textures.

## How it works

Each playable figure is an **actor**: a skeleton, a skinned mesh, materials and textures, and the animations and
abilities that drive it. Creator makes a **cloned actor**: a copy of the base figure whose mesh is replaced by yours,
under a new name.

1. **Skeleton fitting**: horizontal slices of the model give the arms, neck, crotch, knees and ankles; the joints are
   placed on them, then corrected by models calibrated on the game's figures.
2. **Skinning**: Blender's bone-heat weights, or else distance to the bones, then per-zone rules (rigid head, pieces
   below the knees bound to the ankles, skirts smoothed between the legs, the game's twist bones).
3. **Baking into the rest pose**: each body part is moved from your model's joint to the base's. The base's skeleton
   does not change: **every animation of the game applies as is**.
4. **Writing the files** in the game's formats (Octane scenes, compiled Lua, materials, UI bundles, encrypted
   archives), losslessly.

### Contents of a character mod

| File | Role |
| :--- | :--- |
| `characters/<actor>/<actor>.oct`, `_0.vbuf`, `_0.ibuf` | The mesh: vertices, weights, triangles |
| `characters/<actor>/<actor>.mtb` | The materials |
| `characters/<actor>/<actor>.dnax`, `.bent`, `.animtreeoverrides` | The actor definition |
| `textures/<id>.tbody` | Textures (colour and relief) |
| `ui/…`, `<actor>_icon.png` | Icons |
| `skilltrees/ActorList.patch`, `skilltrees/DataMap.patch` | Register the actor in the game |
| `characters/<Actor>.lua` | Adds the figure to the character grid |
| `<name>.lua`, `mod.json` | CrabeLoader entry point and CrabeMenu entry |

## Known limitations

- **Moveset**: the character uses its base's moves, voice and abilities; no custom animations.
- **Textures**: one texture per character (atlas, 2048 px at most); the relief is derived from the colour.
- **Non-humanoid figures** (Olaf, Randall, Maleficent, Elastigirl): unusable as a base.
- **Automatic skeleton placement**: always check the shoulders, elbows and pelvis in the Skeleton tab, it is the main
  source of error.
- **Capes, skirts, hair**: check the poses and lock pieces if needed.

## Troubleshooting

| Problem | Try |
| :--- | :--- |
| The app closes on launch | Run `Launch_Creator.bat` (the window stays open) and read `build\creator.log` |
| Black textures or "IN" icon in game | Close the game, `Manage_Mods.bat` → 4 (rebuild); the icon only exists if "Character icons" was ticked |
| The character does not show up in game | Restart the game; check CrabeLoader; read `loader.log` in the game folder |
| "model too detailed" | Reduce below ~65,000 vertices (the cleanup does it) |
| Model lying down or facing away | Tab 1: **Stand up**, **↻ 90°** / **↻ 180°**, **⇅ Flip** |
| Skeleton offset from the body | Tab 1: position sliders or **Recentre**; "3 views" to check |
| The model turns into a needle / "collapsed" | Blender's weights failed; rebuild the rig and read the log |
| Grey model on import | Texture not linked: put the images next to the model (in the same `.zip`) |
| Elbows or knees bending badly | Tab 2: move the matching slider, then rebuild |
| Hair or cape following the arms | Ctrl+click the piece, Grow, pick the bone (e.g. Head), Lock, then rebuild |
| The character slides without moving its legs | The base's animations are missing: verify the game files through Steam |
| "already a figure of the game" | Choose another internal actor name |

## Credits

- **Disney Infinity Creator**: created by **Crabe** ([LucasLhomme](https://github.com/LucasLhomme)); versions 1.x by
  **Nyzarion**, co-developed with [Claude](https://claude.ai) (Anthropic).
- Tools shipped in `src/tools`: [QuickBMS](https://aluigi.altervista.org/quickbms.htm) by Luigi Auriemma (GPL-2.0)
  with the community's Disney Infinity BMS script, and `offsetting.exe` by
  [Team Offsetting](https://github.com/offsetting/offsetting) (MIT / Apache-2.0).
- The Disney Infinity modding community (format research).
- [trimesh](https://trimesh.org), [ModernGL](https://github.com/moderngl/moderngl),
  [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter), NumPy, SciPy, Pillow,
  [cryptography](https://cryptography.io) and [Blender](https://www.blender.org).
- Robust weight transfer inspired by [Robust Weight Transfer](https://github.com/sentfromspacevr/robust-weight-transfer)
  and [RobustSkinWeightsTransferCode](https://github.com/rin-23/RobustSkinWeightsTransferCode).

Disney Infinity and all related characters are trademarks of their respective owners. This project is intended for
owners of the game.
