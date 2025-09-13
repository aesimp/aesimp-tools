from pathlib import Path
from helper import get_file_info, is_app_installed, run_command

def start(mode, params):
    ffmpeg_path = is_app_installed("ffmpeg") # get ffmpeg path
    if ffmpeg_path is None:
        raise Exception("ffmpeg not found")

    for p in params:
        path = Path(p)
        file_info = get_file_info(path)

        fps = file_info.get("fps", 60)

        width = file_info.get("width")
        height = file_info.get("height")

        # ------ calculate ------
        #
        # Scale & Encode Settings
        #
        # ------ calculate end ------

        output_path = path.parent.joinpath(f"{path.stem}-upload.mp4")

        cmd = f'{ffmpeg_path} -y -i "{str(path)}" #### "{str(output_path)}"'
        run_command(cmd)