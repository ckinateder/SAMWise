from datetime import *
from os import error, listdir, path
from pprint import pprint

import ccxt
import pandas as pd
import progressbar

from bouncer import WIDTH, Bouncer
from helper import *
from scanner import Scanner

__author__ = "Calvin Kinateder"
__email__ = "calvinkinateder@gmail.com"

QUOTE = "USD"


class Hive:
    def __init__(self):
        self.keypath = "keys/"
        availables = self.getAvailableExchanges()
        # availables.remove('bittrex')
        self.exchanges = self.loadExchanges(availables)

    def getTableOfAll(self):
        index = list()

        for i in self.exchanges:
            x = list(i.load_markets().keys())
            for j in x:
                if "USD" in j:
                    index.append(j)

        index = list(set(index))

        alls = list()
        for i in self.exchanges:
            alls.append(i.id)

        headers = alls
        headers.insert(0, "ticker")

        yes_and_no = pd.DataFrame(columns=headers)
        yes_and_no["ticker"] = index

        for exchange in self.exchanges:
            for i in range(0, len(index)):
                marks = list(exchange.load_markets().keys())
                if index[i] in marks:
                    yes_and_no[exchange.id][i] = True
                else:
                    yes_and_no[exchange.id][i] = False
        # print(yes_and_no)
        yes_and_no.reset_index(drop=True, inplace=True)
        yes_and_no.to_csv("logs/pairs.csv")
        return yes_and_no

    def loadExchanges(self, all_ex):
        """
        Create self.exchanges objects for all existing ones
        """
        print("Creating exchange objects for {} ...".format(stringitizeL(all_ex)))
        self.exchanges = list()
        # create objs
        for exchstr in progressbar.progressbar(all_ex, redirect_stdout=True):
            if exchstr in ccxt.exchanges:  # j to be safe
                try:
                    public = open(self.keypath + exchstr + "_public").read().strip()
                    private = open(self.keypath + exchstr + "_private").read().strip()

                    exchange_class = getattr(ccxt, exchstr)

                    if path.exists(
                        self.keypath + exchstr + "_password"
                    ) and path.exists(self.keypath + exchstr + "_uid"):
                        password = (
                            open(self.keypath + exchstr + "_password").read().strip()
                        )
                        uid = open(self.keypath + exchstr + "_uid").read().strip()

                        current = exchange_class(
                            {
                                "apiKey": public,
                                "secret": private,
                                "password": password,
                                "uid": uid,
                            }
                        )
                    elif path.exists(self.keypath + exchstr + "_uid"):
                        uid = open(self.keypath + exchstr + "_uid").read().strip()

                        current = exchange_class(
                            {
                                "apiKey": public,
                                "secret": private,
                                "uid": uid,
                            }
                        )
                    elif path.exists(self.keypath + exchstr + "_password"):
                        password = (
                            open(self.keypath + exchstr + "_password").read().strip()
                        )

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
                    self.exchanges.append(current)
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
                                exchstr, self.keypath
                            )
                        )
                    )
            else:
                print(colorBad("Sorry, {} is not supported yet :(").format(exchstr))

        print(
            colorGood(
                "Done! Added self.exchanges {}.".format(
                    self.stringitizeExc(self.exchanges)
                )
            )
        )
        notify("Loaded self.exchanges {}".format(self.stringitizeExc(self.exchanges)))
        return self.exchanges

    def getCommons(self):
        """
        Get all symbols in common with EVERY given exchange.
        """
        alls = list()
        for i in self.exchanges:
            x = list(i.load_markets().keys())
            for j in x:
                alls.append(j)
        out = list()

        for item in alls:
            # Important - only allows usd
            # and not 'XRP' in item:
            if alls.count(item) == len(self.exchanges) and QUOTE in item:
                out.append(item)
        out = list(set(out))
        return out

    def getDynamicCommons(self, minnum=3):
        """
        Get all symbols in common with 3 or more of the given self.exchanges.
        """
        alls = list()
        for i in self.exchanges:
            x = list(i.load_markets().keys())
            for j in x:
                if (
                    QUOTE in j
                    or "BTC" in j
                    or "ETH" in j
                    and not ("GBP" in j or not "EUR" in j)
                ):
                    alls.append(j)
        alls = list(set(alls))

        compatibles = {}
        for exchange in self.exchanges:
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

    def getInvertedDynamicCommons(self, minnum=3):
        """
        Get all symbols in common with 3 or more of the given self.exchanges.
        """
        if not self.exchanges:
            self.exchanges = self.loadExchanges(self.getAvailableExchanges())
        original = self.getDynamicCommons(minnum)

        return self.transpose(original)

    def transpose(self, original):
        """
        Flip a dictionary of dictionaries
        """
        inverted = {}
        for symbol in original:
            for exchange in self.exchanges:
                if exchange in original[symbol]:
                    if exchange in inverted:
                        inverted[exchange].append(symbol)
                    else:
                        inverted[exchange] = [symbol]

        return inverted

    def getAvailableExchanges(self):
        """
        Get all existing exchanges
        """
        # find exchanges from file structure
        file_list = listdir(self.keypath)
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

    def stringitizeExc(self, l):
        """
        Print out the exchanges nicely
        """
        out = ""
        for i in range(len(l) - 1):
            out += l[i].name + ", "
        out += "and " + l[-1].name
        return out

    def createDynamicScanners(self, trade_size=100, dynamics=None):
        """
        Create scanners for all the dynamic exchanges
        """
        currencies = []
        if not dynamics:
            dynamics = self.getDynamicCommons()
        print(
            colorEh(
                "{} ({} pairs found)".format(
                    stringitizeL(list(dynamics.keys())), len(dynamics)
                )
            )
        )
        print(colorGood(f"Creating {len(dynamics)} scanners ..."))
        for e in progressbar.progressbar(dynamics, redirect_stdout=True):
            currencies.append(
                Scanner(
                    e,
                    trade_size,
                    dynamics[e],
                    margin=0.01,
                    min_speedup=0.2,
                    speedup=72,
                    loud=False,
                    position=list(dynamics.keys()).index(e) / len(dynamics) * 100,
                )
            )
        print(colorGood(f"Created {len(dynamics)} scanners!\nScanning now ..."))
        return currencies

    def scanAll(self, trade_size, n=1):
        """
        Scan every single exchange n times and print a summary.
        """
        currencies = self.createDynamicScanners(trade_size=trade_size)

        for cmt in range(n):
            responses = {}
            for scan in progressbar.progressbar(currencies, redirect_stdout=True):
                spreads, error, ff = scan.getSpread()
                responses[scan] = ff
            for i in responses:
                if responses[i]:
                    print(colorGood(str(i) + ": " + str(responses[i])))
                else:
                    print(colorEh(str(i) + ": " + str(responses[i])))


if __name__ == "__main__":
    hive = Hive()
    start_time = datetime.now()
    hive.scanAll(trade_size=100, n=80)
    print(f"Scanned all symbols in {(datetime.now()-start_time)}")
    tableOfAll = hive.getTableOfAll()
