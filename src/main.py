import sys
import time
from getpass import getpass
from os import listdir, path

import ccxt
try:
    from pynput import keyboard
    dynamic_input = True
except:
    dynamic_input = False
from bouncer import Bouncer
from crayon import *

__author__ = 'Calvin Kinateder'
__email__ = 'calvinkinateder@gmail.com'


# initialize vars
KILL = False
currencies = list()
keypath = 'keys/'
active = True


def setupExchanges():
    '''
    Sets up all exchanges from the CLI. (for first time)
    '''
    exchanges = list()
    moreToAdd = True
    while moreToAdd:
        exchstr = input('Enter name of exchange to add: ')
        if exchstr in ccxt.exchanges:
            public = input('Paste public key: ').strip()
            private = getpass('Paste private key: ').strip()
            password_req_str = input(
                'Does {} require a password? (Y/n): '.format(exchstr))
            print(public)
            print(private)

            if 'y' in password_req_str.lower():
                password_req = True
            else:
                password_req = False

            exchange_class = getattr(ccxt, exchstr)

            if password_req:
                password = getpass(
                    'Enter password for {}: '.format(exchstr)).strip()

                current = exchange_class({
                    'apiKey': public,
                    'secret': private,
                    'password': password,
                })
            else:
                current = exchange_class({
                    'apiKey': public,
                    'secret': private,
                })

            try:
                current.fetch_balance()
                print(colorGood('Exchange {} added successfully!').format(exchstr))
                exchanges.append(current)
                # only write if works
                with open(keypath+exchstr+'_public', 'w+') as pub:
                    pub.write(public)
                with open(keypath+exchstr+'_private', 'w+') as priv:
                    priv.write(private)
                if password_req:
                    with open(keypath+exchstr+'_password', 'w+') as passw:
                        passw.write(password)

                print(colorGood('Saved keys to files'))

            except ccxt.AuthenticationError:
                print(
                    colorBad('Invalid credentials for {} ... moving on.').format(exchstr))

            more = input('Add another exchange? (Y/n): ')
            if 'y' in more.lower():
                moreToAdd = True
                print()
            else:
                moreToAdd = False
        else:
            print(colorBad('Sorry, {} is not supported yet :(').format(exchstr))

    print(colorGood('Done! Added exchanges {}.').format(exchanges))
    return exchanges


def loadExchanges():
    '''
    Create exchanges for all existing ones
    '''
    exchanges = list()
    # find exchanges from file structure
    file_list = listdir(keypath)
    for i in range(0, len(file_list)-2):
        x = file_list[i]
        if '.DS_Store' in x or 'gitkeep' in x:
            file_list.remove(x)
    for i in range(0, len(file_list)):
        x = file_list[i]
        if '_public' in x:
            file_list[i] = x.replace('_public', '')
        elif '_private' in x:
            file_list[i] = x.replace('_private', '')
        elif '_password' in x:
            file_list[i] = x.replace('_password', '')
    all_ex = list(set(file_list))

    print('Creating exchange objects for {}.'.format(all_ex))

    # create objs
    for exchstr in all_ex:
        if exchstr in ccxt.exchanges:  # j to be safe
            public = open(keypath+exchstr+'_public').read().strip()
            private = open(keypath+exchstr+'_private').read().strip()

            exchange_class = getattr(ccxt, exchstr)

            if path.exists(keypath+exchstr+'_password'):
                password = open(keypath+exchstr +
                                '_password').read().strip()

                current = exchange_class({
                    'apiKey': public,
                    'secret': private,
                    'password': password,
                })
            else:
                current = exchange_class({
                    'apiKey': public,
                    'secret': private,
                })
            try:
                current.fetch_balance()
                print(colorGood('Exchange {} added successfully!').format(exchstr))
                exchanges.append(current)
            except ccxt.AuthenticationError:
                print(
                    colorBad('Invalid credentials for {} ... moving on.').format(exchstr))
        else:
            print(colorBad('Sorry, {} is not supported yet :(').format(exchstr))

    print(colorGood('Done! Added exchanges {}.').format(exchanges))
    return exchanges


