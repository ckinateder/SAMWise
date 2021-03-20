"""
Helper class with custom functions used by multiple other classes.
"""
import decimal
import logging
import os
import platform
import socket
import subprocess
import time
from datetime import datetime
from math import floor, log, log10
from string import Template

import psutil
from termcolor import colored
from tqdm import tqdm, trange

try:
    import pync

    notifications = True
except:
    notifications = False


def updateSize():
    return [int(i) for i in subprocess.check_output(["stty", "size"]).decode().split()]


HEIGHT, WIDTH = updateSize()
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
FILE_TIME_FORMAT = "%Y-%m-%d_%H-%M-%S"
QUOTE = "USD"
KEYPATH = "keys/"
LOGPATH = "logs/"
CHARTPATH = "chart/"
COLORING = False
# change this to turn of progress bars
BARSDISABLED = False


def color(text, color, on_color=None):
    if COLORING:
        return colored(text, color=color, on_color=on_color)
    else:
        return text


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


class TqdmLoggingHandler(logging.Handler):
    def __init__(self, level=logging.NOTSET):
        super().__init__(level)

    def emit(self, record):
        try:
            msg = self.format(record)
            tqdm.write(msg)
            self.flush()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


# create logs
logs = logging.getLogger(__name__)
logs.setLevel(logging.DEBUG)
# create file handler which logs even debug messages
fh = logging.FileHandler(f"{LOGPATH}{nowD().strftime('%Y-%m-%d_%H-%M-%S')}.log")
# fh.setLevel(logging.DEBUG)
ch = TqdmLoggingHandler()  # (level=logging.INFO)  # logging.StreamHandler()
# ch.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s:%(levelname)s: %(message)s")

fh.setFormatter(formatter)
# ch.setFormatter(formatter)
# add the handlers to the logs
logs.addHandler(fh)
logs.addHandler(ch)


def intro():
    """
    tqdm.write the intro string.
    """
    logs.debug("Welcome to SAMWise!".center(WIDTH))
    logs.debug("(Spatial Arbitrage Method Wizard)".center(WIDTH))
    logs.debug("Created by Calvin Kinateder, 2021".center(WIDTH))
    logs.debug(
        "calvinkinateder@gmail.com, https://ckinateder.github.io/SAMWise/".center(WIDTH)
    )
    logs.debug(
        "CTRL C to quit. Note: '$' is used to symbolize quote coin.".center(WIDTH)
    )
    logs.debug(("-" * WIDTH).center(WIDTH) + "\n")


def clear():
    """
    Clear screen.
    """
    os.system("cls" if os.name == "nt" else "clear")
    logs.debug("\n" * (HEIGHT - 1))


def getIP():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(("10.255.255.255", 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = "127.0.0.1"
    finally:
        s.close()
    return IP


def countNestedDicts(props):
    """
    Count the entries in a dict of dicts.
    """
    total = 0
    for i in props:
        total += len(props[i])
    return total


def roundSignificant(x, sig=2):
    """
    round x to sig significant digits
    """
    return round(x, sig - int(floor(log10(abs(x)))) - 1)


def searchDict(dictlist, **kwargs):
    """
    Search an array dict for kwargs. similar to a where sql call
    """
    returns = []
    for row in dictlist:
        keeptrack = True
        for argument, value in kwargs.items():
            if not row[argument] == value:
                keeptrack = False
        if keeptrack:
            returns.append(row)
    return returns


def rgb(r, g, b):
    # return a scaled tuple
    return (r / 255.0, g / 255.0, b / 255.0)


def timer(waittime):
    for interval in trange(
        waittime * 1000,
        disable=BARSDISABLED,
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
    elif l == 1:
        out = l[0]
    else:  # empty
        out = ""
    return out


def serializeQuery(query):
    """
    take the RESPONSE from a query and convert to json
    """
    result = []
    for q in query:
        pre = q.__dict__
        pre.pop("_sa_instance_state")
        for post in pre:
            if type(pre[post]) == decimal.Decimal:
                pre[post] = float(pre[post])
            elif isinstance(pre[post], datetime):
                pre[post] = pre[post].strftime(TIME_FORMAT)
        result.append(pre)
    return result


def stringitizeExc(list_of_exchanges):
    """
    Creates a string from a list of ccxt exchange objects, adding 'and' at the end.
    """
    out = ""
    for i in range(len(list_of_exchanges) - 1):
        out += list_of_exchanges[i].name + ", "
    out += "and " + list_of_exchanges[-1].name
    return out


def getInfo():
    """
    Get system platform info for footer.
    """
    l = list(platform.uname())
    return "System Info: " + " - ".join(l)


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt="%D days %H:%M:%S"):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = "{:02d}".format(hours)
    d["M"] = "{:02d}".format(minutes)
    d["S"] = "{:02d}".format(seconds)
    t = DeltaTemplate(fmt)
    formatted = t.substitute(**d)
    # get rid of 0 days
    if tdelta.days == 0:
        formatted = formatted.replace("0 days ", "")
    return formatted


def notify(message):
    """
    Send a notification to the notification center on macos
    """
    if notifications:
        pync.notify(message, title="SAMWise")


def humanFormat(number):
    """
    Shorten a long number with abbreviations
    """
    if type(number) == str:
        return colorEh(number)
    elif number <= 0:
        return colorEh(number)
    units = ["", "K", "M", "G", "T", "P"]
    k = 1000.0
    magnitude = int(floor(log(number, k)))
    return "%.2f%s" % (number / k ** magnitude, units[magnitude])


def getMemUsage():
    return humanFormat(psutil.Process(os.getpid()).memory_info().rss) + "B"


def colorGood(strr):
    """
    Color a string green.
    """
    if not type(strr) == str:
        return color(f"{strr:,}", "green")
    else:
        return color(strr, "green")


def colorEh(strr):
    """
    Color a string yellow.
    """
    if not type(strr) == str:
        return color(f"{strr:,}", "yellow")
    else:
        return color(strr, "yellow")


def colorBad(strr):
    """
    Color a string red.
    """
    if not type(strr) == str:
        return color(f"{strr:,}", "red")
    else:
        return color(strr, "red")


def colorHigh(strr):
    """
    Color a string cyan.
    """
    if not type(strr) == str:
        return color(f"{strr:,}", "cyan")
    else:
        return color(strr, "cyan")


def colorLow(strr):
    """
    Color a string magenta.
    """
    if not type(strr) == str:
        return color(f"{strr:,}", "magenta")
    else:
        return color(strr, "magenta")


def colorClock(strr):
    """
    Color a string green.
    """
    return color(text=strr, color="grey", on_color="on_yellow")


def colorUptime(strr):
    """
    Highlight a string cyan.
    """
    return color(text=strr, color="grey", on_color="on_cyan")


def colorTrades(strr):
    """
    Highlight a string magenta.
    """
    return color(text=strr, color="grey", on_color="on_magenta")


def colorCycle(strr):
    """
    Highlight a string white.
    """
    return color(text=strr, color="grey", on_color="on_white")


def colorProg(strr):
    """
    Highlight a string grey (white text).
    """
    return color(text=strr, color="white", on_color="on_grey")


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
            logs.debug("Couldn't colorize")
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
            logs.debug("Couldn't colorize")
        return form
    else:
        return colorEh(number)
