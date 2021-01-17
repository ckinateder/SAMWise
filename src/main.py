import sys
import time
from getpass import getpass
from os import listdir, path

import ccxt

from bouncer import Bouncer

__author__ = 'Calvin Kinateder'
__email__ = 'calvinkinateder@gmail.com'


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
                print('Exchange {} added successfully!'.format(exchstr))
                exchanges.append(current)
                # only write if works
                with open(keypath+exchstr+'_public', 'w+') as pub:
                    pub.write(public)
                with open(keypath+exchstr+'_private', 'w+') as priv:
                    priv.write(private)
                if password_req:
                    with open(keypath+exchstr+'_password', 'w+') as passw:
                        passw.write(password)

                print('Saved keys to files')

            except ccxt.AuthenticationError:
                print('Invalid credentials for {} ... moving on.'.format(exchstr))

            more = input('Add another exchange? (Y/n): ')
            if 'y' in more.lower():
                moreToAdd = True
                print()
            else:
                moreToAdd = False
        else:
            print('Sorry, {} is not supported yet :('.format(exchstr))

    print('Done! Added exchanges {}.'.format(exchanges))
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
                print('Exchange {} added successfully!'.format(exchstr))
                exchanges.append(current)
            except ccxt.AuthenticationError:
                print('Invalid credentials for {} ... moving on.'.format(exchstr))
        else:
            print('Sorry, {} is not supported yet :('.format(exchstr))

    print('Done! Added exchanges {}.'.format(exchanges))
    return exchanges


if __name__ == '__main__':
    currencies = list()
    keypath = 'keys/'

    add = input('Would you like to add new exhanges? (Y/n): ')
    if 'y' in add.lower():
        exchanges = setupExchanges()
    else:
        exchanges = loadExchanges()

    if len(sys.argv) > 1:
        for i in range(1, len(sys.argv), 2):
            currencies.append(
                Bouncer(sys.argv[i], float(sys.argv[i+1]), exchanges))
    else:
        # default
        size = 15
        currencies = [Bouncer('BCH/USD', size, exchanges)]

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
