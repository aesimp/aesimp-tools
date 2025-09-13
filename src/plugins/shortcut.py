from pathlib import Path
from helper import get_file_info, is_app_installed, run_command, intput

def get_ffmpeg_audio_map_params(audio_streams: list[dict]) -> str:
    """
    Get the audio parameters from FFprobe:
    - If no or only one track -> map first track directly
    - If multilingual -> select Japanese, if necessary extract Front-Center
    """
    if not audio_streams:
        return "-map 0:a:0"  # fallback: first Audio-track
    
    # Default: last track
    selected_stream = audio_streams[-1]
    
    # Search for Japanese track
    for stream in audio_streams:
        tags = stream.get("tags", {})
        language = tags.get("language", "").lower()
        title = tags.get("title", "").lower()
        if any(x in language for x in ["jpn", "japan", "japanese"]) or any(x in title for x in ["jpn", "japan", "japanese"]):
            selected_stream = stream # found japanese stream
            break
    
    stream_index = selected_stream.get("index", 0)
    channels = selected_stream.get("channels", 2)
    
    if channels > 2:  # 5.1 track or more -> extract Front-Center
        return f'-filter_complex "[0:a]pan=mono|c0=FC[a]" -map "[a]" -c:a aac'
    else:
        # fallback: original track copy
        return f'-map 0:a:{stream_index-1} -c copy'


def start(mode, params):
    ffmpeg_path = is_app_installed("ffmpeg")
    if ffmpeg_path is None:
        raise Exception("ffmpeg not found")

    for p in params:
        path = Path(p)
        file_info = get_file_info(path)

        cmd = None
        shell_flag = False

        if not file_info.get("is_video", False):
            raise Exception("File must be a video")

        if mode == "remux":
            ffmpeg_params = get_ffmpeg_audio_map_params(file_info.get("audio_streams", []))

            output_path = path.parent.joinpath(f"{path.stem}-{mode}.mp4")
            cmd = f'{ffmpeg_path} -y -i "{str(path)}" -map 0:v {ffmpeg_params} #### "{str(output_path)}" 2>nul || {ffmpeg_path} -y -i "{str(path)}" #### "{str(output_path)}"'
            shell_flag = True
        elif mode == "decompose":
            output_path = path.parent.joinpath(path.stem)
            output_path.mkdir(parents=True, exist_ok=True)
            cmd = fr'{ffmpeg_path} -y -i "{str(path)}" "{str(output_path)}\%08d.png"'
        elif mode == "ripAudio":
            output_path = path.parent.joinpath(f"{path.stem}-{mode}.mp3")
            cmd = f'{ffmpeg_path} -y -i "{str(path)}" -q:a 0 -map a "{str(output_path)}"'
        elif mode == "compress": # just use downscale with original size
            crf = intput(min=1, max=51, default=15, info="Lower is better quality but larger filesize")
            fps = file_info.get("fps", 60)
            output_path = path.parent.joinpath(f"{path.stem}-{mode}.mp4")

            cmd = f'{ffmpeg_path} -y -i "{str(path)}" #### "{str(output_path)}"'
        elif mode == "downscale":
            fps = file_info.get("fps", 60)
            width = file_info.get("width")
            height = file_info.get("height")

            crf = intput(min=1, max=51, default=15, info="Lower is better quality but larger filesize")

            text = "width" if width < height else "height"
            scale = intput(min=360, max=2160, default=file_info.get(text), info=f"Please enter the target size for <{text}> (original: {file_info.get(text)}): ")

            if scale is not None:
                if width < height:
                    width_scale = scale
                    height_scale = int(round((height / width) * width_scale, 0))
                else:
                    height_scale = scale
                    width_scale = int(round((width / height) * height_scale, 0))
            else:
                height_scale = height
                width_scale = width

            output_path = path.parent.joinpath(f"{path.stem}-{mode}.mp4")
            cmd = f'{ffmpeg_path} -y -i "{str(path)}" #### "{str(output_path)}"'

        # execute command
        if cmd is not None:
            run_command(cmd, process_name=mode, shell_flag=shell_flag)