from pathlib import Path
from shutil import rmtree
from helper import get_file_info, is_app_installed, run_command, extract_num, intput

def start(mode, params):
    ffmpeg_path = is_app_installed("ffmpeg")
    if ffmpeg_path is None:
        raise Exception("ffmpeg not found")

    rife_path = is_app_installed("rife-ncnn-vulkan")
    if rife_path is None:
        raise Exception("rife-ncnn-vulkan not found")

    factor = intput(min=2, max=16, default=8, info="The quality can decrease by higher value")

    for p in params:
        path = Path(p)
        file_info = get_file_info(path)
        if file_info is None:
            print(f"file info not found <{str(path)}>")
            input("Press Enter to continue: ")
            continue

        tmp_dir = None
        try:
            if file_info["is_video"]: # decompose to folder
                tmp_dir = path.parent.joinpath(path.stem)
                tmp_dir.mkdir(parents=True, exist_ok=True)
                run_command(fr'{ffmpeg_path} -i "{str(path)}" "{str(tmp_dir)}\%08d.png"', "decompose") # decompose
                path = Path(tmp_dir)

            # is image
            if path.is_file():
                raise Exception("Please select a video or folder")
            elif path.is_dir():
                output_path = path.joinpath("interpolate")
                output_path.mkdir(parents=True, exist_ok=True)

            # all .png Files (not recursive)
            files = [f for f in path.glob("*.png")]
            numFrames = len(files) * factor

            cmd = f'{rife_path} -i "{str(path)}" -n {str(numFrames)} #### -o "{str(output_path)}"'
            run_command(cmd, "interpolate")

            n = factor - 1  # delete last generated frames to avoid duplicates
            files = [f for f in output_path.glob("*.png")]
            files_sorted = sorted(files, key=extract_num, reverse=True)
            # delete n frames
            for f in files_sorted[:n]:
                f.unlink()


            target_file = Path(file_info.get("path")).parent.joinpath(f"{file_info.get('filename')}-flowframe.mov")
            cmd = f'{ffmpeg_path} -y -framerate 60 -i "{str(output_path)}\%08d.png" #### "{str(target_file)}"'
            run_command(cmd, "encode")
        finally:
            # delete temp folder which is just for building frames
            if file_info["is_video"]:
                if tmp_dir is not None:
                    try:
                        rmtree(tmp_dir)
                    except Exception as e:
                        print("\nFolder not deleted!")
                        input("\nPress Enter to continue: ")