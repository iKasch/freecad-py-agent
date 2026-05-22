#!/usr/bin/env python3
"""Install the folder-watch macro into FreeCAD's user macro folder as a symlink."""

from pathlib import Path


ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / "freecad_folder_watch_agent.FCMacro"
TARGET_DIR = Path.home() / "Library" / "Application Support" / "FreeCAD" / "Macro"
TARGET = TARGET_DIR / SOURCE.name


def main():
    if not SOURCE.exists():
        raise SystemExit("Source macro not found: {}".format(SOURCE))

    TARGET_DIR.mkdir(parents=True, exist_ok=True)

    if TARGET.exists() or TARGET.is_symlink():
        if TARGET.is_symlink() and TARGET.resolve() == SOURCE:
            print("already installed: {}".format(TARGET))
            return
        raise SystemExit(
            "Refusing to overwrite existing macro: {}\n"
            "Remove or rename it first if you want to replace it.".format(TARGET)
        )

    TARGET.symlink_to(SOURCE)
    print("installed symlink:")
    print("{} -> {}".format(TARGET, SOURCE))


if __name__ == "__main__":
    main()
