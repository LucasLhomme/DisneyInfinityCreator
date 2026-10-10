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
from src.core.skeleton import (
    apply_apose_to_proportions,
    apply_tpose_to_proportions,
    base_joint_points,
    base_skeleton_segments,
    build_anchors,
    joint_points,
    measure,
    skeleton_segments,
)
from src.core.blender_rig import load_rig_file, RigParsingError, UnsupportedRigError, ParsedRig
from src.core.animation_player import AnimationPlayer, AnimationClip, get_character_animation_clips

from src.core.npc_config import EntityConfig, EntityType, Faction
from src.core.abilities import (
    CharacterAbilities,
    CombatArchetype,
    ARCHETYPE_ACTOR_MAP,
    ARCHETYPE_PRESETS,
    ANIM_ACTION_SLOTS,
    CustomAnimation,
)
from src.render.gl_widget import GLRenderer
from src.ui.timeline import TimelineWidget

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
        self.animation_player = AnimationPlayer()
        self.custom_rig: ParsedRig | None = None
        self.entity_config = EntityConfig()
        self.abilities = CharacterAbilities()

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
        self._build_abilities_tab(self.tabs.add("3. Abilities & Moveset"))
        self._build_export_tab(self.tabs.add("4. Rig & Export"))

        view = ctk.CTkFrame(self, fg_color="#09090b", corner_radius=0)
        view.grid(row=0, column=1, sticky="nsew")
        view.grid_rowconfigure(0, weight=1)
        view.grid_columnconfigure(0, weight=1)
        self.view_label = ctk.CTkLabel(view, text="")
        self.view_label.grid(row=0, column=0, sticky="nsew")

        self.timeline = TimelineWidget(view, self.animation_player, self._on_anim_frame_changed)
        self.timeline.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 2))

        hint = "Left click: orbit  •  right click: pan  •  wheel: zoom  •  double click: frame"
        ctk.CTkLabel(view, text=hint, text_color=GREY, font=ctk.CTkFont(size=11)).grid(row=2, column=0, pady=(2, 4))
        view.grid_propagate(False)
        self.renderer = GLRenderer(self.view_label)
        view.bind("<Configure>", lambda e: self.renderer.resize(e.width, max(50, e.height - 75)))
        self.after(50, self._drain_events)
        self.after(100, self._start)
        self.after(200, self._anim_tick)

    def _update_anim_render(self):
        if self.rig:
            posed_verts, posed_world = self.animation_player.evaluate_pose_and_world(self.rig)
            self.renderer.update_model_vertices(posed_verts)
            if getattr(self.timeline, "sync_compare", True) and self.base and self.renderer.show_ghost:
                ghost_verts = self.base.deform_preview_parts(posed_world)
                self.renderer.update_ghost_vertices(ghost_verts)
            self.renderer.set_skeleton(None, None)
            self.renderer.set_base_skeleton(None, None)
            self.renderer.request_render()

    def _on_anim_frame_changed(self):
        self._update_anim_render()

    def _anim_tick(self):
        if self.animation_player.tick():
            self.timeline.update_playback_state()
            self._update_anim_render()
        self.after(33, self._anim_tick)


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
                      command=self.on_import).grid(row=0, column=0, sticky="ew", pady=(4, 2))
        ctk.CTkButton(tab, text="Import Blender Rig & Tracks (.glb .gltf .json)", fg_color="#27272a",
                      hover_color="#3f3f46", text_color="#e4e4e7",
                      command=self.on_import_rig).grid(row=1, column=0, sticky="ew", pady=(0, 6))
        self.model_info = ctk.CTkLabel(tab, text="No model loaded: showing the base figure.",
                                       text_color=GREY, wraplength=330, justify="left", font=ctk.CTkFont(size=11))
        self.model_info.grid(row=2, column=0, sticky="w", pady=(0, 10))

        self.base_label = ctk.CTkLabel(tab, text="Base character: —", font=ctk.CTkFont(size=12, weight="bold"))
        self.base_label.grid(row=3, column=0, sticky="w")
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
        top.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        top.grid_columnconfigure((0, 1), weight=1)
        self.skel_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(top, text="Custom Skeleton (Green)", variable=self.skel_var,
                        command=self.on_skeleton_toggle, font=ctk.CTkFont(size=11)).grid(row=0, column=0, sticky="w")
        self.base_skel_var = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(top, text="Base Skeleton (Cyan)", variable=self.base_skel_var,
                        command=self.on_base_skeleton_toggle, font=ctk.CTkFont(size=11),
                        text_color="#38bdf8").grid(row=0, column=1, sticky="w")

        presets = ctk.CTkFrame(tab, fg_color="transparent")
        presets.grid(row=1, column=0, sticky="ew", pady=(2, 4))
        presets.grid_columnconfigure((0, 1), weight=1)
        ctk.CTkButton(presets, text="Auto-Fit Skeleton", fg_color="#27272a", hover_color="#3f3f46",
                      font=ctk.CTkFont(size=11, weight="bold"), command=self.on_auto_fit).grid(row=0, column=0, padx=2, sticky="ew")
        ctk.CTkButton(presets, text="Reset to Auto-Fit", fg_color="#27272a", hover_color="#3f3f46",
                      font=ctk.CTkFont(size=11), command=self.on_reset_fit).grid(row=0, column=1, padx=2, sticky="ew")

        self.overlay_var = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(tab, text="Superimpose base skeleton over model",
                        variable=self.overlay_var, command=self.on_overlay_toggle,
                        font=ctk.CTkFont(size=11), text_color=GREY).grid(row=2, column=0, sticky="w", pady=(0, 2))

        self.fit_label = ctk.CTkLabel(tab, text="Import a model to place the skeleton.", text_color=GREY,
                                      wraplength=330, justify="left", font=ctk.CTkFont(size=11))
        self.fit_label.grid(row=3, column=0, sticky="w", pady=(2, 4))
        self.sliders = {}
        scroll = ctk.CTkScrollableFrame(tab, fg_color="transparent", height=380)
        scroll.grid(row=4, column=0, sticky="nsew")
        scroll.grid_columnconfigure(0, weight=1)
        for i, (name, text, lo, hi, rel) in enumerate(SKELETON_SLIDERS):
            label = ctk.CTkLabel(scroll, text=text, font=ctk.CTkFont(size=12))
            label.grid(row=2 * i, column=0, sticky="w")
            slider = ctk.CTkSlider(scroll, from_=lo, to=hi, command=lambda v, n=name: self.on_slider(n, v))
            slider.grid(row=2 * i + 1, column=0, sticky="ew", pady=(0, 6))
            slider.configure(state="disabled")
            self.sliders[name] = (slider, label, text, rel)
        legend = ("• Green skeleton: Fitted to your 3D model (arms, legs, head).\n"
                  "• Cyan skeleton: Base character reference (on the ghost figure).\n"
                  "• Note: The builder automatically retargets your model to the game's bind pose.")
        ctk.CTkLabel(tab, text=legend, text_color=GREY, wraplength=330, justify="left", font=ctk.CTkFont(size=10)).grid(
            row=5, column=0, sticky="w", pady=4)

    # -------------------------------------------------------- abilities & moveset
    def _build_abilities_tab(self, tab):
        tab.grid_columnconfigure(0, weight=1)
        tab.grid_rowconfigure(0, weight=1)

        scroll = ctk.CTkScrollableFrame(tab, fg_color="#0c0c0e", corner_radius=6)
        scroll.grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
        scroll.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(scroll, text="Gameplay & Moveset Customization", font=ctk.CTkFont(size=14, weight="bold"),
                     text_color="#e4e4e7").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ctk.CTkLabel(scroll, text="Give your character unique attack movesets from other figures, "
                                  "flight, super powers, and custom imported animations.",
                     text_color=GREY, wraplength=330, justify="left", font=ctk.CTkFont(size=11)).grid(
            row=1, column=0, sticky="w", padx=8, pady=(0, 10))

        ctk.CTkLabel(scroll, text="Combat Archetype & Moveset:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#e4e4e7").grid(row=2, column=0, sticky="w", padx=8, pady=(4, 2))

        archetypes = [a.value for a in CombatArchetype]
        self.archetype_menu = ctk.CTkOptionMenu(
            scroll, values=archetypes, command=self._on_archetype_selected,
            height=28, fg_color="#27272a", button_color="#3f3f46", text_color="#e4e4e7"
        )
        self.archetype_menu.set(CombatArchetype.INHERIT_BASE.value)
        self.archetype_menu.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 6))

        self.borrow_frame = ctk.CTkFrame(scroll, fg_color="#18181b", corner_radius=6)
        self.borrow_frame.grid(row=4, column=0, sticky="ew", padx=8, pady=(0, 10))
        self.borrow_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.borrow_frame, text="Borrow attacks from:", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, padx=8, pady=6, sticky="w")
        roster_names = [f"{e.display_name} ({e.actor})" for e in sorted(load_roster(), key=lambda x: x.display_name.lower())]
        self.combat_source_menu = ctk.CTkOptionMenu(
            self.borrow_frame, values=["Inherit Base Figure"] + roster_names,
            command=self._on_combat_source_selected,
            height=26, fg_color="#27272a", button_color="#3f3f46"
        )
        self.combat_source_menu.set("Inherit Base Figure")
        self.combat_source_menu.grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        c_stats = ctk.CTkFrame(scroll, fg_color="transparent")
        c_stats.grid(row=5, column=0, sticky="ew", padx=8, pady=(0, 10))
        c_stats.grid_columnconfigure((0, 1), weight=1)

        self.dmg_label = ctk.CTkLabel(c_stats, text="Damage: 1.0x", font=ctk.CTkFont(size=11))
        self.dmg_label.grid(row=0, column=0, sticky="w")
        self.dmg_slider = ctk.CTkSlider(c_stats, from_=0.5, to=3.0, number_of_steps=25, command=self._on_dmg_slider)
        self.dmg_slider.set(1.0)
        self.dmg_slider.grid(row=1, column=0, sticky="ew", padx=(0, 4), pady=(2, 0))

        self.atk_spd_label = ctk.CTkLabel(c_stats, text="Atk Speed: 1.0x", font=ctk.CTkFont(size=11))
        self.atk_spd_label.grid(row=0, column=1, sticky="w")
        self.atk_spd_slider = ctk.CTkSlider(c_stats, from_=0.5, to=2.0, number_of_steps=15, command=self._on_atk_spd_slider)
        self.atk_spd_slider.set(1.0)
        self.atk_spd_slider.grid(row=1, column=1, padx=(4, 0), sticky="ew", pady=(2, 0))

        ctk.CTkLabel(scroll, text="Special Powers & Locomotion:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#e4e4e7").grid(row=6, column=0, sticky="w", padx=8, pady=(6, 2))

        powers_frame = ctk.CTkFrame(scroll, fg_color="#18181b", corner_radius=6)
        powers_frame.grid(row=7, column=0, sticky="ew", padx=8, pady=(0, 10))
        powers_frame.grid_columnconfigure(0, weight=1)

        self.fly_var = ctk.BooleanVar(value=False)
        self.fly_check = ctk.CTkCheckBox(powers_frame, text="Flight / Hover (Iron Man / Thor / Falcon)",
                                         variable=self.fly_var, command=self._on_power_toggled, font=ctk.CTkFont(size=11))
        self.fly_check.grid(row=0, column=0, sticky="w", padx=8, pady=(6, 4))

        self.super_jump_var = ctk.BooleanVar(value=False)
        self.super_jump_check = ctk.CTkCheckBox(powers_frame, text="Super Jump (Hulk / Heavy Leap)",
                                                variable=self.super_jump_var, command=self._on_power_toggled, font=ctk.CTkFont(size=11))
        self.super_jump_check.grid(row=1, column=0, sticky="w", padx=8, pady=4)

        self.double_jump_var = ctk.BooleanVar(value=True)
        self.double_jump_check = ctk.CTkCheckBox(powers_frame, text="Double Jump (Air Hop)",
                                                 variable=self.double_jump_var, command=self._on_power_toggled, font=ctk.CTkFont(size=11))
        self.double_jump_check.grid(row=2, column=0, sticky="w", padx=8, pady=4)

        self.wall_crawl_var = ctk.BooleanVar(value=False)
        self.wall_crawl_check = ctk.CTkCheckBox(powers_frame, text="Wall Crawling (Spider-Man / Venom)",
                                                variable=self.wall_crawl_var, command=self._on_power_toggled, font=ctk.CTkFont(size=11))
        self.wall_crawl_check.grid(row=3, column=0, sticky="w", padx=8, pady=4)

        self.glide_var = ctk.BooleanVar(value=False)
        self.glide_check = ctk.CTkCheckBox(powers_frame, text="Gliding (Descend smoothly)",
                                           variable=self.glide_var, command=self._on_power_toggled, font=ctk.CTkFont(size=11))
        self.glide_check.grid(row=4, column=0, sticky="w", padx=8, pady=(4, 6))

        self.speed_label = ctk.CTkLabel(scroll, text="Movement Speed: 1.0x", font=ctk.CTkFont(size=11))
        self.speed_label.grid(row=8, column=0, sticky="w", padx=8)
        self.speed_slider = ctk.CTkSlider(scroll, from_=0.5, to=2.5, number_of_steps=20, command=self._on_speed_slider)
        self.speed_slider.set(1.0)
        self.speed_slider.grid(row=9, column=0, sticky="ew", padx=8, pady=(2, 12))

        ctk.CTkLabel(scroll, text="Custom Animation Importer:", font=ctk.CTkFont(size=12, weight="bold"),
                     text_color="#e4e4e7").grid(row=10, column=0, sticky="w", padx=8, pady=(4, 2))
        ctk.CTkLabel(scroll, text="Import .glb, .gltf, .fbx, or .json animations and map them to actions.",
                     text_color=GREY, font=ctk.CTkFont(size=11)).grid(row=11, column=0, sticky="w", padx=8, pady=(0, 6))

        anim_box = ctk.CTkFrame(scroll, fg_color="#18181b", corner_radius=6)
        anim_box.grid(row=12, column=0, sticky="ew", padx=8, pady=(0, 10))
        anim_box.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(anim_box, text="Action Slot:", font=ctk.CTkFont(size=11)).grid(
            row=0, column=0, padx=8, pady=6, sticky="w")
        slot_names = [label for _, label in ANIM_ACTION_SLOTS]
        self.anim_slot_menu = ctk.CTkOptionMenu(
            anim_box, values=slot_names, height=26, fg_color="#27272a", button_color="#3f3f46",
            command=self._on_anim_slot_changed
        )
        self.anim_slot_menu.set(slot_names[0])
        self.anim_slot_menu.grid(row=0, column=1, padx=8, pady=6, sticky="ew")

        self.anim_status_label = ctk.CTkLabel(anim_box, text="No custom animation mapped for this slot.",
                                              text_color=GREY, font=ctk.CTkFont(size=11), wraplength=310, justify="left")
        self.anim_status_label.grid(row=1, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="w")

        btn_row = ctk.CTkFrame(anim_box, fg_color="transparent")
        btn_row.grid(row=2, column=0, columnspan=2, padx=8, pady=(0, 8), sticky="ew")
        btn_row.grid_columnconfigure((0, 1), weight=1)

        self.import_anim_btn = ctk.CTkButton(
            btn_row, text="Import File...", fg_color="#ffffff", text_color="#09090b",
            hover_color="#e4e4e7", font=ctk.CTkFont(size=11, weight="bold"),
            command=self.on_import_custom_animation
        )
        self.import_anim_btn.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        self.preview_anim_btn = ctk.CTkButton(
            btn_row, text="Preview Track", fg_color="#27272a", text_color="#e4e4e7",
            hover_color="#3f3f46", font=ctk.CTkFont(size=11),
            command=self.on_preview_custom_animation
        )
        self.preview_anim_btn.grid(row=0, column=1, padx=(4, 0), sticky="ew")

        self.clear_anim_btn = ctk.CTkButton(
            anim_box, text="Clear Slot", fg_color="transparent", text_color="#f87171",
            hover_color="#27272a", font=ctk.CTkFont(size=11),
            command=self.on_clear_custom_animation
        )
        self.clear_anim_btn.grid(row=3, column=0, columnspan=2, padx=8, pady=(0, 6), sticky="e")

        self.abilities_summary_label = ctk.CTkLabel(scroll, text="", text_color=GREEN,
                                                    wraplength=330, justify="left", font=ctk.CTkFont(size=11))
        self.abilities_summary_label.grid(row=13, column=0, sticky="w", padx=8, pady=(4, 10))
        self._update_abilities_summary()

    def _current_action_slot_key(self) -> str:
        current_label = self.anim_slot_menu.get()
        for key, label in ANIM_ACTION_SLOTS:
            if label == current_label:
                return key
        return "attack_1"

    def _sync_abilities_from_ui(self):
        self.abilities.can_fly = self.fly_var.get()
        self.abilities.super_jump = self.super_jump_var.get()
        self.abilities.double_jump = self.double_jump_var.get()
        self.abilities.wall_crawl = self.wall_crawl_var.get()
        self.abilities.glide = self.glide_var.get()
        self.abilities.speed_multiplier = float(self.speed_slider.get())
        self.abilities.damage_multiplier = float(self.dmg_slider.get())
        self.abilities.attack_speed_multiplier = float(self.atk_spd_slider.get())
        self._update_abilities_summary()

    def _update_abilities_summary(self):
        if hasattr(self, "abilities_summary_label"):
            summary_txt = self.abilities.summary(self.base)
            self.abilities_summary_label.configure(text=f"Summary: {summary_txt}")

    def _on_archetype_selected(self, choice: str):
        try:
            arch = CombatArchetype(choice)
        except ValueError:
            arch = CombatArchetype.INHERIT_BASE
        self.abilities.combat_archetype = arch

        if arch == CombatArchetype.INHERIT_BASE:
            self.abilities.combat_source_actor = None
            self.combat_source_menu.set("Inherit Base Figure")
        elif arch != CombatArchetype.CUSTOM_ROSTER:
            preset = ARCHETYPE_PRESETS.get(arch, {})
            self.fly_var.set(preset.get("can_fly", False))
            self.super_jump_var.set(preset.get("super_jump", False))
            self.wall_crawl_var.set(preset.get("wall_crawl", False))
            self.glide_var.set(preset.get("glide", False))
            dmg = preset.get("damage_multiplier", 1.0)
            spd = preset.get("speed_multiplier", 1.0)
            self.dmg_slider.set(dmg)
            self.dmg_label.configure(text=f"Damage: {dmg:.1f}x")
            self.speed_slider.set(spd)
            self.speed_label.configure(text=f"Movement Speed: {spd:.1f}x")

            actor = ARCHETYPE_ACTOR_MAP.get(arch)
            self.abilities.combat_source_actor = actor
            if actor:
                try:
                    entry = find_entry(actor)
                    self.combat_source_menu.set(f"{entry.display_name} ({entry.actor})")
                except KeyError:
                    pass

        self._sync_abilities_from_ui()
        self._refresh_moveset_clips()

    def _on_combat_source_selected(self, choice: str):
        if choice == "Inherit Base Figure":
            self.abilities.combat_source_actor = None
        else:
            import re
            m = re.search(r"\(([^)]+)\)", choice)
            if m:
                self.abilities.combat_source_actor = m.group(1).strip()
                self.archetype_menu.set(CombatArchetype.CUSTOM_ROSTER.value)
                self.abilities.combat_archetype = CombatArchetype.CUSTOM_ROSTER
        self._sync_abilities_from_ui()
        self._refresh_moveset_clips()

    def _on_dmg_slider(self, val):
        self.abilities.damage_multiplier = float(val)
        self.dmg_label.configure(text=f"Damage: {float(val):.1f}x")
        self._update_abilities_summary()

    def _on_atk_spd_slider(self, val):
        self.abilities.attack_speed_multiplier = float(val)
        self.atk_spd_label.configure(text=f"Atk Speed: {float(val):.1f}x")
        self._update_abilities_summary()

    def _on_power_toggled(self):
        self._sync_abilities_from_ui()

    def _on_speed_slider(self, val):
        self.abilities.speed_multiplier = float(val)
        self.speed_label.configure(text=f"Movement Speed: {float(val):.1f}x")
        self._update_abilities_summary()

    def _on_anim_slot_changed(self, choice: str):
        slot = self._current_action_slot_key()
        if slot in self.abilities.custom_animations:
            ca = self.abilities.custom_animations[slot]
            self.anim_status_label.configure(
                text=f"✓ Mapped: {ca.name} ({ca.duration:.2f}s, {int(round(ca.duration*ca.fps))} frames)",
                text_color=GREEN
            )
        else:
            self.anim_status_label.configure(
                text="No custom animation mapped for this slot.",
                text_color=GREY
            )

    def on_import_custom_animation(self):
        path = filedialog.askopenfilename(
            title="Import Animation Track",
            filetypes=[("Animation Files", "*.glb *.gltf *.fbx *.bvh *.json"), ("All Files", "*.*")]
        )
        if not path:
            return
        slot = self._current_action_slot_key()
        slot_label = self.anim_slot_menu.get()
        try:
            parsed = load_rig_file(path)
            if not parsed.animations:
                self.anim_status_label.configure(
                    text=f"⚠️ {Path(path).name} parsed, but contains 0 animation tracks.",
                    text_color=YELLOW
                )
                return
            anim = parsed.animations[0]
            ca = CustomAnimation(
                slot=slot,
                name=f"{Path(path).stem} ({anim.name})",
                source_path=path,
                duration=anim.duration,
                fps=anim.fps,
                track=anim,
            )
            self.abilities.custom_animations[slot] = ca

            clip = AnimationClip(
                name=f"[Custom] {slot_label.split('(')[0].strip()}: {anim.name}",
                duration=anim.duration,
                fps=anim.fps,
                custom_track=anim,
            )
            self.timeline.add_custom_clip(clip)
            self.anim_status_label.configure(
                text=f"✓ Loaded {ca.name} ({ca.duration:.2f}s, {int(round(ca.duration*ca.fps))} frames)",
                text_color=GREEN
            )
            self.log(f"Custom animation track imported for {slot}: {anim.name} ({anim.duration:.2f}s)")
            self._update_abilities_summary()
        except Exception as exc:
            self.anim_status_label.configure(
                text=f"Import failed: {exc}",
                text_color=RED
            )
            self.log(f"Custom animation import error: {exc}")

    def on_preview_custom_animation(self):
        slot = self._current_action_slot_key()
        if slot not in self.abilities.custom_animations:
            self.anim_status_label.configure(text="Please import an animation file first.", text_color=YELLOW)
            return
        ca = self.abilities.custom_animations[slot]
        slot_label = self.anim_slot_menu.get()
        target_clip = None
        for name in self.timeline.clips:
            if slot in name.lower() or ca.name in name or (ca.track and ca.track.name in name):
                target_clip = name
                break
        if target_clip:
            self.timeline._on_clip_selected(target_clip)

    def on_clear_custom_animation(self):
        slot = self._current_action_slot_key()
        if slot in self.abilities.custom_animations:
            del self.abilities.custom_animations[slot]
            self.anim_status_label.configure(text="Slot cleared.", text_color=GREY)
            self._update_abilities_summary()
            self._refresh_moveset_clips()

    def _refresh_moveset_clips(self):
        if not hasattr(self, "timeline") or not self.timeline:
            return
        game_dir = Path(self.game_entry.get().strip()) if hasattr(self, "game_entry") and self.game_entry.get() else None
        eff_actor = self.abilities.effective_combat_actor(self.base) if self.base else None

        target_base = self.base
        if eff_actor and self.base and eff_actor != self.base.actor:
            try:
                entry = find_entry(eff_actor)
                target_base = BaseCharacter.from_pack(entry)
            except Exception:
                target_base = self.base

        if target_base:
            clips = get_character_animation_clips(target_base, game_dir)
            # Re-add custom animations
            for slot, ca in self.abilities.custom_animations.items():
                if ca.track:
                    c_name = f"[Custom] {slot.upper()}: {ca.name}"
                    clips[c_name] = AnimationClip(name=c_name, duration=ca.duration, fps=ca.fps, custom_track=ca.track)
            self.timeline.set_clips(clips)

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
        self.pose_buttons.grid(row=10, column=0, sticky="ew", pady=(0, 6))
        self.pose_buttons.configure(state="disabled")

        ctk.CTkLabel(tab, text="Entity Type (Character, Enemy, Ally/NPC):", font=ctk.CTkFont(size=12)).grid(
            row=11, column=0, sticky="w")
        self.entity_type_btn = ctk.CTkSegmentedButton(tab, values=["Avatar", "Enemy", "Ally / NPC"],
                                                      command=self._on_entity_type_changed)
        self.entity_type_btn.set("Avatar")
        self.entity_type_btn.grid(row=12, column=0, sticky="ew", pady=(0, 6))

        # Enemy / NPC parameters frame
        self.npc_frame = ctk.CTkFrame(tab, fg_color="#18181b", corner_radius=6)
        self.npc_frame.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self.npc_frame, text="Faction:", font=ctk.CTkFont(size=11)).grid(row=0, column=0, padx=6, pady=4, sticky="w")
        self.faction_menu = ctk.CTkOptionMenu(self.npc_frame, values=["Enemies", "Villains", "Townsperson", "Neutral"],
                                              height=24, fg_color="#27272a", button_color="#3f3f46")
        self.faction_menu.set("Enemies")
        self.faction_menu.grid(row=0, column=1, padx=6, pady=4, sticky="ew")

        ctk.CTkLabel(self.npc_frame, text="HP / Damage:", font=ctk.CTkFont(size=11)).grid(row=1, column=0, padx=6, pady=4, sticky="w")
        hd_row = ctk.CTkFrame(self.npc_frame, fg_color="transparent")
        hd_row.grid(row=1, column=1, padx=6, pady=4, sticky="ew")
        hd_row.grid_columnconfigure((0, 1), weight=1)
        self.health_entry = ctk.CTkEntry(hd_row, height=24, placeholder_text="HP", fg_color="#27272a", border_width=0)
        self.health_entry.insert(0, "250")
        self.health_entry.grid(row=0, column=0, padx=(0, 2), sticky="ew")
        self.damage_entry = ctk.CTkEntry(hd_row, height=24, placeholder_text="DMG", fg_color="#27272a", border_width=0)
        self.damage_entry.insert(0, "35")
        self.damage_entry.grid(row=0, column=1, padx=(2, 0), sticky="ew")

        ctk.CTkLabel(self.npc_frame, text="Animations:", font=ctk.CTkFont(size=11)).grid(row=2, column=0, padx=6, pady=4, sticky="w")
        anim_row = ctk.CTkFrame(self.npc_frame, fg_color="transparent")
        anim_row.grid(row=2, column=1, padx=6, pady=4, sticky="ew")
        anim_row.grid_columnconfigure((0, 1), weight=1)
        self.anim_walk_menu = ctk.CTkOptionMenu(anim_row, values=["Walk", "Run", "Patrol"], height=24,
                                                fg_color="#27272a", button_color="#3f3f46")
        self.anim_walk_menu.set("Walk")
        self.anim_walk_menu.grid(row=0, column=0, padx=(0, 2), sticky="ew")
        self.anim_attack_menu = ctk.CTkOptionMenu(anim_row, values=["Attack", "Slash", "Shoot"], height=24,
                                                  fg_color="#27272a", button_color="#3f3f46")
        self.anim_attack_menu.set("Attack")
        self.anim_attack_menu.grid(row=0, column=1, padx=(2, 0), sticky="ew")

        self.install_button = ctk.CTkButton(tab, text="2. Install into the game", fg_color="#fbbf24",
                                            text_color="#09090b", hover_color="#f59e0b",
                                            font=ctk.CTkFont(weight="bold"), command=self.on_install)
        self.install_button.grid(row=14, column=0, sticky="ew", pady=(4, 8))
        self.log_box = ctk.CTkTextbox(tab, height=240, fg_color="#0c0c0e", font=ctk.CTkFont(family="Consolas", size=11),
                                      wrap="word")
        self.log_box.grid(row=15, column=0, sticky="nsew")
        tab.grid_rowconfigure(15, weight=1)

    def _on_entity_type_changed(self, choice: str):
        if choice == "Avatar":
            self.npc_frame.grid_remove()
            self.install_button.configure(text="2. Install into the game")
        else:
            self.npc_frame.grid(row=13, column=0, sticky="ew", pady=(0, 6))
            if choice == "Enemy":
                self.faction_menu.set("Enemies")
                self.health_entry.delete(0, "end")
                self.health_entry.insert(0, "250")
                self.damage_entry.delete(0, "end")
                self.damage_entry.insert(0, "40")
                self.install_button.configure(text="2. Install Enemy into game")
            else:
                self.faction_menu.set("Townsperson")
                self.health_entry.delete(0, "end")
                self.health_entry.insert(0, "150")
                self.damage_entry.delete(0, "end")
                self.damage_entry.insert(0, "20")
                self.install_button.configure(text="2. Install Ally/NPC into game")

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
            self.base_parts = parts
            self.timeline.set_rig_ready(self.rig is not None)
            self._save_settings()
            self._highlight_base()
            self.renderer.set_ghost(parts)
            self.renderer.show_ghost = self.ghost_var.get()
            self.renderer.set_base_skeleton(base_skeleton_segments(base.joints), base_joint_points(base.joints))
            game_dir = Path(self.game_entry.get().strip()) if hasattr(self, "game_entry") and self.game_entry.get() else None
            self._refresh_moveset_clips()
            self._update_abilities_summary()
            skeleton = base.skeleton

            colour = GREEN if not skeleton.fallbacks else YELLOW
            if not base.supported:
                colour = RED
            mismatch = ""
            if self.model and self.props:
                m_leg = self.props.crotch_y / max(self.props.height, 0.1)
                b_leg = base.joints["Hips"][1] / max(base.height, 0.1)
                if abs(m_leg - b_leg) > 0.20:
                    colour = YELLOW
                    mismatch = (f"\n⚠️ Mismatch: {base.display_name} has {int(b_leg*100)}% legs vs {int(m_leg*100)}% on model. "
                                f"Prefer Donald Duck, Stitch, or Syndrome.")
            self.base_info.configure(
                text=f"{base.display_name}  ({base.actor})\n"
                     f"model {base.model}, {len(base.meshes)} mesh(es), {len(base.bone_names)} skinned bones, "
                     f"height {base.height:.2f}\n{skeleton.summary()}"
                     + mismatch
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

    def on_import_rig(self):
        path = filedialog.askopenfilename(
            title="Import Blender Rig or Animation Tracks",
            filetypes=[("Blender Rig & Animations", "*.glb *.gltf *.json"), ("All Files", "*.*")])
        if not path:
            return
        try:
            rig = load_rig_file(path)
            self.custom_rig = rig
            self.log(f"Blender Rig imported: {rig.summary()}")
            for anim in rig.animations:
                clip = AnimationClip(name=anim.name, duration=anim.duration, fps=anim.fps, custom_track=anim)
                self.timeline.add_custom_clip(clip)
            self.model_info.configure(
                text=f"{self.model_info.cget('text')}\n✓ Rig: {rig.summary()}",
                text_color=GREEN)
        except (RigParsingError, UnsupportedRigError, Exception) as exc:
            self.model_info.configure(text=f"Rig Import Error: {exc}", text_color=RED)
            self.log(f"Rig import failed: {exc}")

    def _refit(self):
        self.auto_props, self.fit_report = measure(self.model.vertices(), self.model.faces, self.base)
        self.props = self.auto_props
        summary = self.fit_report.summary()
        if self.base:
            m_leg = self.props.crotch_y / max(self.props.height, 0.1)
            b_leg = self.base.joints["Hips"][1] / max(self.base.height, 0.1)
            if abs(m_leg - b_leg) > 0.20:
                summary += f"\n⚠️ Morphological Mismatch: {self.base.display_name} has {int(b_leg*100)}% legs vs {int(m_leg*100)}% for your model. For a cartoon character, prefer Donald Duck, Stitch, or Syndrome."
        self.fit_label.configure(text=summary,
                                 text_color=YELLOW if (self.fit_report.estimated or "⚠️" in summary) else GREEN)
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
        if hasattr(self, "timeline"):
            self.timeline.set_rig_ready(False)
        if hasattr(self, "base_parts") and self.base_parts:
            self.renderer.reset_ghost_vertices(self.base_parts)
        self.pose = "tpose"
        self.pose_buttons.set("T-pose")
        self.pose_buttons.configure(state="disabled")
        self.anchors = build_anchors(self.props, self.base)
        if showing_rig:
            self.renderer.set_model(self.model.vertices(), self.model.faces, self.model.uvs, self.model.texture)
        else:
            self.renderer.update_model_vertices(self.model.vertices())
        self.renderer.set_skeleton(skeleton_segments(self.anchors), joint_points(self.anchors))
        if self.base:
            self.renderer.set_base_skeleton(base_skeleton_segments(self.base.joints), base_joint_points(self.base.joints))
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

    def on_base_skeleton_toggle(self):
        self.renderer.show_base_skeleton = self.base_skel_var.get()
        self.renderer.request_render()

    def on_overlay_toggle(self):
        self.renderer.overlay_base_skeleton = self.overlay_var.get()
        self.renderer.request_render()

    def on_apply_apose(self):
        if self.model and self.props and self.base:
            self.props = apply_apose_to_proportions(self.props, self.base)
            self._sync_sliders()
            self._geometry_changed()

    def on_apply_tpose(self):
        if self.model and self.props:
            self.props = apply_tpose_to_proportions(self.props)
            self._sync_sliders()
            self._geometry_changed()

    def on_auto_fit(self):
        if self.model:
            self._refit()

    def on_reset_fit(self):
        if self.auto_props:
            self.props = self.auto_props
            self._sync_sliders()
            self._geometry_changed()

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
        if hasattr(self, "base_parts") and self.base_parts:
            self.renderer.reset_ghost_vertices(self.base_parts)
        if self.pose == "tpose":
            self.renderer.set_skeleton(skeleton_segments(self.anchors), joint_points(self.anchors))
            if self.base:
                self.renderer.set_base_skeleton(base_skeleton_segments(self.base.joints), base_joint_points(self.base.joints))
        else:
            self.renderer.set_skeleton(None, None)
            self.renderer.set_base_skeleton(None, None)
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
            self.timeline.set_rig_ready(True)
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
        ent_choice = self.entity_type_btn.get()
        if ent_choice == "Enemy":
            ent_type = EntityType.ENEMY
            faction = Faction.ENEMIES
        elif ent_choice == "Ally / NPC":
            ent_type = EntityType.ALLY
            try:
                faction = Faction(self.faction_menu.get())
            except (ValueError, AttributeError):
                faction = Faction.TOWNSPERSON
        else:
            ent_type = EntityType.AVATAR
            faction = Faction.HEROES

        try:
            hp = int(self.health_entry.get().strip())
        except (ValueError, AttributeError):
            hp = 100
        try:
            dmg = int(self.damage_entry.get().strip())
        except (ValueError, AttributeError):
            dmg = 25

        entity_cfg = EntityConfig(
            entity_type=ent_type,
            faction=faction,
            max_health=hp,
            base_damage=dmg,
            animations={
                "idle": "Idle",
                "walk": self.anim_walk_menu.get() if hasattr(self, "anim_walk_menu") else "Walk",
                "attack": self.anim_attack_menu.get() if hasattr(self, "anim_attack_menu") else "Attack",
            }
        )

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
                if entity_cfg.is_enemy:
                    self.log(f"Restart the game, then F5 > Spawners > Enemies > {ident.display_name} (or Modded Characters).")
                elif entity_cfg.is_npc_or_ally:
                    self.log(f"Restart the game, then F5 > Spawners > NPCs > {ident.display_name} (or Modded Characters).")
                else:
                    self.log(f"Restart the game, then F5 > Heroes > ★ Modded Characters > {ident.display_name} (or pick it in the Virtual Reader).")
            else:
                self.log("Some checks failed: the entity may not show up in game.")
        rig = self.rig
        texture = self.model.texture
        abilities = self.abilities
        self._run(lambda: install(rig, texture, ident, game_dir, self.log, entity_cfg, abilities=abilities), done)

