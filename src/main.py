import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import errorlog


def missing_game_data() -> list[str]:
    """Files extracted from the game that Creator cannot start without."""
    from src.core.paths import ASSETS_DIR, TOOLS_DIR
    needed = [ASSETS_DIR / "roster.json", ASSETS_DIR / "bases", ASSETS_DIR / "templates", TOOLS_DIR / "offsetting.exe"]
    return [str(p.relative_to(ASSETS_DIR.parent.parent)) for p in needed if not p.exists()]


def main():
    errorlog.install()
    missing = missing_game_data()
    if missing:
        print("Disney Infinity Creator cannot start: the game data is missing.\n")
        for path in missing:
            print(f"  missing: {path}")
        print("\nThis download only contains the source code. Get the full package (with src/assets and src/tools):\n"
              "  https://github.com/LucasLhomme/DisneyInfinityCreator")
        sys.exit(1)
    try:
        from src.ui.main_window import MainWindow
        app = MainWindow()
        # Errors inside Tk callbacks (button clicks, timers) are caught by Tk, not by sys.excepthook.
        app.report_callback_exception = lambda kind, value, tb: errorlog.report(kind, value, tb)
        app.mainloop()
    except Exception:
        errorlog.report(*sys.exc_info())
        sys.exit(1)


if __name__ == "__main__":
    main()
