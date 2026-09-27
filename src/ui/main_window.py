import queue
import threading
import traceback
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from src.core.base_character import BaseCharacter
from src.core.base_pack import has_pack, preview_texture, status
from src.core.config import load_settings, save_settings
from src.core.exporter import install
from src.core.mod_writer import default_actor, make_identity
from src.core.model import CharacterModel, auto_placement, load_source
from src.core.paths import WORK_DIR
from src.core.rig import build_rig
from src.core.roster import find_entry, load_roster
from src.core.skeleton import build_anchors, joint_points, measure, skeleton_segments
from src.render.gl_widget import GLRenderer

GREEN, RED, YELLOW, GREY = "#4ade80", "#f87171", "#fbbf24", "#a1a1aa"
POSES = {"T-pose": "tpose", "In-game pose": "bind", "Arms up": "arms", "Walk": "walk"}
DEFAULT_BASE = "EMP_Luke"

# (field, label, low, high, relative) — relative bounds are multiples of the model height, others are 0..1 fractions.
SKELETON_SLIDERS = (
    ("arm_y", "Arm height", 0.3, 0.95, True),
    ("shoulder_x", "Shoulder width", 0.02, 0.45, True),
    ("wrist", "Wrist position", 0.3, 0.9, False),
    ("neck_y", "Neck", 0.35, 0.98, True),
    ("head_y", "Head pivot", 0.4, 0.99, True),
    ("crotch_y", "Hips (crotch)", 0.12, 0.8, True),
    ("leg_x", "Leg spacing", 0.0, 0.3, True),
    ("knee", "Knees", 0.2, 0.8, False),
    ("ankle_y", "Ankles", 0.01, 0.25, True),
)


class MainWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.settings = load_settings()
        self.base: BaseCharacter | None = None
        self.model: CharacterModel | None = None
        self.props = None
        self.auto_props = None
        self.fit_report = None
        self.anchors = None
        self.rig = None
        self.pose = "tpose"
        self.busy = False
        self._actor_edited = False
        self._events: queue.Queue = queue.Queue()
        self._generation = 0
        self.base_buttons = {}

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title("Disney Infinity Creator")
        self.geometry("1440x900")
        self.configure(fg_color="#09090b")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        side = ctk.CTkFrame(self, width=380, corner_radius=0, fg_color="#121316")
        side.grid(row=0, column=0, sticky="nsew")
        side.grid_propagate(False)
        side.grid_rowconfigure(1, weight=1)
        side.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(side, text="Disney Infinity Creator", font=ctk.CTkFont(size=20, weight="bold")).grid(
            row=0, column=0, padx=16, pady=(16, 4), sticky="w")
        self.tabs = ctk.CTkTabview(side, fg_color="#121316")
        self.tabs.grid(row=1, column=0, padx=8, pady=0, sticky="nsew")
        self._build_base_tab(self.tabs.add("0. Base"))
        self._build_model_tab(self.tabs.add("1. Model"))
        self._build_skeleton_tab(self.tabs.add("2. Skeleton"))
        self._build_export_tab(self.tabs.add("3. Rig & Export"))

        view = ctk.CTkFrame(self, fg_color="#09090b", corner_radius=0)
        view.grid(row=0, column=1, sticky="nsew")
        view.grid_rowconfigure(0, weight=1)
        view.grid_columnconfigure(0, weight=1)
        self.view_label = ctk.CTkLabel(view, text="")
        self.view_label.grid(row=0, column=0, sticky="nsew")
        hint = "Left click: orbit  •  right click: pan  •  wheel: zoom  •  double click: frame"
        ctk.CTkLabel(view, text=hint, text_color=GREY, font=ctk.CTkFont(size=11)).grid(row=1, column=0, pady=4)
        view.grid_propagate(False)
        self.renderer = GLRenderer(self.view_label)
        view.bind("<Configure>", lambda e: self.renderer.resize(e.width, e.height - 30))
        self.after(50, self._drain_events)
        self.after(100, self._start)

    def _start(self):
        if not has_pack():
            self.base_info.configure(text="Creator's base pack is missing (src/assets/bases): "
                                          "run tools/build_base_pack.py.", text_color=RED)
            return
        self.on_pick_base(self.settings.get("base_actor", DEFAULT_BASE))

    # ------------------------------------------------------------------ tabs
    def _build_base_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(2, weight=1)
        ctk.CTkLabel(tab, text="Pick the figure your character is built on: it keeps its skeleton, animations "
                               "and moveset, only the mesh changes.",
                     text_color=GREY, wraplength=330, justify="left", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, sticky="w", pady=(0, 6))
        # No textvariable: CTkEntry hides its placeholder when one is bound.
        self.search_entry = ctk.CTkEntry(tab, placeholder_text="Search a figure (name, franchise)…",
                                         fg_color="#27272a", border_width=0)
        self.search_entry.grid(row=1, column=0, sticky="new", pady=(0, 4))
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_bases())
        self.base_list = ctk.CTkScrollableFrame(tab, fg_color="#0c0c0e", height=400)
        self.base_list.grid(row=2, column=0, sticky="nsew")
        self.base_list.grid_columnconfigure(0, weight=1)
        for entry in sorted(load_roster(), key=lambda e: e.display_name.lower()):
            button = ctk.CTkButton(self.base_list, text=self._base_label(entry), anchor="w", height=26,
                                   fg_color="transparent", hover_color="#27272a", text_color="#e4e4e7",
                                   command=lambda a=entry.actor: self.on_pick_base(a))
            self.base_buttons[entry.actor] = (entry, button)
        self._filter_bases()
        ctk.CTkLabel(tab, text="● standard skeleton   ◐ adapted (some bones stand in for others)   ✕ not humanoid",
                     text_color=GREY, wraplength=330, justify="left", font=ctk.CTkFont(size=10)).grid(
            row=3, column=0, sticky="w", pady=(4, 2))
        self.base_info = ctk.CTkLabel(tab, text="Loading…", wraplength=330, justify="left",
                                      font=ctk.CTkFont(size=11))
        self.base_info.grid(row=4, column=0, sticky="w", pady=(2, 4))

    def _build_model_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        ctk.CTkButton(tab, text="Import a 3D model (.zip .obj .glb .gltf ...)", fg_color="#ffffff",
                      text_color="#09090b", hover_color="#e4e4e7", font=ctk.CTkFont(weight="bold"),
                      command=self.on_import).grid(row=0, column=0, sticky="ew", pady=(4, 6))
        self.model_info = ctk.CTkLabel(tab, text="No model loaded: showing the base figure.",
                                       text_color=GREY, wraplength=330, justify="left", font=ctk.CTkFont(size=11))
        self.model_info.grid(row=1, column=0, sticky="w", pady=(0, 10))

        self.base_label = ctk.CTkLabel(tab, text="Base character: —", font=ctk.CTkFont(size=12, weight="bold"))
        self.base_label.grid(row=2, column=0, sticky="w")
        ctk.CTkLabel(tab, text="Your character reuses its skeleton, animations and moveset (tab 0 to change it).",
                     text_color=GREY, font=ctk.CTkFont(size=11), wraplength=330, justify="left").grid(
            row=3, column=0, sticky="w", pady=(0, 10))

        ctk.CTkLabel(tab, text="Orientation (T-pose, facing you):").grid(row=4, column=0, sticky="w")
        row = ctk.CTkFrame(tab, fg_color="transparent")
        row.grid(row=5, column=0, sticky="ew", pady=(2, 10))
        for i, (text, cmd) in enumerate((("↻ 90°", lambda: self.on_turn(1)), ("↻ 180°", lambda: self.on_turn(2)),
                                         ("Stand up", self.on_upright))):
            row.grid_columnconfigure(i, weight=1)
            ctk.CTkButton(row, text=text, width=90, fg_color="#27272a", hover_color="#3f3f46", command=cmd).grid(
                row=0, column=i, padx=2, sticky="ew")

        self.height_label = ctk.CTkLabel(tab, text="Model height")
        self.height_label.grid(row=6, column=0, sticky="w")
        self.height_slider = ctk.CTkSlider(tab, from_=0.5, to=3.5, command=self.on_height)
        self.height_slider.set(2.0)
        self.height_slider.grid(row=7, column=0, sticky="ew", pady=(0, 10))
        self._update_height_label()

        self.ghost_var = ctk.BooleanVar(value=True)
        self.ghost_box = ctk.CTkCheckBox(tab, text="Show the base figure alongside (comparison)",
                                         variable=self.ghost_var, command=self.on_ghost)
        self.ghost_box.grid(row=8, column=0, sticky="w", pady=4)

    def _build_skeleton_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        top = ctk.CTkFrame(tab, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)
        self.skel_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(top, text="Show skeleton", variable=self.skel_var,
                        command=self.on_skeleton_toggle).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(top, text="Auto fit", width=120, fg_color="#27272a", hover_color="#3f3f46",
                      command=self.on_auto_fit).grid(row=0, column=1)
        self.fit_label = ctk.CTkLabel(tab, text="Import a model to place the skeleton.", text_color=GREY,
                                      wraplength=330, justify="left", font=ctk.CTkFont(size=11))
        self.fit_label.grid(row=1, column=0, sticky="w", pady=(4, 6))
        self.sliders = {}
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent", height=460)
        scroll.grid(row=2, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        for i, (name, text, lo, hi, rel) in enumerate(SKELETON_SLIDERS):
            label = ctk.CTkLabel(scroll, text=text, font=ctk.CTkFont(size=12))
            label.grid(row=2 * i, column=0, sticky="w")
            slider = ctk.CTkSlider(scroll, from_=lo, to=hi, command=lambda v, n=name: self.on_slider(n, v))
            slider.grid(row=2 * i + 1, column=0, sticky="ew", pady=(0, 6))
            slider.configure(state="disabled")
            self.sliders[name] = (slider, label, text, rel)
        ctk.CTkLabel(tab, text="Yellow dots = joints, green lines = bones. Line them up with the model: "
                               "shoulders, elbows, wrists, hips, knees, ankles.",
                     text_color=GREY, wraplength=330, justify="left", font=ctk.CTkFont(size=11)).grid(
            row=3, column=0, sticky="w", pady=6)

    def _build_export_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)

        def entry(row, label, value, browse=None):
            ctk.CTkLabel(tab, text=label, font=ctk.CTkFont(size=12)).grid(row=row, column=0, sticky="w")
            frame = ctk.CTkFrame(tab, fg_color="transparent")
            frame.grid(row=row + 1, column=0, sticky="ew", pady=(0, 6))
            frame.grid_columnconfigure(0, weight=1)
            e = ctk.CTkEntry(frame, fg_color="#27272a", border_width=0)
            e.insert(0, value)
            e.grid(row=0, column=0, sticky="ew")
            if browse:
                ctk.CTkButton(frame, text="…", width=32, fg_color="#27272a", hover_color="#3f3f46",
                              command=lambda: browse(e)).grid(row=0, column=1, padx=(4, 0))
            return e

        self.name_entry = entry(0, "Character name", self.settings.get("mod_name", "mario"))
        self.actor_entry = entry(2, "Internal actor name (3 to 32 characters, e.g. MAR_Mari)",
                                 default_actor(self.name_entry.get()))
        self.name_entry.bind("<KeyRelease>", self._sync_actor)
        self.actor_entry.bind("<KeyRelease>", lambda e: setattr(self, "_actor_edited", True))
        self.game_entry = entry(4, "Game folder", self.settings.get("game_path", ""), self._browse_dir)
        self.blender_entry = entry(6, "Blender (for high-quality skinning weights)",
                                   self.settings.get("blender_path", ""), self._browse_exe)

        self.rig_button = ctk.CTkButton(tab, text="1. Build the rig", fg_color="#3b82f6", hover_color="#2563eb",
                                        font=ctk.CTkFont(weight="bold"), command=self.on_rig)
        self.rig_button.grid(row=8, column=0, sticky="ew", pady=(8, 4))
        ctk.CTkLabel(tab, text="Rig preview:", font=ctk.CTkFont(size=12)).grid(row=9, column=0, sticky="w")
        self.pose_buttons = ctk.CTkSegmentedButton(tab, values=list(POSES), command=self.on_pose)
        self.pose_buttons.set("T-pose")
        self.pose_buttons.grid(row=10, column=0, sticky="ew", pady=(0, 8))
        self.pose_buttons.configure(state="disabled")
        self.install_button = ctk.CTkButton(tab, text="2. Install into the game", fg_color="#fbbf24",
                                            text_color="#09090b", hover_color="#f59e0b",
                                            font=ctk.CTkFont(weight="bold"), command=self.on_install)
        self.install_button.grid(row=11, column=0, sticky="ew", pady=(0, 8))
        self.log_box = ctk.CTkTextbox(tab, height=260, fg_color="#0c0c0e", font=ctk.CTkFont(family="Consolas", size=11),
                                      wrap="word")
        self.log_box.grid(row=12, column=0, sticky="nsew")
        tab.grid_rowconfigure(12, weight=1)

    # ------------------------------------------------------------- helpers
    def _browse_dir(self, e):
        path = filedialog.askdirectory(title="Disney Infinity 3.0 folder", initialdir=e.get() or None)
        if path:
            e.delete(0, "end")
            e.insert(0, path)
            self._save_settings()

    def _browse_exe(self, e):
        path = filedialog.askopenfilename(title="blender.exe", filetypes=[("blender.exe", "blender.exe"), ("*", "*.*")])
        if path:
            e.delete(0, "end")
            e.insert(0, path)

    def _sync_actor(self, _=None):
        if not self._actor_edited:
            self.actor_entry.delete(0, "end")
            self.actor_entry.insert(0, default_actor(self.name_entry.get()))

    def _save_settings(self):
        self.settings.update(game_path=self.game_entry.get().strip(), blender_path=self.blender_entry.get().strip(),
                             mod_name=self.name_entry.get().strip())
        if self.base:
            self.settings["base_actor"] = self.base.actor
        save_settings(self.settings)

    def _drain_events(self):
        """Worker threads never touch Tk: they queue callables that run here, on the UI thread."""
        while True:
            try:
                self._events.get_nowait()()
            except queue.Empty:
                break
        self.after(50, self._drain_events)

    def log(self, text):
        def write():
            self.log_box.insert("end", text + "\n")
            self.log_box.see("end")
        self._events.put(write)

    def _set_busy(self, busy):
        self.busy = busy
        state = "disabled" if busy else "normal"
        self.rig_button.configure(state=state)
        self.install_button.configure(state=state)

    def _update_height_label(self):
        ref = f" ({self.base.display_name} = {self.base.fit_height:.2f})" if self.base else ""
        self.height_label.configure(text=f"Model height: {self.height_slider.get():.2f}{ref}")

    # ---------------------------------------------------------------- bases
    def _base_label(self, entry) -> str:
        mark = status(entry.actor).mark
        franchise = f"   ·  {entry.franchise}" if entry.franchise else ""
        return f"{mark}  {entry.display_name}{franchise}"

    def _filter_bases(self):
        needle = self.search_entry.get().strip().lower()
        row = 0
        for actor, (entry, button) in self.base_buttons.items():
            hay = f"{entry.display_name} {entry.actor} {entry.franchise}".lower()
            if needle in hay:
                button.grid(row=row, column=0, sticky="ew")
                row += 1
            else:
                button.grid_remove()

    def _highlight_base(self):
        for actor, (_, button) in self.base_buttons.items():
            selected = self.base is not None and actor == self.base.actor
            button.configure(fg_color="#1e3a8a" if selected else "transparent")

    def on_pick_base(self, actor: str):
        if self.busy:
            return
        try:
            entry = find_entry(actor)
        except KeyError:
            entry = find_entry(DEFAULT_BASE)
        self.base_info.configure(text=f"Loading {entry.display_name}…", text_color=GREY)

        def job():
            base = BaseCharacter.from_pack(entry)
            parts = base.preview_parts(preview_texture)
            _ = base.skeleton, base.body_mesh, base.winding_sign
            return base, parts

        def done(result, error):
            self._set_busy(False)
            if error:
                self.base_info.configure(text=f"Could not load {entry.display_name}: {error[0]}", text_color=RED)
                print(error[1])
                return
            base, parts = result
            self.base = base
            self._save_settings()
            self._highlight_base()
            self.renderer.set_ghost(parts)
            self.renderer.show_ghost = self.ghost_var.get()
            skeleton = base.skeleton
            colour = GREEN if not skeleton.fallbacks else YELLOW
            if not base.supported:
                colour = RED
            self.base_info.configure(
                text=f"{base.display_name}  ({base.actor})\n"
                     f"model {base.model}, {len(base.meshes)} mesh(es), {len(base.bone_names)} skinned bones, "
                     f"height {base.height:.2f}\n{skeleton.summary()}"
                     + ("" if base.supported else "\nThis figure cannot take a humanoid mesh: pick another one."),
                text_color=colour)
            self.base_label.configure(text=f"Base character: {base.display_name} ({base.actor})")
            self.ghost_box.configure(text=f"Show {base.display_name} alongside (comparison)")
            if self.model:
                self.height_slider.set(base.fit_height)
                self.on_height(base.fit_height)
            else:
                self.height_slider.set(base.fit_height)
                self._update_height_label()
            self.renderer.frame_all()
        self._run(job, done)

    # -------------------------------------------------------------- model
    def on_import(self):
        if self.base is None:
            self.model_info.configure(text="Pick a base figure first (tab 0).", text_color=RED)
            return
        path = filedialog.askopenfilename(
            title="Import a 3D model or a ZIP archive",
            filetypes=[("3D models and ZIP", "*.zip *.obj *.glb *.gltf *.dae *.ply *.stl *.off"), ("All", "*.*")])
        if not path:
            return
        try:
            source = load_source(path)
        except Exception as exc:
            self.model_info.configure(text=f"Error: {exc}", text_color=RED)
            return
        placement = auto_placement(source, self.height_slider.get())
        self.model = CharacterModel(source, placement)
        self.model_info.configure(
            text=f"{Path(path).name}\n{len(source.vertices)} vertices, {len(source.faces)} triangles, "
                 f"texture {source.texture.width}×{source.texture.height}\n"
                 f"Auto orientation: {placement.quarter_turns % 4 * 90}°"
                 f"{', stood up (Z-up file)' if placement.upright_fix else ''}",
            text_color=GREEN)
        self.renderer.set_model(self.model.vertices(), self.model.faces, self.model.uvs, self.model.texture)
        self._refit()
        self.renderer.frame_all()

    def _refit(self):
        self.auto_props, self.fit_report = measure(self.model.vertices(), self.model.faces, self.base)
        self.props = self.auto_props
        self.fit_label.configure(text=self.fit_report.summary(),
                                 text_color=YELLOW if self.fit_report.estimated else GREEN)
        self._sync_sliders()
        self._geometry_changed()

    def _sync_sliders(self):
        h = self.props.height
        for name, (slider, label, text, rel) in self.sliders.items():
            lo, hi = next((s[2], s[3]) for s in SKELETON_SLIDERS if s[0] == name)
            if rel:
                slider.configure(from_=lo * h, to=hi * h, state="normal")
            else:
                slider.configure(from_=lo, to=hi, state="normal")
            value = getattr(self.props, name)
            slider.set(value)
            label.configure(text=f"{text}: {value:.2f}")

    def _geometry_changed(self):
        """Placement, joints or base changed: the rig is stale, redraw the T-pose model and its skeleton."""
        showing_rig = self.rig is not None
        self._generation += 1
        self.rig = None
        self.pose = "tpose"
        self.pose_buttons.set("T-pose")
        self.pose_buttons.configure(state="disabled")
        self.anchors = build_anchors(self.props, self.base)
        if showing_rig:
            self.renderer.set_model(self.model.vertices(), self.model.faces, self.model.uvs, self.model.texture)
        else:
            self.renderer.update_model_vertices(self.model.vertices())
        self.renderer.set_skeleton(skeleton_segments(self.anchors), joint_points(self.anchors))
        self.renderer.request_render()

    def on_turn(self, quarters):
        if self.model:
            self.model.placement.quarter_turns += quarters
            self._refit()

    def on_upright(self):
        if self.model:
            self.model.placement.upright_fix = not self.model.placement.upright_fix
            self._refit()
            self.renderer.frame_all()

    def on_height(self, value):
        self._update_height_label()
        if not self.model:
            return
        ratio = value / self.model.placement.height
        self.model.placement.height = value

        def scale(props):
            return props.adjusted(**{k: (v if k in ("wrist", "knee") else v * ratio) for k, v in vars(props).items()})
        self.props, self.auto_props = scale(self.props), scale(self.auto_props)
        self._sync_sliders()
        self._geometry_changed()

    def on_ghost(self):
        self.renderer.show_ghost = self.ghost_var.get()
        self.renderer.request_render()

    # ------------------------------------------------------------ skeleton
    def on_skeleton_toggle(self):
        self.renderer.show_skeleton = self.skel_var.get()
        self.renderer.request_render()

    def on_auto_fit(self):
        if self.model:
            self._refit()

    def on_slider(self, name, value):
        if not self.props:
            return
        changes = {name: float(value)}
        if name == "arm_y":
            changes["tip_y"] = self.props.tip_y + (value - self.props.arm_y)
        self.props = self.props.adjusted(**changes)
        slider, label, text, _ = self.sliders[name]
        label.configure(text=f"{text}: {value:.2f}")
        self._geometry_changed()

    # --------------------------------------------------------- rig & export
    def on_pose(self, choice):
        if not self.rig:
            return
        self.pose = POSES[choice]
        self.renderer.update_model_vertices(self.rig.posed(self.pose))
        if self.pose == "tpose":
            self.renderer.set_skeleton(skeleton_segments(self.anchors), joint_points(self.anchors))
        else:
            self.renderer.set_skeleton(None, None)
        self.renderer.request_render()

    def _run(self, job, done):
        def worker():
            try:
                result = job()
                self._events.put(lambda: done(result, None))
            except Exception as exc:
                detail = traceback.format_exc()
                self._events.put(lambda: done(None, (exc, detail)))
        self._set_busy(True)
        threading.Thread(target=worker, daemon=True).start()

    def _failed(self, error):
        self.log(f"FAILED: {error[0]}")
        print(error[1])

    def _ready_to_rig(self) -> bool:
        if not self.model:
            self.log("Import a model first (tab 1).")
            return False
        if self.base is None or not self.base.supported:
            self.log("Pick a base figure with a humanoid skeleton first (tab 0).")
            return False
        return True

    def on_rig(self, then=None):
        if not self._ready_to_rig():
            return
        self._save_settings()
        self.log(f"— Building the rig on {self.base.display_name} —")
        generation = self._generation

        def done(rig, error):
            self._set_busy(False)
            if error:
                self._failed(error)
                return
            if generation != self._generation:
                self.log("The model, skeleton or base changed while the rig was building: build it again.")
                return
            self.rig = rig
            # The rig has its own vertex set (seams welded, UV splits rebuilt): show that mesh from now on.
            self.renderer.set_model(rig.tpose, rig.faces, rig.uvs, self.model.texture)
            self.log(f"Rig ready ({rig.method} weights). Try the “In-game pose”, “Arms up” and “Walk” previews.")
            self.pose_buttons.configure(state="normal")
            self.pose_buttons.set("In-game pose")
            self.on_pose("In-game pose")
            if then:
                then()
        blender = self.blender_entry.get().strip()
        model, anchors, base = self.model, self.anchors, self.base
        self._run(lambda: build_rig(model, anchors, base, Path(blender) if blender else None,
                                    WORK_DIR / "rig", self.log), done)

    def on_install(self):
        if not self._ready_to_rig():
            return
        if self.rig is None:
            self.on_rig(then=self.on_install)
            return
        self._save_settings()
        game_dir = Path(self.game_entry.get().strip())
        try:
            ident = make_identity(self.name_entry.get(), self.actor_entry.get().strip(), self.base, game_dir)
        except ValueError as exc:
            self.log(f"FAILED: {exc}")
            return
        self.log(f"— Installing “{ident.display_name}” (actor {ident.actor}, based on {self.base.display_name}) —")
        rig, texture = self.rig, self.model.texture

        def done(report, error):
            self._set_busy(False)
            if error:
                self._failed(error)
                return
            self.log("Checks:")
            for passed, msg in report.checks:
                self.log(f"  {'OK    ' if passed else 'FAILED'}  {msg}")
            if report.ok:
                self.log(f"Installed in {report.mod_dir}")
                self.log("Restart the game, then F5 > Heroes > ★ Modded Characters > "
                         f"{ident.display_name} (or pick it in the Virtual Reader).")
            else:
                self.log("Some checks failed: the character may not show up in game.")
        self._run(lambda: install(rig, texture, ident, game_dir, self.log), done)
