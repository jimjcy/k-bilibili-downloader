from typing import *
from tkinter.messagebox import *
import tkinter as tk
from tkinter import ttk
from . import util


def askToSelect(
    title: str,
    questions: List[Tuple[str, List[str]]],
    callback: Callable[[List[int]], None],
    width: int = 40,
    master: tk.Tk | tk.Toplevel = util.rootWindow,
) -> List[int]:
    """
    Ask the user to select answers from a list of questions.

    Args:
        title (str): The title of the window.
        questions (List[Tuple[str, List[str]]]): A list of tuples, where each tuple contains a question string and a list of answer strings.

    Returns:
        List[int]: A list of indices representing the selected answers.
    """

    logger = util.getLogger("askToSelect")

    window = util.showModal(master)
    window.title(title)

    selecters: ttk.Combobox = []

    for index, (question, answers) in enumerate(questions):
        tk.Label(window, text=question).grid(
            row=index, column=0, padx=5, pady=5, sticky="e"
        )
        selecter = ttk.Combobox(window, width=width)
        selecter.grid(row=index, column=1, padx=5)
        selecters.append(selecter)
        selecter["values"] = answers
        selecter.current(0)

    buttonBox = tk.Frame(window)
    buttonBox.grid(row=len(questions), column=0, columnspan=2, pady=5, sticky="e")

    def confirmed():
        """
        Callback function for the "Confirm" button.
        Closes the window and returns the selected answers.
        """
        result = [i.current() for i in selecters]
        close()
        callback(result)

    def close():
        logger.info("window closed")
        window.destroy()

    ttk.Button(buttonBox, text="确定", command=confirmed).grid(row=0, column=1, padx=10)
    ttk.Button(buttonBox, text="取消", command=close).grid(row=0, column=0, padx=10)


def showProgress(
    title: str,
    progressName: List[str],
    _cancel: Callable[[], None],
    master: tk.Tk | tk.Toplevel = util.rootWindow,
    length: int = 300,
) -> Tuple[
    Callable[[], None],
    Tuple[Callable[[], None], Callable[[], None]],
    Tuple[ttk.Progressbar, ...],
]:
    logger = util.getLogger("showProgress")
    window = util.showModal(master)
    window.title(title)

    result: List[ttk.Progressbar] = []

    for index, name in enumerate(progressName):
        tk.Label(window, text=name).grid(
            row=index, column=0, padx=5, pady=5, sticky="e"
        )
        progress = ttk.Progressbar(
            window, orient="horizontal", mode="determinate", length=length
        )
        progress.grid(row=index, column=1, padx=5, sticky="w")
        result.append(progress)

    buttonBox = tk.Frame(window)
    buttonBox.grid(row=len(progressName), column=0, columnspan=2, pady=5, sticky="e")

    def ok():
        """
        Callback function for the "OK" button.
        Closes the window.
        """
        close()
    def _cancel():
        """
        Callback function for the "Cancel" button.
        Calls the `cancel` function and closes the window.
        """
        _cancel()
        close()
    def close():
        logger.info("window closed")
        window.destroy()

    okButton = ttk.Button(buttonBox, text="确定", command=ok, state=tk.DISABLED)
    okButton.grid(row=0, column=1, padx=5)
    ttk.Button(buttonBox, text="取消", command=_cancel).grid(row=0, column=0, padx=5)

    return (
        close,
        (
            lambda: okButton.config(state=tk.NORMAL),
            lambda: okButton.config(state=tk.DISABLED),
        ),
        tuple(result),
    )
