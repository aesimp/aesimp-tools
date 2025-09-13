import sys
from pathlib import Path
from os import getenv
from winshell import shortcut
from importlib import import_module

from questionary import Style, checkbox # for multiple choice

SEND_TO_DIR = Path(getenv("APPDATA")) / "Microsoft" / "Windows" / "SendTo"
INSTALL_DIR = Path(getenv("LocalAppData")) / "aesimp-tools"
IS_EXE = getattr(sys, 'frozen', False)

TARGET_EXE = INSTALL_DIR / Path(sys.executable).name

PLUGIN_LIST = {"converter", "upscale", "interpolate"}

# create a new list that contains PLUGIN_LIST
# all tools that can have a shortcut in SendTo
SHORTCUT_LIST = PLUGIN_LIST.copy()
SHORTCUT_LIST.add("remux")
SHORTCUT_LIST.add("decompose")
SHORTCUT_LIST.add("ripAudio")
SHORTCUT_LIST.add("downscale")


def create_lnk(mode_name: str):
    lnk_file = SEND_TO_DIR / f"aesimp {mode_name}.lnk"

    # Shortcut mit Icon aus der eigenen Exe
    with shortcut(str(lnk_file)) as link:
        exefile_name = Path(sys.executable).name
        link.path = str(INSTALL_DIR / exefile_name)
        link.arguments = mode_name
        link.working_directory = str(INSTALL_DIR)
        link.icon_location = (str(INSTALL_DIR / exefile_name), 0)  # Icon aus der eigenen Exe

def create_lnks():
    # delete old lnk
    for lnk in SEND_TO_DIR.rglob("aesimp*.lnk"): # delete all lnk
        lnk.unlink()

    custom_style = Style([
        ('checkbox', 'fg:cyan bold'),       # die Checkbox
        ('selected', 'fg:yellow'),           # ausgewählt
        ('pointer', 'fg:red bold')          # Pfeil
    ])

    custom_list = SHORTCUT_LIST.copy()
    custom_list.add("all of them")
    custom_list = sorted(custom_list)

    selected = checkbox(
        "Which tools will you use?",
        choices=custom_list,
        style=custom_style
    ).ask()

    if selected[0] == "all of them":
        selected = SHORTCUT_LIST.copy()

    for plugin in selected:
        create_lnk(plugin)
        print(" "*4, f"Created shortcut for <{plugin}>")


# ------------------------------------------------------------------
#
# Token verification
# tools to verify token
#
# ------------------------------------------------------------------


def main(args):
    executable = args[0] if len(args) > 0 else None        # "exe name"
    mode = args[1] if len(args) > 1 else "install"        # "plugin_name" if nothing selected, then "install"
    params = args[2:] if len(args) > 2 else []      # alle vom Explorer übergebenen Dateien

    # check if exe is installed
    # if IS_EXE:
    if mode == "install": # not in local app folder
        if not INSTALL_DIR.exists():
            INSTALL_DIR.mkdir(parents=True, exist_ok=True)

        if IS_EXE: # wenn es eine exe ist, kopiere die exe
            print("Copy exe to target Folder...")
            from shutil import copy2
            copy2(sys.executable, TARGET_EXE)

            print("Installed to", INSTALL_DIR)

        print("Create SendTo links...")
        create_lnks()
        print("Successfully created")

        print()
        print("You can now right-click on files in Explorer, select 'Send to' and then choose the desired tool.")

        # installation done
        return

    try:
        # only import when exists
        if mode not in SHORTCUT_LIST:
            print(f"No Module <{mode}> found")
            input("Press Enter to continue: ")
            return

        # greater tools have own files
        # small tools are in shortcut.py
        im_module = mode if mode in PLUGIN_LIST else "shortcut"
        m = import_module(f"plugins.{im_module}")
        if m is None:
            raise Exception(f"Module <{im_module}> not found")
        m.start(mode, params)
    except Exception as e:
        print("An error occurred!")
        print(e)
        input("\nPress Enter to continue: ")
        return


if __name__ == "__main__":
    main(sys.argv) # getting all args from SendTo