def getCommons(exchanges):
    alls = list()
    for i in exchanges:
        x = list(i.load_markets().keys())
        for j in x:
            alls.append(j)
    out = list()

    for item in alls:
        if alls.count(item) == 4 and 'USD' in item:  # Important - only allows usd
            out.append(item)
    out = list(set(out))
    return out


def on_press(key):
    try:
        pass
        # print('alphanumeric key {0} pressed'.format(
        #    key.char))
    except AttributeError:
        pass
        # print('special key {0} pressed'.format(
        #   key))


def on_release(key):
    # print('{0} released'.format(
    # key))
    if hasattr(key, 'char'):
        if key.char == 'q':
            globals()['KILL'] = True

    if key == keyboard.Key.esc:
        globals()['KILL'] = True


def kill():
    print('\nQuitting\n')
    if active:
        todo = input('Cleanup balances? (Y/n) ')
        if 'Y' in todo:
            for i in currencies:
                i.cleanup()
    sys.exit(0)


def configure():
    # check for adding exchanges
    inip = False
    log = True
    active = True
    add = input(('Would you like to add new exhanges? (Y/n): '))
    if 'y' in add.lower():
        exchanges = setupExchanges()
    else:
        exchanges = loadExchanges()

    # check for scanning
    scan = input(
        ('Would you like to run in scanner mode? (Y/n): '))
    if 'y' in scan.lower():
        active = False
        login = input('Would you like to disable logging to file? (Y/n): ')
        if 'y' in login.lower():
            log = False
    else:
        # check for initialization
        ini = input(
            ('Would you like to initalize the exchanges with crypto? (Y/n): '))
        if 'y' in ini.lower():
            inip = True
        else:
            inip = False

    # check for commandline override
    if len(sys.argv) > 1:
        for i in range(1, len(sys.argv), 2):
            currencies.append(
                Bouncer(sys.argv[i], float(sys.argv[i+1]), exchanges, inip, active, log))
    else:
        commons = getCommons(exchanges)
        curr = 'list'
        while 'list' in curr.lower():
            curr = input((
                'Which crypto ticker would you like to run on?\n  (\'list\' for available tickers or \'all\' to run on each): '))
            if 'list' in curr.lower():
                print(colorEh(commons))

        invest = ''
        if active:
            while type(invest) == str:
                invest = float(input((
                    'How much would you like each transaction to be worth in dollars?')+' $'))
        else:
            invest = 100

        if 'all' in curr.lower():
            for sym in commons:
                currencies.append(
                    Bouncer(sym, invest, exchanges, inip, active, log))
        else:
            currencies.append(
                Bouncer(curr, invest, exchanges, inip, active, log))


# run main
if __name__ == '__main__':
    WIDTH = 80  # of console
    # welcome
    print()
    print('Welcome to SAMWise!'.center(WIDTH))
    print('(Spatial Arbitrage Method Wizard)'.center(WIDTH))
    print('Created by Calvin Kinateder, 2021'.center(WIDTH))
    print('calvinkinateder@gmail.com, https://ckinateder.github.io/SAMWise/'.center(WIDTH))
    if dynamic_input:
        print('Press \'q\' or ESC to quit.'.center(WIDTH))
    else:
        print('CTRL C to quit.'.center(WIDTH))
    print(('-'*80)+'\n')

    # attach key listener
    # ...or, in a non-blocking fashion:
    if dynamic_input:
        listener = keyboard.Listener(
            on_press=on_press,
            on_release=on_release)
        listener.start()

    configure()

    while True:
        try:
            for i in currencies:
                i.arbitrate()
                if KILL:
                    kill()
            time.sleep(3/len(currencies))
        except KeyboardInterrupt:
            kill()
