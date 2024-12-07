import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import os
import requests
import json
import threading
from typing import *
import re
import io
import pyperclip
import tempfile
import pathlib
import time
import subprocess
import logging
import sys
from PIL import Image, ImageTk
import zipfile
# from rich.progress import track

if getattr(sys, "frozen", None):
    dataBasePath = pathlib.Path(sys._MEIPASS)
else:
    dataBasePath = pathlib.Path(os.getcwd()).joinpath("data")


def dataPath(filename: str | pathlib.Path):
    if isinstance(filename, str):
        filename = pathlib.Path(filename)
    return dataBasePath.joinpath(filename)


tempRoot = pathlib.Path(tempfile.gettempdir()).joinpath(
    f"k-bilibili-download-{time.time()}"
)
if not tempRoot.exists():
    os.mkdir(tempRoot)

fileLogHandler = logging.FileHandler(
    filename=str(tempRoot.joinpath("log.txt")),
    mode="w",
    encoding="utf-8",
)
fmter = logging.Formatter(
    fmt="[%(asctime)s] [%(name)s] [t-%(thread)d] [%(levelname)s]: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

consoleLogHandler = logging.StreamHandler()

rootLogger = logging.getLogger()

rootLogger.addHandler(fileLogHandler)
rootLogger.addHandler(consoleLogHandler)
rootLogger.setLevel(logging.DEBUG)

fileLogHandler.setLevel(logging.INFO)
fileLogHandler.setFormatter(fmter)
consoleLogHandler.setLevel(logging.INFO)
consoleLogHandler.setFormatter(fmter)

rootLogger.info(f"base dir: {dataBasePath}")


root = tk.Tk()


def showModal(master: tk.Tk | tk.Toplevel) -> tk.Toplevel:
    window = tk.Toplevel(master)
    window.transient(master)
    window.grab_set()
    window.geometry("".join(["+" + i for i in master.geometry().split("+")[-2:]]))
    window.resizable(0, 0)
    return window


def _download(
    url: str,
    header: Dict[str, str],
    saveIO: io.FileIO,
    succeed: Callable[[], None],
    fail: Callable[[], None],
    progress: ttk.Progressbar,
):
    logger = rootLogger.getChild("_download")

    logger.info(f"start downloading {url}")

    try:
        response = requests.get(url, headers=header, stream=True, timeout=60)
        logger.info(f"response status code: {response.status_code}")

        assert response.status_code // 100 == 2

        progress["maximum"] = int(response.headers["Content-Length"])

        for i in response.iter_content(1024):
            saveIO.write(i)
            progress["value"] += len(i)
            progress.update()

    except Exception as e:
        logger.warning(f"download failed: {e.__class__.__name__}: {e}")

        fail()
    else:
        saveIO.close()
        logger.info("download succeed")
        succeed()


def startDownload(
    videoInfo: dict, audioInfo: dict, header: dict, savePath: pathlib.Path
):
    logger = rootLogger.getChild("startDownload")

    videoPath = tempRoot.joinpath(f"video-{time.time()}.tmp")
    audioPath = tempRoot.joinpath(f"audio-{time.time()}.tmp")

    logger.info(f"videoPath: {videoPath}, audioPath: {audioPath}")

    progressWindow = showModal(root)
    progressWindow.title("下载进度")

    _main = tk.Frame(progressWindow)
    _main.grid(column=0, row=0, padx=10, pady=10)

    tk.Label(_main, text="视频").grid(row=0, column=0, sticky="e")
    tk.Label(_main, text="音频").grid(row=1, column=0, sticky="e")
    tk.Label(_main, text="转码").grid(row=2, column=0, sticky="e")

    videoProgress = ttk.Progressbar(
        _main, orient="horizontal", mode="determinate", length=200
    )
    audioProgress = ttk.Progressbar(
        _main, orient="horizontal", mode="determinate", length=200
    )
    mergeProgress = ttk.Progressbar(
        _main, orient="horizontal", mode="indeterminate", length=200
    )
    mergeProgress.start()

    videoProgress.grid(row=0, column=1)
    audioProgress.grid(row=1, column=1)
    mergeProgress.grid(row=2, column=1)

    buttonBox = tk.Frame(_main)
    buttonBox.grid(row=3, column=0, columnspan=2, sticky="E")

    def cancel():
        logger.info("download cancel")
        for i in [videoThread, audioThread, mergeThread]:
            try:
                i._stop()
            except Exception:
                pass
        close()

    def close():
        progressWindow.destroy()
        logger.info("window closed")

    ttk.Button(buttonBox, text="取消", command=cancel).grid(row=0, column=0)

    okButton = ttk.Button(buttonBox, text="确定", state="disabled")
    okButton.grid(column=1, row=0)

    succeed = 0

    def downloadSuccess():
        nonlocal succeed
        succeed += 1
        if (succeed) >= 2:
            logger.info("download success")
            _start("merge")

    def fail(t=Literal["video", "audio"]):
        logger.info(f"{t} download failed")
        if messagebox.askokcancel("错误", f"{t}下载失败，是否重试"):
            logger.info(f"{t} download retry")
            _start(t)
        else:
            logger.info(f"download cancel, case by download {t} fail")
            cancel()

    def mergeSuccess():
        close()
        logger.info("merge succeed, download complete")
        messagebox.showinfo("完成", "下载完成")

    def mergeFail():
        logger.info("merge failed")
        if messagebox.askokcancel("错误", "合并失败，是否重试"):
            logger.info("merge retry")
            _start("merge")
        else:
            logger.info("download cancel, case by merge fail")
            cancel()

    videoThread: threading.Thread | None = None
    audioThread: threading.Thread | None = None
    mergeThread: threading.Thread | None = None

    def _start(t=Literal["video", "audio", "merge"]):
        nonlocal videoThread, audioThread, mergeThread
        logger.info(f"start thread: {t}")
        if t == "video":
            videoThread = threading.Thread(
                target=_download,
                args=(
                    videoInfo["baseUrl"],
                    header,
                    io.FileIO(videoPath, "wb"),
                    downloadSuccess,
                    lambda: fail(t),
                    videoProgress,
                ),
                daemon=True,
            )
            videoThread.start()
            logger.info(f"video thread started in thread {videoThread.ident}")
        elif t == "audio":
            audioThread = threading.Thread(
                target=_download,
                args=(
                    audioInfo["baseUrl"],
                    header,
                    io.FileIO(audioPath, "wb"),
                    downloadSuccess,
                    lambda: fail(t),
                    audioProgress,
                ),
                daemon=True,
            )
            audioThread.start()
            logger.info(f"audio thread started in thread {videoThread.ident}")
        elif t == "merge":
            mergeThread = threading.Thread(
                target=mergeVideo,
                args=(videoPath, audioPath, savePath, mergeSuccess, mergeFail),
                daemon=True,
            )
            mergeThread.start()
            logger.info(f"merge thread started in thread {mergeThread.ident}")

    logger.info("window initialized")

    _start("video")
    _start("audio")


def requestDownload():

    logger = rootLogger.getChild("requestDownload")

    video = videoVar.get()
    cookie = cookieVar.get().replace("\r", "").replace("\n", "")
    savePath = savePathVar.get()

    logger.info(f"video: {video}, cookie: {cookie}, savePath: {savePath}")

    if not (video and cookie and savePath):
        logger.info("Incomplete information, return")
        messagebox.showerror("错误", "请填写完整信息")
        return
    if re.match(
        r"^(((ht|f)tps?):\/\/)?([^!@#$%^&*?.\s-]([^!@#$%^&*?.\s]{0,63}[^!@#$%^&*?.\s])?\.)+[a-z]{2,6}\/?",
        video,
    ):
        url = video
        logger.info("input type is url")
    elif re.match(
        re.compile("av[1-9][0-9]*", re.I),
        video,
    ) or re.match("(?:B|b)(?:v|V)[0-9a-zA-Z]{10}", video):
        url = f"https://www.bilibili.com/video/{video}?spm_id_from=player_end_recommend_autoplay"
        logger.info(f"input type is av/bv, transform to url: {url}")
    elif re.match(
        re.compile("(?:ep|ss)[1-9][0-9]*", re.I),
        video,
    ):
        url = f"https://www.bilibili.com/bangumi/play/{video}"
        logger.info(f"input type is ep, transform to url: {url}")
    else:
        logger.info("input type is invalid, return")
        messagebox.showerror("错误", "请输入正确的视频地址或av号/BV号")
        return
    headers = {
        "Referer": url,
        "Cookie": cookie,
        "Accept": "*/*" "Accept-language:zh-CN,zh;q=0.9,en;q=0.8",
        "sec-ch-ua": '"Microsoft Edge";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-site",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0",
    }

    try:
        logger.info(f"request page url: {url}, headers: {headers}")
        response = requests.get(url, headers=headers, timeout=60)
        logger.info(f"response status code: {response.status_code}")
        assert response.status_code // 100 == 2
        html = response.text
    except Exception as e:
        logger.warning(
            f"Can't get page response with error {e.__class__.__name__}:{str(e)}"
        )
        messagebox.showerror(
            "错误",
            f"请求错误，无法获取页面信息\n{e.__class__.__name__}:{str(e)}",
        )
        return

    try:
        logger.info("start parse page")
        flag = False
        f = open("a.html", "w", encoding="utf-8")
        f.write(response.text)
        f.close()
        for i, maper in [
            (
                re.compile(r"window.__playinfo__=(.*?)</script>", re.S),
                lambda x: x["data"],
            ),
            (
                re.compile(
                    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
                    re.S,
                ),
                lambda x: [
                    i["state"]["data"]["result"]["video_info"]
                    for i in x["props"]["pageProps"]["dehydratedState"]["queries"]
                    if i.get("state", {})
                    .get("data", {})
                    .get("result", {})
                    .get("video_info")
                ][0],
            ),
        ]:
            try:
                palyInfo = maper(json.loads(re.findall(i, html)[0]))
            except Exception:
                continue
            else:
                flag = True
                break
        if not flag:
            logger.warning("Can't find playinfo in page")
            raise Exception("Can't find playinfo in page")

        acceptQuality: Dict[int, str] = dict(
            zip(
                palyInfo["accept_quality"],
                palyInfo["accept_description"],
            )
        )

        videoList: List[dict] = palyInfo["dash"]["video"]
        audioList: List[dict] = palyInfo["dash"]["audio"]

        assert len(audioList)
        assert len(videoList)

    except Exception as e:
        logger.warning(
            f"Can't parse page with error {e.__class__.__name__}:{str(e)}, return"
        )
        messagebox.showerror("错误", "解析错误，无法获取视频信息")
        return
    try:
        logger.info("Validating the save path")
        open(savePath, "wb").close()
    except Exception:
        logger.warning("Invalid save path, return")
        messagebox.showerror("错误", "无法打开保存路径")
        return

    def askDownloadTypeCallback(videoInfo: dict, audioInfo: dict):
        logger.info("download information confirmed")
        startDownload(videoInfo, audioInfo, headers, savePath)

    logger.info("start ask download type")
    askDownloadType(videoList, audioList, acceptQuality, askDownloadTypeCallback)


def askDownloadType(
    videoList: List[Dict],
    audioList: List[Dict],
    acceptQuality: Dict[int, str],
    callback: Callable[[Dict, Dict], None],
):
    logger = rootLogger.getChild("askDownloadType")

    selectWindow = showModal(root)
    selectWindow.title("选择音视频通道")

    _main = tk.Frame(selectWindow)
    _main.grid(row=0, column=0, padx=10, pady=10)

    tk.Label(_main, text="视频通道:").grid(row=0, column=0)
    tk.Label(_main, text="音频通道:").grid(row=1, column=0)

    videoCombobox = ttk.Combobox(_main, width=40)
    videoCombobox["values"] = [
        f"{index+1}. {acceptQuality.get(value.get('id',-1),'Unknown')} - {value.get('width')}x{value.get('height')}@{value.get('frameRate')}fps"
        for index, value in enumerate(videoList)
    ]
    videoCombobox.current(0)
    videoCombobox.config(state="readonly")

    videoCombobox.grid(row=0, column=1)

    audioCombobox = ttk.Combobox(_main, width=40)
    audioCombobox["values"] = [
        f"{index+1}. {value.get('id',-1)} - {value.get('codecs')}"
        for index, value in enumerate(audioList)
    ]
    audioCombobox.current(0)
    audioCombobox.config(state="readonly")

    audioCombobox.grid(row=1, column=1)

    buttonBox = tk.Frame(_main)
    buttonBox.grid(row=2, column=0, columnspan=2, pady=10, sticky="e")

    def confirmed():
        logger.info(
            f"download information confirmed by user, v:{videoCombobox.current()} a:{audioCombobox.current()}"
        )
        video = videoList[videoCombobox.current()]
        audio = audioList[audioCombobox.current()]
        close()
        logger.info("End this life cycle")
        callback(video, audio)

    def close():
        logger.info("window closed")
        selectWindow.destroy()

    ttk.Button(buttonBox, text="取消", command=close).grid(row=0, column=0)
    ttk.Button(buttonBox, text="确认", command=confirmed).grid(row=0, column=1, padx=2)

    logger.info("window initialized")


def mergeVideo(
    videoPath: pathlib.Path,
    audioPath: pathlib.Path,
    savePath: pathlib.Path,
    mergeSuccess: Callable[[], None],
    mergeFail: Callable[[], None],
):
    logger = rootLogger.getChild("mergeVideo")

    logger.info(f"merge video: {videoPath}, audio: {audioPath}, save: {savePath}")

    ffmpegProcess = subprocess.Popen(
        [
            "ffmpeg",
            "-hide_banner",
            "-i",
            str(videoPath),
            "-i",
            str(audioPath),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-strict",
            "experimental",
            savePath,
            "-y",
        ],
        text=True,
        bufsize=50,
    )
    logger.info("ffmpeg process started")
    ffmpegProcess.wait()
    logger.info(f"ffmpeg process ended, with code: {ffmpegProcess.returncode}")
    if ffmpegProcess.returncode != 0:
        logger.warning("ffmpeg process failed")
        mergeFail()
        return
    logger.info("ffmpeg process success")
    mergeSuccess()


class HelpButton(tk.Label):
    img = ImageTk.PhotoImage(
        Image.open(dataPath("help.png")).resize((18, 18), Image.LANCZOS)
    )
    helpTitle: str
    helpText: str

    def __init__(self, master, helpTitle: str, helpText: str, **kwargs):
        super().__init__(
            master,
            image=self.img,
            width=18,
            height=18,
            **kwargs,
            padx=2,
            pady=2,
            cursor="hand2",
        )
        self.helpTitle = helpTitle
        self.helpText = helpText
        self.bind("<Button-1>", self._showHelp)

    def _showHelp(self, *_args, **_kw):
        messagebox.showinfo(self.helpTitle, self.helpText)


rootLogger.info("starting")

root.title("视频下载器")
root.resizable(0, 0)

try:
    root.iconphoto(True, tk.PhotoImage(file=str(dataPath("icon.png"))))
except Exception as e:
    rootLogger.warning("failed to load icon")
else:
    rootLogger.info("icon loaded")


main = tk.Frame()
main.grid(row=0, column=0, padx=10, pady=10)

tk.Label(main, text="视频URL/ID号:").grid(row=0, column=0, sticky="e")

videoVar = tk.StringVar()

urlEntry = ttk.Entry(main, textvariable=videoVar, width=30)
urlEntry.grid(row=0, column=1)

HelpButton(
    main,
    helpTitle="关于视频URL/ID号",
    helpText="除了直接的b站链接外，目前还支持：\nBV号、AV号、EP号、SS号",
).grid(row=0, column=3)

ttk.Button(main, text="粘贴", command=lambda: videoVar.set(pyperclip.paste())).grid(
    row=0, column=2
)

cookieVar = tk.StringVar()
tk.Label(main, text="Cookie:").grid(row=1, column=0, sticky="e")
cookieEntry = ttk.Entry(main, textvariable=cookieVar, width=30)
cookieEntry.grid(row=1, column=1)

ttk.Button(main, text="粘贴", command=lambda: cookieVar.set(pyperclip.paste())).grid(
    row=1, column=2
)

HelpButton(
    main,
    helpTitle="关于Cookie",
    helpText="需要登录后才能下载，可以在浏览器中复制出来",
).grid(row=1, column=3)

savePathVar = tk.StringVar()
tk.Label(main, text="保存路径:").grid(row=2, column=0, sticky="e")
pathEntry = ttk.Entry(main, textvariable=savePathVar, width=30)
pathEntry.grid(row=2, column=1)

ttk.Button(
    main,
    text="选择",
    command=lambda: savePathVar.set(
        filedialog.asksaveasfilename(
            title="选择保存路径",
            filetypes=[("视频文件", ["*.mp4"]), ("所有文件", "*.*")],
            defaultextension=".mp4",
            parent=root,
        )
    ),
).grid(row=2, column=2)


def downloadButtonOnClick():
    downloadButton.configure(state="disabled")
    requestDownloadThread = threading.Thread(
        target=lambda: (requestDownload(), downloadButton.configure(state="normal")),
        daemon=True,
    )
    requestDownloadThread.start()
    rootLogger.info(
        f"download button onclick, starting download thread %{requestDownloadThread.ident}"
    )


downloadButton = ttk.Button(main, text="下载", command=downloadButtonOnClick)
downloadButton.grid(row=3, column=0, pady=10, columnspan=3, sticky="we")

rootLogger.info("Done")

root.mainloop()
