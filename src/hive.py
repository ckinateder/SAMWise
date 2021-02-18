from datetime import *
from os import error, listdir, path
from pprint import pprint
from typing import final

import ccxt
import pandas as pd
from tqdm import tqdm
from tqdm.std import trange

import propagator
from bouncer import Bouncer
from helper import *
from scanner import Scanner

__author__ = "Calvin Kinateder"
__email__ = "calvinkinateder@gmail.com"

QUOTE = "USD"


class Hive:
    """"""

    def __init__(self):
        self.keypath = "keys/"
        with tqdm(
            total=3, position=1, leave=False, dynamic_ncols=True, desc="total"
        ) as init_bar:
            availables = self.getAvailableExchanges()
            init_bar.update(1)
            # availables.remove('bittrex')
            self.exchanges = self.loadExchanges(availables)
            init_bar.update(1)
            self.dynamics = self.getDynamicCommons()
            init_bar.update(1)

    def updateDynamics(self):
        self.dynamics = self.getDynamicCommons()

    def getTableOfAll(self):
        """
        Get table of all symbols mapped with all exchanges.
        """
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
        headers.append("count")

        yes_and_no = pd.DataFrame(columns=headers)
        yes_and_no["ticker"] = index
        yes_and_no["count"] = 0

        for exchange in self.exchanges:
            for i in range(0, len(index)):
                marks = list(exchange.load_markets().keys())
                if index[i] in marks:
                    yes_and_no[exchange.id].loc[i] = True
                    yes_and_no["count"].loc[i] += 1
                else:
                    yes_and_no[exchange.id].loc[i] = False
        # tqdm.write(yes_and_no)
        yes_and_no.reset_index(drop=True, inplace=True)
        yes_and_no = yes_and_no.sort_values("count", ascending=False)
        yes_and_no.to_csv("logs/pairs.csv", index=False)
        return yes_and_no

    def loadExchanges(self, all_ex):
        """
        Create self.exchanges objects for all existing ones
        """

        self.exchanges = list()
        tqdm.write("Creating exchange objects for {} ...".format(stringitizeL(all_ex)))
        verified = []
        if path.exists(self.keypath + "verified"):
            with open(self.keypath + "verified", "r") as verified_f:
                verified = [i.strip() for i in verified_f.readlines()]
                tqdm.write(
                    colorGood(
                        f"Verified exchanges {stringitizeL(verified)}; skipping validation on these."
                    )
                )
        else:
            tqdm.write(colorBad("No verified keys."))
        # create objs
        for exchstr in tqdm(
            all_ex, leave=False, dynamic_ncols=True, unit="exc", desc="xchng"
        ):
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
                    # if not verified
                    if not exchstr in verified:
                        current.fetch_balance()
                        # save to file
                        with open(self.keypath + "verified", "a+") as verified_f:
                            verified_f.write(exchstr + "\n")

                    # tqdm.write(
                    #    colorGood("Exchange {} added successfully!").format(exchstr)
                    # )
                    self.exchanges.append(current)
                except ccxt.AuthenticationError:
                    tqdm.write(
                        colorBad("Invalid credentials for {} ... moving on.").format(
                            exchstr
                        )
                    )
                except FileNotFoundError:
                    tqdm.write(
                        colorBad(
                            "Keys for {} not found in {} ... moving on.".format(
                                exchstr, self.keypath
                            )
                        )
                    )
            else:
                tqdm.write(
                    colorBad("Sorry, {} is not supported yet :(").format(exchstr)
                )

        tqdm.write(
            colorGood(
                "Done! Added exchanges {}.".format(self.stringitizeExc(self.exchanges))
            )
        )
        notify("Loaded {}".format(self.stringitizeExc(self.exchanges)))
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
        Get all symbols in common with minnum or more of the given self.exchanges.
        """
        tqdm.write("Getting shared symbols ...")
        alls = list()
        for i in tqdm(
            self.exchanges, unit="exc", leave=False, dynamic_ncols=True, desc="xchng"
        ):
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

    def getInvertedDynamicCommons(self, original=None, minnum=3):
        """
        Get all symbols in common with 3 or more of the given self.exchanges.
        """
        if not self.exchanges:
            self.exchanges = self.loadExchanges(self.getAvailableExchanges())
        if not original:
            original = self.getDynamicCommons(minnum)

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

        for i in trange(0, len(file_list), unit="exc", leave=False, dynamic_ncols=True):
            x = file_list[i]
            if "_public" in x:
                file_list[i] = x.replace("_public", "")
            elif "_private" in x:
                file_list[i] = x.replace("_private", "")
            elif "_password" in x:
                file_list[i] = x.replace("_password", "")
            elif "_uid" in x:
                file_list[i] = x.replace("_uid", "")
            else:
                file_list[i] = "bad"
        if "bad" in file_list:
            file_list = [x for x in file_list if not x == "bad"]
        all_ex = list(set(file_list))
        return all_ex

    def stringitizeExc(self, l):
        """
        tqdm.write out the exchanges nicely
        """
        out = ""
        for i in range(len(l) - 1):
            out += l[i].name + ", "
        out += "and " + l[-1].name
        return out

    def createDynamicScanners(self, trade_size=100):
        """
        Create scanners for all the dynamic exchanges
        """
        currencies = []
        tqdm.write(
            colorEh(
                "{} ({} pairs found)".format(
                    stringitizeL(list(self.dynamics.keys())), len(self.dynamics)
                )
            )
        )
        tqdm.write(colorGood(f"Creating {len(self.dynamics)} scanners ..."))
        for e in tqdm(
            self.dynamics, leave=False, unit="sym", dynamic_ncols=True, desc="symbl"
        ):
            currencies.append(
                Scanner(
                    e,
                    trade_size,
                    self.dynamics[e],
                    margin=0.01,
                    min_speedup=0.2,
                    speedup=72,
                    loud=False,
                    position=list(self.dynamics.keys()).index(e)
                    / len(self.dynamics)
                    * 100,
                )
            )
        tqdm.write(
            colorGood(f"Created {len(self.dynamics)} scanners!\nScanning now ...")
        )
        return currencies

    def myPrint(self, dic):
        for x in dic:
            tqdm.write(f"'{x}': ", end="")
            for exc in dic[x]:
                tqdm.write(f"{exc}: " + "{ ... }")

    def verify(self, test, sure):
        """
        Verify if test recieved as many responses as sure
        """
        verified = True
        for sym in sure:
            if sym in sure and sym in test:
                if not set(sure[sym]) == set(test[sym].keys()):
                    verified = False
            else:
                verified = False
        return verified

    def scanAll(self, trade_size, n=1, beta=True):
        """
        Scan every single exchange n times and print a summary. Set 'beta' to False to run the stable mode.
        """
        currencies = self.createDynamicScanners(trade_size=trade_size)
        idynamics = self.getInvertedDynamicCommons(original=self.dynamics)
        # nested loop with progressbar
        total = len(currencies) * n
        with tqdm(
            total=total,
            position=1,
            leave=False,
            unit="sym",
            dynamic_ncols=True,
            desc="total",
        ) as total_bar:
            for cmt in range(n):
                if beta:
                    pgator = propagator.Propagtor()
                    start_time = datetime.now()
                    props = pgator.propagate(idynamics)
                    endtime = datetime.now() - start_time
                # pprint(props)
                responses = {}
                for scan in tqdm(
                    currencies,
                    leave=False,
                    unit="sym",
                    dynamic_ncols=True,
                    desc="cycle",
                ):
                    if beta:
                        if scan.symbol in props:
                            spreads, error, ff = scan.getSpread(props[scan.symbol])
                        else:
                            spreads, error, ff = scan.getSpread()
                    else:
                        spreads, error, ff = scan.getSpread()
                    responses[scan] = {"flip_flop": ff, "error": error}
                    total_bar.update(1)
                # tqdm.write summary
                tqdm.write(f"Summary of cycle {cmt+1} in {endtime}:")
                flops = []
                errors = []
                for i in responses:
                    if responses[i]["flip_flop"]:
                        flops.append(str(i))
                    if responses[i]["error"]:
                        errors.append(str(i))
                tqdm.write(colorGood(f"Flip flops: {stringitizeL(flops)}"))
                if errors:
                    tqdm.write(colorBad(f"Errors: {stringitizeL(errors)}"))
                notify(
                    f"Completed cycle {cmt+1} of {n} ({((cmt+1)/n)*100:.0f}%) in {endtime}"
                )
                # sleep cause you don't need all that data
                time.sleep(9)
        notify("Completed!")


if __name__ == "__main__":
    clear()
    intro()
    hive = Hive()

    # tableOfAll = hive.getTableOfAll()
    start_time = datetime.now()
    n = 10
    hive.scanAll(trade_size=100, n=n, beta=True)
    tqdm.write(f"Scanned all symbols {n} times in {(datetime.now()-start_time)}")
