
from pprint import pprint
from math import log, floor
import pandas as pd

try:
    from pynput import keyboard
    dynamic_input = True
except:
    dynamic_input = False

__author__ = 'Calvin Kinateder'
__email__ = 'calvinkinateder@gmail.com'


from main import getAvailableExchanges, loadExchanges
keypath = 'keys/'


def human_format(number):
    units = ['', 'K', 'M', 'G', 'T', 'P']
    k = 1000.0
    magnitude = int(floor(log(number, k)))
    return '%.2f%s' % (number / k**magnitude, units[magnitude])


def getTableOfAll():
    availables = getAvailableExchanges()
    # availables.remove('bittrex')
    exchanges = loadExchanges(availables)
    index = list()

    for i in exchanges:
        x = list(i.load_markets().keys())
        for j in x:
            if 'USD' in j:
                index.append(j)

    index = list(set(index))

    alls = list()
    for i in exchanges:
        alls.append(i.id)

    headers = alls
    headers.insert(0, 'ticker')

    yes_and_no = pd.DataFrame(columns=headers)
    yes_and_no['ticker'] = index

    for exchange in exchanges:
        for i in range(0, len(index)):
            marks = list(exchange.load_markets().keys())
            if index[i] in marks:
                yes_and_no[exchange.id][i] = True
            else:
                yes_and_no[exchange.id][i] = False
    print(yes_and_no)
    yes_and_no.reset_index(drop=True, inplace=True)
    yes_and_no.to_csv('logs/pairs.csv')


if __name__ == '__main__':
    getTableOfAll()
