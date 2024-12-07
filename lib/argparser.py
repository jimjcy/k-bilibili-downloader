from typing import *
import lib.types as types
import argparse

argParser = argparse.ArgumentParser()

argParser.add_argument("-t", "--timeout", type=int, help="timeout", default=10)
argParser.add_argument(
    "-l",
    "--log-level",
    choices=["DEBUG", "INFO", "WARNING", "ERROR"],
    default="INFO",
    help="log level",
)

argParser.add_argument("-f", "--ffmpeg", type=str, help="ffmpeg path", default="ffmpeg")


config = types.Config()

def parse():
    global config
    config = types.Config(**vars(argParser.parse_args()))
