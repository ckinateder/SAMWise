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
