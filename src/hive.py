from datetime import *
from statistics import mean
from os import error, listdir, path
from pprint import pformat, pprint

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
    Main class of the program. Handles collecting and controlling the data.
    """

    def __init__(self, minnum=3):
        self.pgator = propagator.Propagtor()
        with tqdm(
            total=3, position=1, leave=False, dynamic_ncols=True, desc="total"
        ) as init_bar:
            availables = self.pgator.getAvailableExchanges()
            init_bar.update(1)
            # create exchanges
            self.exchanges = self.pgator.loadExchanges(availables)
            init_bar.update(1)
            # create dynamics
            self.dynamic_commons = self.pgator.getDynamicCommons(minnum=minnum)
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

    def createDynamicScanners(self, trade_size=100):
        """
        Create scanners for all the dynamic exchanges
        """
        currencies = []
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
            currencies.append(
                Scanner(
                    e,
                    trade_size,
                    self.dynamic_commons[e],
                    margin=0.01,
                    min_speedup=0.2,
                    speedup=72,
                    loud=False,
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

    def scanAll(self, trade_size, n=1):
        """
        Scan every single exchange n times and print a summary. Set 'beta' to False to run the stable mode.
        """
        currencies = self.createDynamicScanners(trade_size=trade_size)
        idynamics = self.pgator.getInvertedDynamicCommons(original=self.dynamic_commons)
        # nested loop with progressbar
        total = len(currencies) * n
        total_profitables = []
        total_ff = []
        with tqdm(
            total=total,
            position=1,
            leave=False,
            unit="sym",
            dynamic_ncols=True,
            desc="total",
        ) as total_bar:
            for cmt in range(n):
                propagation_time = nowD()
                props = self.pgator.propagate(idynamics)
                propagation_time = nowD() - propagation_time
                # pprint(props)
                responses = {}
                # multiprocess this ----

                solve_time = nowD()
                for scan in tqdm(
                    currencies,
                    leave=False,
                    unit="sym",
                    dynamic_ncols=True,
                    desc="cycle",
                ):
                    if scan.symbol in props:
                        spreads, error, ff = scan.getSpread(props[scan.symbol])
                    else:
                        spreads, error, ff = scan.getSpread()
                    responses[scan] = {
                        "flip_flop": ff,
                        "error": error,
                        "profitables": len(spreads),
                    }
                    total_bar.update(1)

                solve_time = nowD() - solve_time
                # summarize
                cycle_profit_pairs = 0
                cycle_ff_pairs = 0
                for i in currencies:
                    cycle_profit_pairs += responses[i]["profitables"]
                    cycle_ff_pairs += responses[i]["flip_flop"]
                total_profitables.append(cycle_profit_pairs)
                total_ff.append(cycle_ff_pairs)
                # notify
                notify(
                    f"Completed cycle {cmt+1} of {n} ({((cmt+1)/n)*100:.0f}%) in {propagation_time}"
                )
                # sleep cause you don't need all that data
                tqdm.write(
                    f"Waiting 9s (propagated in {propagation_time}, solved in {solve_time}) ..."
                )
                timer(9)
        tqdm.write(
            colorGood(
                f"Average profitable pairs per cycle: {mean(total_profitables)}\nAverage flip flop pairs per cycle: {mean(total_ff)}"
            )
        )
        notify("Completed!")


if __name__ == "__main__":
    clear()
    intro()
    hive = Hive()

    # tableOfAll = hive.getTableOfAll()
    start_time = nowD()
    n = 100
    hive.scanAll(trade_size=100, n=n)
    tqdm.write(f"Scanned all symbols {n} times in {(nowD()-start_time)}")
