from termcolor import colored


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


def colorProfit(number):
    '''
    Color code a number.
    '''
    number = round(number, 3)
    try:
        if number > 0:
            form = colorGood(number)
        elif number < 0:
            form = colorBad(number)
        else:
            form = colorEh(number)
    except:
        print('Couldn\'t colorize')
    return form
