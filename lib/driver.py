from . import util
from . import types
from typing import *
import platform
import subprocess


def getBrowserVersion() -> types.BrowserConfig:
    logger = util.getLogger("getBrowserVersion")
    logger.info("getting system info")
    system = tuple(platform.uname())[0]
    logger.info(f"system: {system}")
    if system == "Windows":
        logger.info("getting browser info")
        EdgeVersion = subprocess.check_output(
            [
                "powershell",
                "-command",
                "&{(Get-Item 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe').VersionInfo.ProductVersion}",
            ]
        ).decode("utf-8")[:-2]
        if EdgeVersion == "":
            logger.warning("Edge isn't installed, getting Chrome version")
            ChromeVersion = subprocess.check_output(
                [
                    "powershell",
                    "-command",
                    "&{(Get-Item 'C:\Program Files\Google\Chrome\Application\chrome.exe').VersionInfo.ProductVersion}",
                ]
            ).decode("utf-8")[:-2]
            if ChromeVersion == "":
                logger.warning("Chrome isn't installed, return none")
                return types.BrowserConfig(system, "none", "")
            logger.info(f"Chrome version: {ChromeVersion}")
            return types.BrowserConfig(system, "chrome", ChromeVersion)
        logger.info(f"Successfully, Edge version: {EdgeVersion}")
        return types.BrowserConfig(system, "edge", EdgeVersion)
    elif system == "Linux":
        return types.BrowserConfig(system, "none", "")
    
