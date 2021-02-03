from termcolor import colored
from string import Template
from math import floor, log


class DeltaTemplate(Template):
    delimiter = "%"


def strfdelta(tdelta, fmt):
    d = {"D": tdelta.days}
    hours, rem = divmod(tdelta.seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    d["H"] = '{:02d}'.format(hours)
    d["M"] = '{:02d}'.format(minutes)
    d["S"] = '{:02d}'.format(seconds)
    t = DeltaTemplate(fmt)
    return t.substitute(**d)


def humanFormat(number):
    units = ['', 'K', 'M', 'G', 'T', 'P']
    k = 1000.0
    magnitude = int(floor(log(number, k)))
    return '%.2f%s' % (number / k**magnitude, units[magnitude])


def colorGood(strr):
    return colored(strr, 'green')


def colorEh(strr):
    return colored(strr, 'yellow')


def colorBad(strr):
    return colored(strr, 'red')


def colorHigh(strr):
    return colored(strr, 'cyan')


def colorLow(strr):
    return colored(strr, 'magenta')


def colorClock(strr):
    return colored(text=strr, color='grey', on_color='on_yellow')


def colorUptime(strr):
    return colored(text=strr, color='grey', on_color='on_cyan')


def colorTrades(strr):
    return colored(text=strr, color='grey', on_color='on_magenta')


def colorThreshold(number, dig=3, threshold=0, rev=False):
    '''
    Color code a number.
    '''
    if type(number) == float:
        number = round(number, dig)
        try:
            if not rev:
                if number > threshold:
                    form = colorGood(number)
                elif number < threshold:
                    form = colorBad(number)
                else:
                    form = colorEh(number)
            elif rev:
                if number < threshold:
                    form = colorGood(number)
                elif number > threshold:
                    form = colorBad(number)
                else:
                    form = colorEh(number)
        except:
            print('Couldn\'t colorize')
        return form
    else:
        return colorEh(number)


def colorSymbol(strr):
    pair = strr.split('/')
    # return colored(pair[0], 'blue', 'on_white')+colored('/', 'white', 'on_grey')+colored(pair[1], 'white', 'on_blue')
    return colored(strr, 'white', 'on_blue')
