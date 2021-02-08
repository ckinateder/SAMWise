from bouncer import WIDTH, Bouncer
from scanner import Scanner
from helper import *
from os import listdir, path
import ccxt
import pandas as pd

__author__ = "Calvin Kinateder"
__email__ = "calvinkinateder@gmail.com"

QUOTE = "USD"


class Hive:
    def __init__(self):
        self.keypath = "keys/"

    def getTableOfAll(self):
        availables = self.getAvailableExchanges()
        # availables.remove('bittrex')
        exchanges = self.loadExchanges(availables)
        index = list()

        for i in exchanges:
            x = list(i.load_markets().keys())
            for j in x:
                if "USD" in j:
                    index.append(j)

        index = list(set(index))

        alls = list()
        for i in exchanges:
            alls.append(i.id)

        headers = alls
        headers.insert(0, "ticker")

        yes_and_no = pd.DataFrame(columns=headers)
        yes_and_no["ticker"] = index

        for exchange in exchanges:
            for i in range(0, len(index)):
                marks = list(exchange.load_markets().keys())
                if index[i] in marks:
                    yes_and_no[exchange.id][i] = True
                else:
                    yes_and_no[exchange.id][i] = False
        print(yes_and_no)
        yes_and_no.reset_index(drop=True, inplace=True)
        yes_and_no.to_csv("logs/pairs.csv")

    def loadExchanges(self, all_ex):
        """
        Create exchanges objects for all existing ones
        """
        print("Creating exchange objects for {}.".format(stringitizeL(all_ex)))
        exchanges = list()
        # create objs
        for exchstr in all_ex:
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
                                exchstr, self.keypath
                            )
                        )
                    )
            else:
                print(colorBad("Sorry, {} is not supported yet :(").format(exchstr))

        print(
            colorGood(
                "Done! Added exchanges {}.".format(self.stringitizeExc(exchanges))
            )
        )
        notify("Loaded exchanges {}".format(self.stringitizeExc(exchanges)))
        return exchanges

    def getCommons(self, exchanges):
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

    def getDynamicCommons(self, exchanges=None, minnum=3):
        """
        Get all symbols in common with 3 or more of the given exchanges.
        """
        if not exchanges:
            exchanges = self.loadExchanges(self.getAvailableExchanges())
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
        out = ""
        for i in range(len(l) - 1):
            out += l[i].name + ", "
        out += "and " + l[-1].name
        return out


if __name__ == "__main__":
    hive = Hive()
    hive.getTableOfAll()
