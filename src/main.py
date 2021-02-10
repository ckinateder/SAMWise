import re
import sys
import time
from getpass import getpass
from os import listdir, path
from pprint import pprint

import ccxt

try:
    from pynput import keyboard

    dynamic_input = True
except:
    dynamic_input = False
from bouncer import Bouncer
from scanner import Scanner
from helper import *

__author__ = "Calvin Kinateder"
__email__ = "calvinkinateder@gmail.com"


# initialize vars
KILL = False
currencies = list()
keypath = "keys/"
QUOTE = "USD"


def setupExchanges():
    """
    Sets up all exchanges from the CLI (for first time use).
    """
    exchanges = list()
    moreToAdd = True
    while moreToAdd:
        exchstr = input("Enter name of exchange to add: ")
        if exchstr in ccxt.exchanges:
            public = input("Paste public key: ").strip()
            private = getpass("Paste private key: ").strip()
            password_req_str = input(
                "Does {} require a password? (Y/n): ".format(exchstr)
            )

            if "y" in password_req_str.lower():
                password_req = True
            else:
                password_req = False

            password_req_str = input("Does {} require a uid? (Y/n): ".format(exchstr))

            if "y" in password_req_str.lower():
                uid_req = True
            else:
                uid_req = False

            exchange_class = getattr(ccxt, exchstr)

            if password_req and uid_req:
                uid = input("Enter uid for {}: ".format(exchstr)).strip()
                password = getpass("Enter password for {}: ".format(exchstr)).strip()

                current = exchange_class(
                    {
                        "apiKey": public,
                        "secret": private,
                        "password": password,
                        "uid": uid,
                    }
                )
            elif password_req:
                password = getpass("Enter password for {}: ".format(exchstr)).strip()

                current = exchange_class(
                    {
                        "apiKey": public,
                        "secret": private,
                        "password": password,
                    }
                )
            elif uid_req:
                uid = input("Enter uid for {}: ".format(exchstr)).strip()

                current = exchange_class(
                    {
                        "apiKey": public,
                        "secret": private,
                        "uid": uid,
                    }
                )
            else:
                current = exchange_class(
                    {
                        "apiKey": public,
                        "secret": private,
                    }
                )

            try:
                current.fetch_balance()
                print(colorGood("Exchange {} added successfully :)").format(exchstr))
                exchanges.append(current)
                # only write if works
                with open(keypath + exchstr + "_public", "w+") as pub:
                    pub.write(public)
                with open(keypath + exchstr + "_private", "w+") as priv:
                    priv.write(private)
                if password_req:
                    with open(keypath + exchstr + "_password", "w+") as passw:
                        passw.write(password)
                if uid_req:
                    with open(keypath + exchstr + "_uid", "w+") as uidw:
                        uidw.write(uid)
                print(colorGood("Saved keys to files"))

            except ccxt.AuthenticationError as e:
                print(
                    colorBad("Invalid credentials for {} ... moving on. ({})").format(
                        exchstr, e
                    )
                )

            more = input("Add another exchange? (Y/n): ")
            if "y" in more.lower():
                moreToAdd = True
                print()
            else:
                moreToAdd = False
        else:
            print(colorBad("Sorry, {} is not supported yet :(").format(exchstr))

    print(colorGood("Done! Added exchanges {}.".format(stringitizeExc(exchanges))))
    return exchanges


def getAvailableExchanges():
    """
    Get all existing exchanges
    """
    # find exchanges from file structure
    file_list = listdir(keypath)
    end = len(file_list) - 1
    for i in range(0, end):
        x = file_list[i]
        # print(x)
        if ".DS_Store" in x or ".gitkeep" in x:
            file_list.remove(x)
        end = len(file_list)
    for i in range(0, len(file_list)):
        x = file_list[i]
        if "_public" in x:
            file_list[i] = x.replace("_public", "")
        elif "_private" in x:
            file_list[i] = x.replace("_private", "")
        elif "_password" in x:
            file_list[i] = x.replace("_password", "")
        elif "_uid" in x:
            file_list[i] = x.replace("_uid", "")
    all_ex = list(set(file_list))
    return all_ex


