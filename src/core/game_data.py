"""Game data Creator needs, extracted from the player's own Disney Infinity 3.0 install on first launch.

The base figures (models, actor scripts, animation trees, preview textures: src/assets/bases/) and the material
template (src/assets/templates/skinned_body.mtb) are the game's own files: they are never shipped with Creator, each
player builds them from their copy of the game. What ships is only metadata Creator worked out (roster.json: names
and ids of the playable figures; shader_layouts.json: record sizes and texture slots per shader).
"""
import time
from pathlib import Path
from typing import Callable

from src.core import base_pack
from src.core.material_bundle import TEMPLATE_PATH, MaterialBundle, _shader_layouts
from src.core.paths import ASSETS_DIR, TOOLS_DIR

TEMPLATE_SOURCE = "emp_luke"
"""The material template is the body material of Luke Skywalker (standard skinned shader, diffuse + normal map)."""
SHIPPED = (ASSETS_DIR / "roster.json", ASSETS_DIR / "shader_layouts.json", TOOLS_DIR / "quickbms.exe",
           TOOLS_DIR / "disney_infinity_new.bms")
DEFAULT_GAME_DIRS = [
    r"C:\Program Files (x86)\Steam\steamapps\common\Disney Infinity 3.0 Gold Edition",
    r"C:\Program Files\Steam\steamapps\common\Disney Infinity 3.0 Gold Edition",
] + [rf"{d}:\SteamLibrary\steamapps\common\Disney Infinity 3.0 Gold Edition" for d in "CDEFGHIJKLM"]
Log = Callable[[str], None]
Progress = Callable[[int, int, str], None]


def missing_shipped() -> list[Path]:
    """Files that come with Creator itself: without them the download is incomplete."""
    return [p for p in SHIPPED if not p.exists()]


def needs_extraction() -> bool:
    return not base_pack.INDEX_PATH.is_file() or not TEMPLATE_PATH.is_file()


def is_game_dir(path: str | Path) -> bool:
    return bool(path) and (Path(path) / "assets" / "characters").is_dir()


def find_game_dir(hint: str = "") -> str:
    for candidate in [hint, *DEFAULT_GAME_DIRS]:
        if candidate and is_game_dir(candidate):
            return str(Path(candidate))
    return ""


class _Textures:
    """Textures read straight from the game's encrypted archives, one archive kept open at a time."""

    def __init__(self, game_dir: Path):
        self.textures = Path(game_dir) / "assets" / "textures"
        self.prefix, self.entries = None, {}

    def __call__(self, texture_id: str):
        import io

        from PIL import Image

        from src.core import octane_zip
        texture_id = texture_id.lower()
        prefix = texture_id[:2]
        if prefix != self.prefix:
            archive = self.textures / f"{prefix}.zip"
            self.prefix = prefix
            try:
                self.entries = ({Path(e.name).stem.lower(): e for e in octane_zip.read(archive)}
                                if archive.is_file() else {})
            except (OSError, ValueError):
                self.entries = {}
        entry = self.entries.get(texture_id)
        loose = self.textures / f"{texture_id}.tbody"
        try:
            if entry is not None:
                data = entry.data()
            elif loose.is_file():
                data = loose.read_bytes()
            else:
                return None
            img = Image.open(io.BytesIO(data))
            img.load()
            return img
        except (OSError, ValueError):
            return None


def _packed_install(game_dir: Path):
    """GameInstall that also finds the actor scripts (.dnax) packed in assets/characters/characters.zip, as in the
    Steam release (the loose layout of an unpacked game works as before)."""
    from src.core import octane_zip
    from src.core.game_files import CACHE_DIR, GameFileError, GameInstall

    class PackedInstall(GameInstall):
        _packed = None

        def dnax(self, rel_path: str) -> Path:
            try:
                return super().dnax(rel_path)
            except GameFileError:
                pass
            name = Path(rel_path).name.lower()
            if PackedInstall._packed is None:
                archive = self.assets / "characters" / "characters.zip"
                PackedInstall._packed = ({Path(e.name).name.lower(): e for e in octane_zip.read(archive)}
                                         if archive.is_file() else {})
            entry = PackedInstall._packed.get(name)
            if entry is None:
                raise GameFileError(f"{rel_path} not found in {self.assets} nor in characters/characters.zip")
            out = CACHE_DIR / "dnax" / name
            if not out.is_file():
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(entry.data())
            return out
    return PackedInstall(game_dir)


def _status(base):
    skeleton = base.skeleton
    if not base.supported:
        state = "unsupported"
    elif skeleton.fallbacks:
        state = "adapted"
    else:
        state = "standard"
    return base_pack.BaseStatus(state, skeleton.summary(), len(base.meshes), round(base.fit_height, 3))


def write_template() -> None:
    """skinned_body.mtb = the first material of Luke's bundle (its two textures, its shader, its data record)."""
    source = next((base_pack.PACK_DIR / TEMPLATE_SOURCE).glob("*.mtb"), None)
    if source is None:
        raise FileNotFoundError(f"{TEMPLATE_SOURCE} is missing from the base pack: the material template needs it")
    luke = MaterialBundle.from_bytes(source.read_bytes())
    size = _shader_layouts()[luke.shaders[0]]["record_size"]
    template = MaterialBundle(textures=luke.textures[:2], shaders=luke.shaders[:1], uuids=luke.uuids[:1],
                              shader_ids=[0], hashes=luke.hashes[:1], data=luke.data[:size])
    TEMPLATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    TEMPLATE_PATH.write_bytes(template.to_bytes())


def extract(game_dir: str | Path, log: Log = print, progress: Progress | None = None) -> int:
    """Build src/assets/bases and the material template from the game install. Returns the number of figures."""
    from PIL import Image  # noqa: F401  (imported here so a missing Pillow fails before anything is written)

    from src.core.base_character import BaseCharacter, looks_like_normal_map
    from src.core.roster import load_roster
    game = _packed_install(Path(game_dir))
    game.check()
    textures = _Textures(Path(game_dir))
    entries = sorted(load_roster(), key=lambda e: e.actor.lower())
    rows, total, t0 = {}, 0, time.time()
    for i, entry in enumerate(entries):
        if progress:
            progress(i, len(entries), entry.display_name)
        try:
            base = BaseCharacter.from_game(entry, game)
            status = _status(base)
            total += base_pack.add_to_pack(base, status, textures, looks_like_normal_map)
            rows[entry.actor] = base_pack.index_row(base, status)
        except Exception as exc:  # noqa: BLE001 - one broken figure must not stop the others
            log(f"  {entry.display_name}: skipped ({exc})")
    if not rows:
        raise RuntimeError("no figure could be read from this game folder")
    write_template()
    base_pack.write_index(rows)  # last: its presence marks a complete extraction
    base_pack._index.cache_clear()
    if progress:
        progress(len(entries), len(entries), "")
    log(f"{len(rows)} figures extracted ({total / 1e6:.0f} MB) in {time.time() - t0:.0f} s")
    return len(rows)
