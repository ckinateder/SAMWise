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
        self.idynamics = {}

        with tqdm(
            total=5,
            disable=BARSDISABLED,
            position=1,
            leave=False,
            dynamic_ncols=True,
            desc="total",
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
            self.scanners = self.createDynamicSB(Scanner, trade_size=100, minnum=minnum)
            self.bouncers = []
            # self.bouncers = self.createDynamicSB(Bouncer, trade_size=100, minnum=minnum)
            init_bar.update(1)
        self.supported_idynamics = self.idynamics.copy()
        self.supported_dynamics = self.dynamic_commons.copy()

    def sliceFromIdynamics(self, names):
        """
        Takes an array of exchange names and returns a slice from the supported idynamics of ONLY those.
        """
        # update idynamics
        sliced = {}
        for exchange in self.supported_idynamics:
            for name in names:
                if exchange.name == name:
                    sliced[exchange] = self.supported_idynamics[exchange]
        self.idynamics = sliced

        self.pgator.exchanges = list(self.idynamics.keys())

    def getWithSymbol(self, Handler, symbol):
        """
        Get a bouncer or scanner with symbol
        """
        thing = None
        if Handler == Scanner:
            for scanner in self.scanners:
                if scanner.symbol == symbol:
                    thing = scanner
        elif Handler == Bouncer:
            if self.bouncers:
                for bouncer in self.bouncers:
                    if bouncer.symbol == symbol:
                        thing = bouncer
        return thing

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

    def addBouncer(self, symbol, order_size):
        """
        Add a single bouncer to self.bouncers.
        """
        logs.debug(f"Trying to add bouncer with {symbol} and {order_size}")
        exchanges = []
        for i in self.idynamics:
            if symbol in self.idynamics[i]:
                exchanges.append(i)
        if len(exchanges) >= 2:
            try:
                self.bouncers.append(
                    Bouncer(
                        symbol,
                        float(order_size),
                        exchanges,
                        initializeq=False,
                        speedup=10,
                        margin=0.01,
                        min_speedup=0.1,
                    )
                )
            except ValueError:
                logs.debug(f"{order_size} is not a number.")
        else:
            logs.debug(f"{symbol} is not supported by more than 1 exchange.")

    def createDynamicSB(self, handler, trade_size=100, minnum=2):
        """
        Create scanners OR bouncers for ALL the dynamic exchanges.
        """
        if handler == Scanner:
            name = "scanner"
        elif handler == Bouncer:
            name = "bouncer"
        else:
            return []

        self.scanners = []
        logs.debug(
            colorEh(
                "{} ({} pairs found)".format(
                    stringitizeL(list(self.dynamic_commons.keys())),
                    len(self.dynamic_commons),
                )
            )
        )
        logs.debug(colorGood(f"Creating {len(self.dynamic_commons)} {name}s ..."))
        for e in tqdm(
            self.dynamic_commons,
            disable=BARSDISABLED,
            leave=False,
            unit="sym",
            dynamic_ncols=True,
            desc="symbl",
        ):
            if len(self.dynamic_commons[e]) >= minnum:
                self.scanners.append(
                    handler(
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
        logs.debug(colorGood(f"Created {len(self.dynamic_commons)} {name}s!\n"))
        return self.scanners

    def myPrint(self, dic):
        for x in dic:
            logs.debug(f"'{x}': ", end="")
            for exc in dic[x]:
                logs.debug(f"{exc}: " + "{ ... }")

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
            self.scanners,
            disable=BARSDISABLED,
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
                logs.debug(
                    colorEh(
                        f"Symbol {scan.symbol} not found in props! This is probably not an issue, but beware."
                    )
                )
                # procs.append(
                #     Thread(
                #        target=scan.wrapGetSpreadToResults,
                #         args=(responses),
                #     )
                # )
        # start
        for proc in tqdm(
            procs,
            disable=BARSDISABLED,
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

    def bounce(self, props):
        """
        Bounce once
        """
        pass

    def scanNTimes(self, n=1):
        """
        Scan every single exchange n times and print a summary.
        """
        # nested loop with progressbar
        total = len(self.scanners) * n
        with tqdm(
            total=total,
            disable=BARSDISABLED,
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
                logs.debug(message)
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
    logs.debug(f"Scanned all symbols {n} times in {(nowD()-start_time)}")
