import asyncio
import logging
import re
import shlex
import subprocess
from typing import Optional, Tuple

from .exceptions import YtDlpError
from .ffmpeg import cleanup_commands
from .types.raw import VideoParameters

py_logger = logging.getLogger("pytgcalls")


class YtDlp:
    YOUTUBE_REGX = re.compile(
        r"^((?:https?:)?//)?((?:www|m)\.)?"
        r"(youtube(-nocookie)?\.com|youtu.be)"
        r"(/(?:[\w\-]+\?v=|embed/|live/|v/)?)"
        r"([\w\-]+)(\S+)?$",
    )

    @staticmethod
    def is_valid(link: str) -> bool:
        return bool(YtDlp.YOUTUBE_REGX.match(link))

    @staticmethod
    async def extract(
        link: Optional[str],
        video_parameters: VideoParameters,
        add_commands: Optional[str],
    ) -> Tuple[Optional[str], Optional[str]]:
        if link is None:
            return None, None

        commands = [
            "yt-dlp",
            "-g",
            "-f",
            "bestvideo[vcodec~='(vp09|avc1)']+m4a/best",
            "-S",
            "res:" + f"{min(video_parameters.width, video_parameters.height)}",
            "--no-warnings",
            "--extractor-args", "youtubetab:skip=authcheck",  
        ]

        if add_commands:
            commands += await cleanup_commands(
                shlex.split(add_commands),
                "yt-dlp",
                [
                    "-f",
                    "-g",
                    "--no-warnings",
                    "--extractor-args",  # jika mau allow override dari luar
                ],
            )

        commands.append(link)

        py_logger.log(
            logging.DEBUG,
            f'Running with "{" ".join(commands)}" command',
        )

        loop = asyncio.get_running_loop()
        try:
            proc_res = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    commands,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    timeout=20,
                ),
            )
            if proc_res.returncode != 0:
                raise YtDlpError(proc_res.stderr)

            stdout: str = proc_res.stdout

            data = stdout.strip().split("\n")
            if data:
                return data[0], data[1] if len(data) >= 2 else data[0]
            raise YtDlpError("No video URLs found")
        except FileNotFoundError:
            raise YtDlpError("yt-dlp is not installed on your system")
