from os.path import join
from os import makedirs, getenv
import json
import io, zipfile
from pathlib import Path
import mimetypes
from re import search, compile
import subprocess


# ------------------------------------------------------------------
# GLOBAL VARIABLES
# ------------------------------------------------------------------
SERVER_URL = "https://aesimp.com" # my website, my server, https encryption
INSTALL_DIR = Path(getenv("LocalAppData")) / "aesimp-tools"
DEPENDENCIES_DIR = INSTALL_DIR / "dependencies" # for external apps like ffmpeg, Real-CUGAN, rife-ncnn-vulkan, etc.
CACHE_DIR = INSTALL_DIR / "cache" # can be deleted anytime
makedirs(CACHE_DIR, exist_ok=True)


# ------------------------------------------------------------------
# Cache
# ------------------------------------------------------------------

def write_cache(cache_name: str, value: str = None, suffix: str = "cache"):
    if not value:
        return
    cache_file = CACHE_DIR / f"{cache_name}.{suffix}"
    try:
        with cache_file.open("w", encoding="utf-8") as f:
            f.write(value.strip())
    except:
        pass

def get_cache(cache_name: str, suffix: str = "cache") -> str | None:
    cache_file = CACHE_DIR / f"{cache_name}.{suffix}"
    if cache_file.is_file():
        with cache_file.open("r", encoding="utf-8") as f:
            data = f.read().strip()
        return data or None
    return None

def delete_cache(cache_name: str, suffix: str = "cache"):
    cache_file = CACHE_DIR / f"{cache_name}.{suffix}"
    if cache_file.is_file():
        cache_file.unlink()


# ------------------------------------------------------------------
# General Functions
# ------------------------------------------------------------------

# extract last number from string or filenames
def extract_num(f: str | Path):
    search_str = f.stem if isinstance(f, Path) else f
    match = search(r"(\d+)(?!.*\d)", search_str)  # last number in string
    return int(match.group(1)) if match else -1

# input number with min, max and default value
def intput(min=0, max=100, default=0, info: str = None):
    while True:
        try:
            if info:
                print(info)
            value = input(f"Please enter a number between {min} - {max} (Default: {default}): ")
            if value == "":
                return default
            num = int(value)
            if min <= num <= max:
                return num
            else:
                print(f"Number must be between {min} and {max}.")
        except ValueError:
            print("Invalid input. Please enter a valid number.")

def to_int_default(s, default=0):
    try:
        return int(float(s))
    except Exception:
        return default

def to_float_default(s, default=0.0):
    try:
        return float(s)
    except Exception:
        return default


# ------------------------------------------------------------------
# Functions for File Info
# ------------------------------------------------------------------

def get_audio_streams(filepath: str|Path) -> list[dict]:
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_streams",
            "-select_streams", "a",
            "-of", "json",
            str(filepath)
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        info = json.loads(result.stdout)
        return info.get("streams", [])
    except:
        return []

