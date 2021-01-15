import sys
import time

from bouncer import Bouncer


__author__ = 'Calvin Kinateder'
__email__ = 'calvinkinateder@gmail.com'

if __name__ == '__main__':
    currencies = list()
    if len(sys.argv) > 1:
        for i in range(1, len(sys.argv), 2):
            currencies.append(Bouncer(sys.argv[i], float(sys.argv[i+1])))
    else:
        size = 15
        currencies = [Bouncer('BCH/USD', size)]

    while True:
        try:
            for i in currencies:
                i.arbitrate()
            time.sleep(3/len(sys.argv))
        except KeyboardInterrupt:
            print('\nQuitting\n')
            todo = input('Cleanup balances? (Y/n) ')
            if 'Y' in todo:
                for i in currencies:
                    i.cleanup()
            sys.exit(0)