def loadExchanges(all_ex):
    """
    Create exchanges objects for all existing ones
    """
    print("Creating exchange objects for {}.".format(stringitizeL(all_ex)))
    exchanges = list()
    # create objs
    for exchstr in all_ex:
        if exchstr in ccxt.exchanges:  # j to be safe
            try:
                public = open(keypath + exchstr + "_public").read().strip()
                private = open(keypath + exchstr + "_private").read().strip()

                exchange_class = getattr(ccxt, exchstr)

                if path.exists(keypath + exchstr + "_password") and path.exists(
                    keypath + exchstr + "_uid"
                ):
                    password = open(keypath + exchstr + "_password").read().strip()
                    uid = open(keypath + exchstr + "_uid").read().strip()

                    current = exchange_class(
                        {
                            "apiKey": public,
                            "secret": private,
                            "password": password,
                            "uid": uid,
                        }
                    )
                elif path.exists(keypath + exchstr + "_uid"):
                    uid = open(keypath + exchstr + "_uid").read().strip()

                    current = exchange_class(
                        {
                            "apiKey": public,
                            "secret": private,
                            "uid": uid,
                        }
                    )
                elif path.exists(keypath + exchstr + "_password"):
                    password = open(keypath + exchstr + "_password").read().strip()

                    current = exchange_class(
                        {
                            "apiKey": public,
                            "secret": private,
                            "password": password,
                        }
                    )
                else:
                    current = exchange_class(
                        {
                            "apiKey": public,
                            "secret": private,
                        }
                    )
                current.fetch_balance()
                print(colorGood("Exchange {} added successfully!").format(exchstr))
                exchanges.append(current)
            except ccxt.AuthenticationError:
                print(
                    colorBad("Invalid credentials for {} ... moving on.").format(
                        exchstr
                    )
                )
            except FileNotFoundError:
                print(
                    colorBad(
                        "Keys for {} not found in {} ... moving on.".format(
                            exchstr, keypath
                        )
                    )
                )
        else:
            print(colorBad("Sorry, {} is not supported yet :(").format(exchstr))

    print(colorGood("Done! Added exchanges {}.".format(stringitizeExc(exchanges))))
    notify("Loaded exchanges {}".format(stringitizeExc(exchanges)))
    return exchanges


def getCommons(exchanges):
    """
    Get all symbols in common with EVERY given exchange.
    """
    alls = list()
    for i in exchanges:
        x = list(i.load_markets().keys())
        for j in x:
            alls.append(j)
    out = list()

    for item in alls:
        # Important - only allows usd
        # and not 'XRP' in item:
        if alls.count(item) == len(exchanges) and QUOTE in item:
            out.append(item)
    out = list(set(out))
    return out


def getDynamicCommons(exchanges, minnum=3):
    """
    Get all symbols in common with 3 or more of the given exchanges.
    """
    alls = list()
    for i in exchanges:
        x = list(i.load_markets().keys())
        for j in x:
            # if QUOTE in j:  # or 'BTC' in j or 'ETH' in j:
            alls.append(j)
    alls = list(set(alls))

    compatibles = {}
    for exchange in exchanges:
        possibles = list(exchange.load_markets().keys())
        for symbol in alls:
            if symbol in possibles:
                if symbol in compatibles:
                    compatibles[symbol].append(exchange)
                else:  # initialize
                    compatibles[symbol] = [exchange]

    multiples = {}
    for key in compatibles:
        if len(compatibles[key]) >= minnum:
            multiples[key] = compatibles[key]
    return multiples


def on_release(key):
    """
    Key release handler
    """
    if hasattr(key, "char"):
        if key.char == "q":
            globals()["KILL"] = True


def kill():
    """
    kill the program
    """
    print("\nQuitting\n")
    notify("Quitting")
    should = input("Are you sure you want to quit? (Y/n) ")
    if "y" in should.lower():
        if globals()["trading"]:
            todo = input("Cleanup balances? (Y/n) ")
            if "y" in todo.lower():
                for i in currencies:
                    i.cleanup()
        sys.exit(0)
    notify("Resuming")
    globals()["KILL"] = False


