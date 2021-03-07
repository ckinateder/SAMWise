from datetime import *
from os import error, listdir, path
from pprint import pformat, pprint
from statistics import mean
from threading import Thread

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


class Hive:
    """
    Handles collecting and controlling the data.
    """

    def __init__(self, minnum=2):
        """
        minnum is the minimum number of exchanges that a symbol is on. this is only used to block a bouncer to be
        created. propagation is not affected by this.
        """
        self.pgator = propagator.Propagtor()
        with tqdm(
            total=5, position=1, leave=False, dynamic_ncols=True, desc="total"
        ) as init_bar:
            availables = self.pgator.getAvailableExchanges()
            init_bar.update(1)
            # create exchanges
            self.exchanges = self.pgator.loadExchanges(availables)
            init_bar.update(1)
            # create dynamics
            self.dynamic_commons = self.pgator.getDynamicCommons()
            init_bar.update(1)
            self.idynamics = self.pgator.getInvertedDynamicCommons(
                original=self.dynamic_commons
            )
            init_bar.update(1)
            self.currencies = self.createDynamicScanners(trade_size=100, minnum=minnum)
            init_bar.update(1)

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

    def createDynamicScanners(self, trade_size=100, minnum=2):
        """
        Create scanners for all the dynamic exchanges
        """
        self.currencies = []
        tqdm.write(
            colorEh(
                "{} ({} pairs found)".format(
                    stringitizeL(list(self.dynamic_commons.keys())),
                    len(self.dynamic_commons),
                )
            )
        )
        tqdm.write(colorGood(f"Creating {len(self.dynamic_commons)} scanners ..."))
        for e in tqdm(
            self.dynamic_commons,
            leave=False,
            unit="sym",
            dynamic_ncols=True,
            desc="symbl",
        ):
            if len(self.dynamic_commons[e]) >= minnum:
                self.currencies.append(
                    Scanner(
                        e,
                        trade_size,
                        self.dynamic_commons[e],
                        margin=0.01,
                        min_speedup=0.2,
                        speedup=72,
                        loud=False,
                        silent=True,
                        position=list(self.dynamic_commons.keys()).index(e)
                        / len(self.dynamic_commons)
                        * 100,
                    )
                )
        tqdm.write(
            colorGood(
                f"Created {len(self.dynamic_commons)} scanners!\nScanning now ..."
            )
        )
        return self.currencies

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

    def scanFull(self, props=None):
        """
        Scan every currency once and return as nested dict.
        """
        propagation_time = nowD()
        if not props:
            props, latest_batch = self.pgator.propagate(self.idynamics)
        propagation_time = nowD() - propagation_time
        responses = {}

        # multithreaded for speed
        procs = []
        solve_time = nowD()
        for scan in tqdm(
            self.currencies,
            leave=False,
            unit="sym",
            dynamic_ncols=True,
            desc="create",
        ):
            if scan.symbol in props:
                procs.append(
                    Thread(
                        target=scan.wrapGetSpreadToResults,
                        args=(responses, props[scan.symbol]),
                    )
                )
            else:
                tqdm.write(colorBad(f"Symbol {scan.symbol} not found in props!"))
                procs.append(
                    Thread(
                        target=scan.wrapGetSpreadToResults,
                        args=(responses),
                    )
                )
        # start
        for proc in tqdm(
            procs,
            leave=False,
            unit="sym",
            dynamic_ncols=True,
            desc="solve",
        ):
            proc.start()
        # join
        for proc in procs:
            proc.join()

        solve_time = nowD() - solve_time
        return responses

    def summarize(self, responses):
        """
        Summarize the scans for that cycle and pick a symbol to arbitrate.
        This will be some sort of rolling thing. This also should maybe be moved to analyze.py
        """
        pass

    def scanNTimes(self, n=1):
        """
        Scan every single exchange n times and print a summary.
        """
        # nested loop with progressbar
        total = len(self.currencies) * n
        with tqdm(
            total=total,
            position=1,
            leave=False,
            unit="sym",
            dynamic_ncols=True,
            desc="total",
        ) as total_bar:
            for cmt in range(n):
                start = nowD()
                self.scanFull()
                message = f"Completed cycle {cmt+1} of {n} ({((cmt+1)/n)*100:.0f}%) in {nowD()-start}"
                # notify
                tqdm.write(message)
                notify(message)
                # sleep cause you don't need all that data
                total_bar.update(1)
                timer(7)
        notify("Completed!")


if __name__ == "__main__":
    clear()
    intro()
    hive = Hive()

    # tableOfAll = hive.getTableOfAll()
    start_time = nowD()
    n = 100
    hive.scanNTimes(n=n)
    tqdm.write(f"Scanned all symbols {n} times in {(nowD()-start_time)}")
