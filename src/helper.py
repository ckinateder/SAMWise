from datetime import datetime
import os
from tqdm import tqdm, trange
import subprocess
import time
from math import floor, log
from string import Template

from termcolor import colored

try:
    import pync

    notifications = True
except:
    notifications = False


def updateSize():
    return [int(i) for i in subprocess.check_output(["stty", "size"]).decode().split()]


HEIGHT, WIDTH = updateSize()
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
QUOTE = "USD"
KEYPATH = "keys/"


def intro():
    """
    tqdm.write the intro string.
    """
    tqdm.write("Welcome to SAMWise!".center(WIDTH))
    tqdm.write("(Spatial Arbitrage Method Wizard)".center(WIDTH))
    tqdm.write("Created by Calvin Kinateder, 2021".center(WIDTH))
    tqdm.write(
        "calvinkinateder@gmail.com, https://ckinateder.github.io/SAMWise/".center(WIDTH)
    )
    tqdm.write(
        "CTRL C to quit. Note: '$' is used to symbolize quote coin.".center(WIDTH)
    )
    tqdm.write(("-" * WIDTH).center(WIDTH) + "\n")


def clear():
    """
    Clear screen.
    """
    os.system("cls" if os.name == "nt" else "clear")
    tqdm.write("\n" * (HEIGHT - 1))


def timer(waittime):
    for interval in trange(
        waittime * 1000,
        leave=False,
        desc="timer",
        dynamic_ncols=True,
        position=1,
    ):
        time.sleep(0.001)


def stringitizeL(l):
    """
    Creates a string from a list, adding 'and' at the end.
    """
    if len(l) > 1:
        out = ""
        for i in range(len(l) - 1):
            out += l[i] + ", "
        out += "and " + l[-1]
    else:
        out = l[0]
    return out


def stringitizeExc(list_of_exchanges):
    """
    Creates a string from a list of ccxt exchange objects, adding 'and' at the end.
    """
    out = ""
    for i in range(len(list_of_exchanges) - 1):
        out += list_of_exchanges[i].name + ", "
    out += "and " + list_of_exchanges[-1].name
    return out


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = "{:02d}".format(hours)
    d["M"] = "{:02d}".format(minutes)
    d["S"] = "{:02d}".format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


def notify(message):
    """
    Send a notification to the notification center on macos
    """
    if notifications:
        pync.notify(message, title="SAMWise")


def now():
    """
    Shortened version of calling time.time()
    """
    return time.time()


def nowD():
    """
    Shortened version of calling datetime.now()
    """
    return datetime.now()


def humanFormat(number):
    """
    Shorten a long number with abbreversediations
    """
    if type(number) == str:
        return colorEh(number)
    units = ["", "K", "M", "G", "T", "P"]
    k = 1000.0
    magnitude = int(floor(log(number, k)))
    return "%.2f%s" % (number / k ** magnitude, units[magnitude])


def colorGood(strr):
    """
    Color a string green.
    """
    if not type(strr) == str:
        return colored(f"{strr:,}", "green")
    else:
        return colored(strr, "green")


def colorEh(strr):
    """
    Color a string yellow.
    """
    if not type(strr) == str:
        return colored(f"{strr:,}", "yellow")
    else:
        return colored(strr, "yellow")


def colorBad(strr):
    """
    Color a string red.
    """
    if not type(strr) == str:
        return colored(f"{strr:,}", "red")
    else:
        return colored(strr, "red")


def colorHigh(strr):
    """
    Color a string cyan.
    """
    if not type(strr) == str:
        return colored(f"{strr:,}", "cyan")
    else:
        return colored(strr, "cyan")


def colorLow(strr):
    """
    Color a string magenta.
    """
    if not type(strr) == str:
        return colored(f"{strr:,}", "magenta")
    else:
        return colored(strr, "magenta")


def colorClock(strr):
    """
    Color a string green.
    """
    return colored(text=strr, color="grey", on_color="on_yellow")


def colorUptime(strr):
    """
    Highlight a string cyan.
    """
    return colored(text=strr, color="grey", on_color="on_cyan")


def colorTrades(strr):
    """
    Highlight a string magenta.
    """
    return colored(text=strr, color="grey", on_color="on_magenta")


def colorCycle(strr):
    """
    Highlight a string white.
    """
    return colored(text=strr, color="grey", on_color="on_white")


def colorProg(strr):
    """
    Highlight a string grey (white text).
    """
    return colored(text=strr, color="white", on_color="on_grey")


def colorThreshold(number, dig=3, threshold=0, reversed=False):
    """
    Color code a number based on a threshold.
    """
    if type(number) == float:
        number = round(number, dig)
        try:
            if not reversed:
                if number > threshold:
                    form = colorGood(number)
                elif number < threshold:
                    form = colorBad(number)
                else:
                    form = colorEh(number)
            elif reversed:
                if number < threshold:
                    form = colorGood(number)
                elif number > threshold:
                    form = colorBad(number)
                else:
                    form = colorEh(number)
        except:
            tqdm.write("Couldn't colorize")
        return form
    else:
        return colorEh(number)


def colorLiquidity(number, threshold=0):
    """
    Color code a LARGE number based on a threshold.
    """
    if type(number) == float:
        try:
            if number > threshold:
                form = colorGood(humanFormat(number))
            elif number < threshold:
                form = colorBad(humanFormat(number))
            else:
                form = colorEh(humanFormat(number))
        except:
            tqdm.write("Couldn't colorize")
        return form
    else:
        return colorEh(number)