def configure():
    """
    Configure options for starting the program.
    """
    start_time = now()
    inip = False
    globals()["trading"] = True
    # check for commandline override
    if len(sys.argv) > 1:
        exchanges = loadExchanges(getAvailableExchanges())
        if sys.argv[1] == "test_usd":
            dynamics = getDynamicCommons(exchanges)
            print(
                colorEh(
                    "Creating for: {} ({} pairs)".format(
                        stringitizeL(list(dynamics.keys())), len(dynamics)
                    )
                )
            )
            for e in dynamics:
                currencies.append(
                    Scanner(
                        e,
                        float(sys.argv[2]),
                        dynamics[e],
                        margin=0.01,
                        min_speedup=0.2,
                        speedup=72,
                        loud=False,
                        position=list(dynamics.keys()).index(e) / len(dynamics) * 100,
                    )
                )
        else:
            for i in range(1, len(sys.argv), 2):
                currencies.append(
                    Bouncer(
                        sys.argv[i],
                        float(sys.argv[i + 1]),
                        exchanges,
                        margin=0.01,
                        min_speedup=0.1,
                    )
                )
    else:
        add = input(("Would you like to add new exhanges? (Y/n): "))
        if "y" in add.lower():
            exchanges = setupExchanges()
        # get availables
        availables = getAvailableExchanges()

        available_str = "\n"
        for i in range(0, len(availables)):
            available_str += "\t{}: {}\n".format(i, availables[i])
        whichones = input(
            "Which exchanges would you like to run on? (enter a comma separated list or 'all') {{available: {}}}: ".format(
                availables
            )
        )
        if "all" in whichones:
            actuals = availables
        elif whichones == "":
            actuals = ["binanceus", "coinbasepro", "bittrex", "kraken"]
        else:
            actuals = [
                re.sub("[\W_]+", "", x) for x in whichones.split(",")
            ]  # remove whitespace
        # create exchanges
        exchanges = loadExchanges(actuals)

        # check for scanning
        scan = input(("Would you like to run in scanner mode? (Y/n): "))
        commons = getCommons(exchanges)

        curr = "list"
        while "list" in curr.lower():
            curr = input(
                (
                    "Which crypto ticker would you like to run on?\n  ('list' for available tickers or 'all' to run on each): "
                )
            ).upper()
            if "list" in curr.lower():
                print(colorEh(stringitizeL(commons)))
            elif curr == "":
                curr = "all"

        if "y" in scan.lower():
            globals()["trading"] = False
        else:
            # check for initialization
            ini = input(
                ("Would you like to initalize the exchanges with crypto? (Y/n): ")
            )
            if "y" in ini.lower():
                inip = True
            else:
                inip = False

        invest = ""
        while type(invest) == str:
            invest = input(
                ("How much would you like each transaction to be worth in dollars?")
                + " $"
            )
            try:
                invest = float(invest)
            except:
                if invest == "":
                    invest = 100  # default
                else:
                    print(colorBad("Enter a number."))

        margin = ""
        while type(margin) == str:
            margin = input(("Minimum profit margin? ") + " $")
            try:
                margin = float(margin)
            except:
                if margin == "":
                    margin = 0.01  # default
                else:
                    print(colorBad("Enter a number."))

        speedup = ""
        while type(speedup) == str:
            speedup = input("Max speedup? (0 to 100%) ")
            try:
                speedup = float(speedup)
            except:
                if speedup == "":
                    speedup = 10  # default
                else:
                    print(colorBad("Enter a number."))

        min_speedup = ""
        while type(min_speedup) == str:
            if speedup > 0:
                min_speedup = input("Min speedup? (0 to {}%) ".format(speedup))
                try:
                    min_speedup = float(min_speedup)
                except:
                    if min_speedup == "":
                        min_speedup = 0  # default
                    else:
                        print(colorBad("Enter a number."))

        if "all" in curr.lower():
            dynamics = getDynamicCommons(exchanges)
            print(
                colorEh(
                    "Creating for: {} ({} pairs)".format(
                        list(dynamics.keys()), len(dynamics)
                    )
                )
            )
            if globals()["trading"]:
                for sym in dynamics:
                    currencies.append(
                        Bouncer(
                            sym,
                            invest,
                            dynamics[sym],
                            inip,
                            speedup,
                            margin,
                            min_speedup,
                        )
                    )
            else:
                for sym in dynamics:
                    currencies.append(
                        Scanner(
                            sym,
                            invest,
                            dynamics[sym],
                            inip,
                            speedup,
                            margin,
                            min_speedup,
                        )
                    )
        else:
            if globals()["trading"]:
                currencies.append(
                    Bouncer(
                        curr,
                        invest,
                        exchanges,
                        inip,
                        speedup,
                        margin,
                        min_speedup,
                    )
                )
            else:
                currencies.append(
                    Scanner(
                        curr,
                        invest,
                        exchanges,
                        inip,
                        speedup,
                        margin,
                        min_speedup,
                    )
                )
    end_time = now() - start_time
    notify("Configured in {:.2f} s".format(end_time))


# run main
if __name__ == "__main__":
    # welcome
    print()
    print("Welcome to SAMWise!".center(WIDTH))
    print("(Spatial Arbitrage Method Wizard)".center(WIDTH))
    print("Created by Calvin Kinateder, 2021".center(WIDTH))
    print(
        "calvinkinateder@gmail.com, https://ckinateder.github.io/SAMWise/".center(WIDTH)
    )
    if dynamic_input:
        print(
            "Press 'q' or ESC to quit. Note: '$' is used to symbolize quote coin.".center(
                WIDTH
            )
        )
    else:
        print(
            "CTRL C to quit. Note: '$' is used to symbolize quote coin.".center(WIDTH)
        )
    print(("-" * WIDTH) + "\n")

    # attach key listener
    # ...or, in a non-blocking fashion:
    if dynamic_input:
        listener = keyboard.Listener(on_release=on_release)
        listener.start()

    configure()

    while True:
        try:
            for i in currencies:
                if type(i) == Bouncer:
                    i.arbitrate()
                elif type(i) == Scanner:
                    i.getSpread()
                if KILL:
                    kill()
            time.sleep(3 / len(currencies))
        except KeyboardInterrupt:
            kill()
