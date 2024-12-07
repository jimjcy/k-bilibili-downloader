from typing import *
from dataclasses import dataclass


@dataclass(frozen=True, eq=True)
class Config:
    timeout: int = 10
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    ffmpeg: str = "ffmpeg"

PlayInfo = Dict

@dataclass
class VideoPart:
    title: str
    playinfo: Callable[[], PlayInfo]
