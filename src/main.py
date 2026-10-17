import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core import errorlog


def main():
    errorlog.install()
    from src.core import game_data
    missing = game_data.missing_shipped()
    if missing:
        print("Disney Infinity Creator cannot start: this download is incomplete.\n")
        for path in missing:
            print(f"  missing: {path}")
        print("\nDownload Creator again: https://github.com/LucasLhomme/DisneyInfinityCreator")
        sys.exit(1)
    if game_data.needs_extraction():
        from src.ui.setup_window import SetupWindow
        setup = SetupWindow()
        setup.mainloop()
        if not setup.done:
            sys.exit(0)
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
