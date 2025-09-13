from pathlib import Path
from shutil import rmtree
from helper import get_file_info, is_app_installed, run_command

def start(mode, params):
    ffmpeg_path = is_app_installed("ffmpeg")
    if ffmpeg_path is None:
        print("ffmpeg not found")
        input("Press Enter to continue: ")
        return

    cugan_path = is_app_installed("cugan")
    if cugan_path is None:
        print("cugan not found")
        input("Press Enter to continue: ")
        return

    for p in params:
        path = Path(p)
        file_info = get_file_info(path)
        if file_info is None:
            print("file info not found")
            input("Press Enter to continue: ")
            return

        tmp_dir = None
        try:
            if file_info["is_video"]: # decompose to folder
                tmp_dir = path.parent.joinpath(path.stem)
                tmp_dir.mkdir(parents=True, exist_ok=True)
                run_command(fr'{ffmpeg_path} -i "{str(path)}" "{str(tmp_dir)}\%08d.png"', "decompose") # decompose
                path = Path(tmp_dir)

            # is image
            if path.is_file():
                output_path = path.parent.joinpath("upscaled", path.name)
                output_path.parent.mkdir(parents=True, exist_ok=True)
            elif path.is_dir():
                output_path = path.joinpath("upscaled")
                output_path.mkdir(parents=True, exist_ok=True)

            cmd = f'{cugan_path} -i "{str(path)}" -o "{str(output_path)}" -s 2 -n 3 -m models-pro >NUL'
            run_command(cmd, "upscale")

            if file_info["is_video"]: # reencode / concat frames
                fps = file_info.get("fps", 60)
                target_file = Path(file_info.get("path")).parent.joinpath(f"{file_info.get('filename')}-upscaled.mov")
                cmd = f'{ffmpeg_path} -y -framerate {fps} -i "{str(output_path)}\%08d.png" -i "{str(p)}" #### "{str(target_file)}"'
                run_command(cmd, "encode")
        finally:
            if file_info["is_video"]:
                if tmp_dir is not None:
                    try:
                        rmtree(tmp_dir)
                    except Exception as e:
                        print("\nFolder not deleted!")
                        print(e)
                        input("\nPress Enter to continue: ")