def get_file_info(path: Path):
    ffprobe_path = is_app_installed("ffprobe", package_name="ffmpeg")
    if ffprobe_path is None:
        raise Exception("ffprobe not found")

    info = {
        "path": path,
        "filename": path.stem,
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
        "size_bytes": path.stat().st_size if path.is_file() else None,
        "type": None,
        "is_video": False,
        "is_image": False,
        "duration": None,
        "fps": None,
        "width": None,
        "height": None,
    }

    if not info["is_file"]:
        return info

    mime, _ = mimetypes.guess_type(str(path))
    info["type"] = mime

    if mime and mime.startswith("image"):
        info["is_image"] = True
    elif mime and mime.startswith("video"):
        try:
            # ffprobe liefert Infos zu Auflösung & Dauer
            cmd = [
                ffprobe_path, "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,r_frame_rate,duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path)
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            lines = result.stdout.strip().split("\n")
            if len(lines) >= 4:
                # Framerate kommt als Bruch (z.B. 30000/1001)
                info["is_video"] = True
                info["width"]  = to_int_default(lines[0], default=0)
                info["height"] = to_int_default(lines[1], default=0)
                info["fps"]    = lines[2]
                info["duration"] = to_float_default(lines[3], default=0.0)
            info["audio_streams"] = get_audio_streams(path)
        except Exception:
            pass

    return info

# run a command and show progress
def run_command(final_cmd, process_name="Process", shell_flag: bool = False):
    fps_pattern = compile(r'frame=\s*([\d.]+)') # regex to find "frame= 1234" in ffmpeg output

    proc = subprocess.Popen(
        final_cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        shell=shell_flag
    )

    while True:
        line = proc.stderr.readline()
        if not line:
            break

        decoded = line.strip()

        fps_match = fps_pattern.search(decoded)
        if fps_match:
            fps = int(fps_match.group(1))
            print(f"{process_name} frame: {fps}", end="\r")
        else:
            print(f"{process_name}", end="\r")

    proc.wait()

    if proc.returncode != 0:
        raise Exception(f"{process_name} failed with code {proc.returncode}")
    else:
        print(f"{process_name} finished", " "*10)


# ------------------------------------------------------------------
# Check if external app is installed
# ------------------------------------------------------------------

def is_app_installed(name: str, already_tried: bool = False, package_name: str = None) -> str:
    if package_name is None:
        package_name = name

    cached_path = get_cache(name) # check cache first
    if cached_path:
        return cached_path

    exe_name = f"{name}.exe"

    # check common install paths
    # e.g. ffmpeg.exe (in Path), INSTALL_DIR/dependencies/ffmpeg/ffmpeg.exe, INSTALL_DIR/dependencies/ffmpeg/bin/ffmpeg.exe
    install_paths = [exe_name, join(DEPENDENCIES_DIR, package_name, exe_name), join(DEPENDENCIES_DIR, package_name, "bin", exe_name)]
    for exe_path in install_paths:
        try:
            # Aufruf von cugan, -version gibt Info zurück
            subprocess.run([exe_path, "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            write_cache(name, exe_path) # cache path for next time
            return exe_path
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

    # install from aesimp.com

    # Note:
    # I would love to let people download apps from official sources,
    # but the installation process is different for each app,
    # so I provide a simple way to get them all from my server.
    # As long as it's open source and free, I think it's okay.

    # If you don't trust me, you can always install them manually.
    # for ffmpeg, just download from https://ffmpeg.org/download.html
    # and put ffmpeg.exe and ffprobe.exe in the same folder as this script, or in windows path
    # for other apps, please check their official websites or github pages.

    # All information is in the readme file.

    if not already_tried:
        print(f"\nApp <{name}> not found.")
        if input("Type 'y' to install missing app <" + name + ">: ").lower() != "y":
            return None

        print(f"Try installing {name}...")
        try:
            zip_bytes = fetch_app_from_server(package_name)
            extractZIP(zip_bytes)
        except:
            raise Exception(f"Error while installing <{name}>")

        return is_app_installed(name, already_tried=True, package_name=package_name)
    return None


# ------------------------------------------------------------------
# Server Connection
# ------------------------------------------------------------------
from urllib.request import Request, urlopen
from urllib.parse import urlencode

def fetch_app_from_server(zipname) -> bytes:
    req = Request(
        f"{SERVER_URL}/aesimp-tools/application/{zipname}",
        headers={"Content-Type": "application/octet-stream"}
    )

    try:
        # get zip file from server as bytes
        with urlopen(req) as resp:
            response_bytes = resp.read()

        return response_bytes
    except Exception as e:
        raise Exception("Error while fetching app from server")

# can only install in DEPENDENCIES_DIR aesimp-tools/dependencies/
def extractZIP(zip_bytes: bytes):
    DEPENDENCIES_DIR.mkdir(parents=True, exist_ok=True)
    makedirs(str(DEPENDENCIES_DIR), exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        zf.extractall(str(DEPENDENCIES_DIR))
