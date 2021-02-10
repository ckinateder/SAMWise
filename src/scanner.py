import logging
from tqdm import tqdm
import sys
import csv
import time
from datetime import date, datetime, timedelta
from os import path
from math import log, floor

from collections import OrderedDict
from operator import getitem

import ccxt
import pandas as pd
from pprint import pformat, pprint

from helper import *

__author__ = "Calvin Kinateder"
__email__ = "calvinkinateder@gmail.com"


class Scanner:
    def __init__(
        self,
        symbol,
        quote_order_size,
        exchanges,
        speedup=10,
        margin=0.01,
        min_speedup=1,
        loud=True,
        position=None,
        timeout=3,
    ):
        """
        Create the class.
        Params:
            symbol: market pair to run on
            quote_order_size: how much each trade should be worth
            exchanges: exchanges it should run on
            speedup: max percentage value of how tight the margin may be squeezed
            margin: min trade profit
            min_speedup: min percentage value of how tight the margin may be squeezed
            loud: tqdm.write all pairs or just profitable
            position: optional, number assigned to object
            timeout: seconds to wait for a response until canceling
        """
        self.start_time = datetime.now()
        self.uptime = self.start_time - datetime.now()  # really not necessary
        self.position = position
        # precision to display quotes
        # speedup is used to narrow the price gap to enable trades to finish faster.
        self.max_speedup = speedup
        self.min_speedup = min_speedup
        self.exchanges = exchanges
        self.timeout = timeout
        self.notifying = False
        self.loud = loud
        # check if symbol supported by all
        if self.validateSymbol(symbol):
            self.symbol = symbol
            self.base_coin = symbol.split("/")[0]
            self.quote_coin = symbol.split("/")[1]
        else:
            tqdm.write(
                "Symbol '{}' not supported by all platforms. Exiting ...".format(symbol)
            )
            sys.exit(0)

        # set precision
        self.precision = 5

        if "USD" in self.quote_coin:
            self.precision = 2
        # get width
        self.height, self.width = updateSize()
        # find currency name
        count = 0
        self.currency_name = None
        while count < len(self.exchanges) and not self.currency_name:
            if self.base_coin in self.exchanges[count].currencies:
                if "name" in self.exchanges[count].currencies[self.base_coin]:
                    self.currency_name = self.exchanges[count].currencies[
                        self.base_coin
                    ]["name"]
            count += 1

        # initialize for indicators
        self.selling = None
        self.buying = None

        # initialize
        self.cycles = 0  # counts cycles
        self.quote_order_size = quote_order_size
        self.pro_filename = "logs/" + self.base_coin + "-" + self.quote_coin + ".csv"
        self.trades_filename = (
            "logs/trades/"
            + datetime.now().strftime("%m-%d-%Y_%H-%M")
            + "_"
            + self.base_coin
            + "-"
            + self.quote_coin
            + "_trades.csv"
        )
        self.margin = margin  # for trades

        exchanges_str = ""
        for i in range(0, len(self.exchanges) - 1):
            exchanges_str += self.exchanges[i].name + ", "
        exchanges_str += "and " + self.exchanges[-1].name
        self.ireq = (
            len(exchanges) * self.quote_order_size * 2
        )  # how much invested total
        if self.loud:
            tqdm.write(
                colorGood(
                    "Scanning for {}: playing with ${:,.0f}, speedup {}% to {}%, margin ${} - [{}]"
                ).format(
                    self.symbol,
                    self.ireq,
                    self.min_speedup,
                    self.max_speedup,
                    self.margin,
                    exchanges_str,
                )
            )

    def saveDict(self, toCSV):
        """
        takes a list of dictionaries and saves it to a csv
        """
        keys = toCSV[0].keys()
        did_exist = path.isfile(self.pro_filename)
        with open(self.pro_filename, "a+", newline="") as output_file:
            dict_writer = csv.DictWriter(output_file, keys)
            if not did_exist:
                dict_writer.writeheader()  # only write if not exists
            dict_writer.writerows(toCSV)

    def updateUptime(self):
        """
        Updates the uptime and returns a formatted string.
        """
        self.uptime = datetime.now() - self.start_time
        return strfdelta(self.uptime, "%H:%M:%S")

    def validateSymbol(self, symbol):
        """
        Returns whether or not the symbol is supported by all exchanges.
        """
        if symbol in self.getCommons():
            return True
        else:
            return False

    def getCommons(self):
        """
        Get symbols in common with ALL self.exchanges. Used to check if __init__ given a valid symbol or not.
        """
        alls = list()
        for i in self.exchanges:
            x = list(i.load_markets().keys())
            for j in x:
                alls.append(j)
        out = list()

        for item in alls:
            if alls.count(item) == len(self.exchanges):
                out.append(item)
        out = set(out)
        # for i in out:
        #    if 'USD' in i:
        #       tqdm.write(i, '1', end=' ')
        return out

    def getWatched(self):
        """
        Get responses for each exchange for self.symbol.
        """
        all_responses = dict()
        start = now()
        while now() - start <= self.timeout:
            for exchange in self.exchanges:
                try:
                    all_responses[exchange] = exchange.fetch_ticker(self.symbol)
                except ccxt.RateLimitExceeded:
                    tqdm.write(
                        colorBad("Rate limit exceeded on {}".format(exchange.name))
                    )
        if len(list(all_responses.keys())) < len(self.exchanges):
            missed = [
                i
                for i in self.exchanges + list(all_responses.keys())
                if i not in self.exchanges or i not in list(all_responses.keys())
            ]
            tqdm.write(colorBad("Timeout reached on {}".format(stringitizeL(missed))))
        return all_responses

    def calculateLiquidity(self, test_buy, test_sell):
        """
        Calculate the liquidity metric for two exchanges
        """
        l = "unknown"
        try:
            buy_volume = test_buy[1]["quoteVolume"]
            sell_volume = test_sell[1]["quoteVolume"]
            buy_close = test_buy[1]["close"]
            sell_close = test_sell[1]["close"]
            buy_high = test_buy[1]["high"]
            buy_low = test_buy[1]["low"]
            sell_high = test_sell[1]["high"]
            sell_low = test_sell[1]["low"]
            l1 = (buy_volume * buy_close) / (buy_high - buy_low)
            l2 = (sell_volume * sell_close) / (sell_high - sell_low)
            # l = f'b{l1}  s{l2}'
            l = 0.5 * l1 + 0.5 * l2
        except:
            l = "unknown"
        return l

    def findFlipFlop(self, spreadlist):
        """
        Finds if an option in the spreadlist can be both bought and sold to and from each other and still be profitable.
        """
        flops = []
        flops_bool = False
        for item in spreadlist:
            for compared in spreadlist:
                if item["buy"] == compared["sell"] and item["sell"] == compared["buy"]:
                    flops_bool = True
                    flops.append([item, compared])
        # tqdm.write(flops)
        return flops_bool, flops

    def getSpread(self, responses=None):
        """
        Get tickers for the watched symbols and return exchanges and spread.
        returns: spreads, [error True or False]
        """  # update sizes
        self.height, self.width = updateSize()
        self.cycles += 1

        # only tqdm.write ONCE
        total_message = ""
        # return statements
        spreads_return = None
        error_return = True
        flip_flop_return = False
        try:
            #
            if responses == None:
                t_formatted = datetime.now().strftime("%m-%d-%Y_%H-%M-%S")
                timestamp = time.time()
                responses = self.getWatched()
            # not necessary to sort but it helps
            # pprint(responses)
            got_zero = False
            try:
                responses = OrderedDict(
                    sorted(responses.items(), key=lambda x: getitem(x[1], "ask"))
                )
            except TypeError:
                response_items = []
                got_zero = True
            response_items = list(responses.items())

            # set high and low
            """
            Format on response_items
            [
                (exchange,{
                    ask: 333,
                    bid: 345,
                    ...
                }),
                ...
            ]
            """

            # make dict of spreads COUNTING fees
            spreads = dict()
            for test_buy in response_items:
                for test_sell in response_items:
                    if not test_sell == test_buy:
                        buy_price = test_buy[1]["bid"]
                        sell_price = test_sell[1]["ask"]
                        if buy_price != 0 and sell_price != 0:
                            buy_volume = test_buy[1]["quoteVolume"]
                            sell_volume = test_sell[1]["quoteVolume"]
                            liquidity = self.calculateLiquidity(
                                test_buy, test_sell
                            )  # change

                            # calculate speedup
                            test_spread = (self.quote_order_size / sell_price) * (
                                sell_price - buy_price
                            )
                            test_fee = (
                                test_buy[0].calculateFee(
                                    self.symbol,
                                    "limit",
                                    "buy",
                                    self.quote_order_size / buy_price,
                                    buy_price,
                                    takerOrMaker="taker",
                                    params={},
                                )["cost"]
                                + test_sell[0].calculateFee(
                                    self.symbol,
                                    "limit",
                                    "sell",
                                    self.quote_order_size / sell_price,
                                    sell_price,
                                    takerOrMaker="taker",
                                    params={},
                                )["cost"]
                            )
                            spread_w_fee = test_spread - test_fee

                            actual_speedup = 0
                            inc = 0.001
                            ran = False
                            while (
                                spread_w_fee > self.margin + inc
                                and actual_speedup <= self.max_speedup
                            ):
                                buy_price = test_buy[1]["bid"] * (
                                    1 + (actual_speedup / 200)
                                )
                                sell_price = test_sell[1]["ask"] * (
                                    1 - (actual_speedup / 200)
                                )
                                # recalculate
                                test_spread = (self.quote_order_size / sell_price) * (
                                    sell_price - buy_price
                                )
                                test_fee = (
                                    test_buy[0].calculateFee(
                                        self.symbol,
                                        "limit",
                                        "buy",
                                        self.quote_order_size / buy_price,
                                        buy_price,
                                        takerOrMaker="taker",
                                        params={},
                                    )["cost"]
                                    + test_sell[0].calculateFee(
                                        self.symbol,
                                        "limit",
                                        "sell",
                                        self.quote_order_size / sell_price,
                                        sell_price,
                                        takerOrMaker="taker",
                                        params={},
                                    )["cost"]
                                )
                                spread_w_fee = test_spread - test_fee
                                actual_speedup = round(actual_speedup + inc, 3)
                                ran = True
                            if ran:
                                actual_speedup -= inc  # set after

                            # create dictionary
                            spreads[spread_w_fee] = {
                                "time": t_formatted,
                                "symbol": self.symbol,
                                "profitable": spread_w_fee >= self.margin,
                                "spread_w_fees": spread_w_fee,
                                "fees": test_fee,
                                "buy_price": buy_price,
                                "sell_price": sell_price,
                                "buy": test_buy[0],
                                "sell": test_sell[0],
                                "quote_order_size": self.quote_order_size,
                                "speedup": actual_speedup,
                                "buy_bid": test_buy[1]["bid"],
                                "buy_ask": test_buy[1]["ask"],
                                "buy_volume": buy_volume,
                                "sell_bid": test_sell[1]["bid"],
                                "sell_ask": test_sell[1]["ask"],
                                "sell_volume": sell_volume,
                                "liquidity": liquidity,
                                "no_fees": test_spread,  # a percent
                                "timestamp": timestamp,
                            }
                        else:
                            got_zero = True
            if not got_zero:
                spreads = sorted(
                    spreads.values(),
                    key=lambda x: (
                        getitem(x, "speedup"),
                        getitem(x, "spread_w_fees"),
                        getitem(x, "liquidity"),
                    ),
                )  # as a list
                # reverse the list for printing
                spreads.reverse()
                # pprint(spreads)
                # get last in list, sorted from low to high spread_w_fees
                """
                sample from spreads:
                {
                    'buy': ccxt.bittrex(),
                    'buy_ask': 1.30599,
                    'buy_bid': 1.24303,
                    'buy_price': 1.2676792848999983,
                    'buy_volume': None,
                    'fees': 0.35,
                    'liquidity': 4.422258513471112,
                    'no_fees': 0.36009720681011115,
                    'profitable': True,
                    'quote_order_size': 100,
                    'sell': ccxt.binanceus(),
                    'sell_ask': 1.298,
                    'sell_bid': 1.293,
                    'sell_price': 1.2722606600000022,
                    'sell_volume': 142404.2786,
                    'speedup': 3.9659999999996742,
                    'spread_w_fees': 0.01009720681011117,
                    'symbol': 'KNC/USD',
                    'time': '02-01-2021_00-20-52',
                    'timestamp': 1612156852.032166
                }
                """
                # get most profitable
                most_profitable = spreads[0]
                buy = most_profitable["buy"]
                sell = most_profitable["sell"]
                low = most_profitable["buy_price"]  # will remove soon
                high = most_profitable["sell_price"]  # ditto
                fees = most_profitable["fees"]
                no_fees = most_profitable["no_fees"]
                spread = most_profitable["spread_w_fees"]

                # create formatted out string
                exchanges_str = ""
                for i in range(0, len(responses)):
                    ask = response_items[i][1]["ask"]
                    bid = response_items[i][1]["bid"]
                    exchange = response_items[i][0]
                    if exchange == buy:
                        logstr = colorLow(
                            "\t{}: ${} ask, ${} bid".format(
                                exchange.name,
                                round(ask, self.precision),
                                round(bid, self.precision),
                            )
                        )
                    elif exchange == sell:
                        logstr = colorHigh(
                            "\t{}: ${} ask, ${} bid".format(
                                exchange.name,
                                round(ask, self.precision),
                                round(bid, self.precision),
                            )
                        )
                    elif exchange == sell and exchange == buy:
                        logstr = colorEh(
                            "\t{}: ${} ask, ${} bid".format(
                                exchange.name,
                                round(ask, self.precision),
                                round(bid, self.precision),
                            )
                        )
                    else:
                        logstr = "\t{}: ${} ask, ${} bid".format(
                            exchange.name,
                            round(ask, self.precision),
                            round(bid, self.precision),
                        )

                    exchanges_str += logstr + "\n"

                # remove all values less than margin
                for i in range(0, len(spreads)):
                    if spreads[i]["spread_w_fees"] <= self.margin:
                        spreads[i] = None
                spreads[:] = [x for x in spreads if x]

                # if empty, not profitable
                if spreads:
                    profitable = True
                    if self.notifying:
                        notify(f"Profitable on {self.symbol}")
                else:
                    profitable = False

                # show percentage

                currency_str = ""
                if self.currency_name:
                    currency_str = f" ({self.currency_name})"

                uptime_str = colorUptime(self.updateUptime())
                clock_str = colorClock(datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f"))

                total_header_str = (
                    "/"
                    + "-" * (self.width - 44)
                    + colorCycle(f"{self.cycles:2d}")
                    + "--"
                    + uptime_str
                    + "--"
                    + clock_str
                )

                flip_flop, flop_pairs = self.findFlipFlop(spreads)
                # indicates whether there are any open trades
                # format ** [buy, sell]
                if self.selling and self.buying:
                    indicator = colorGood("*") * 2
                else:  # all good
                    indicator = colorGood("*") * 2

                if spreads:
                    total_message += total_header_str + "\n"
                    total_message += "[For {} w/ ${:,.3f}{}]:\n".format(
                        (self.symbol), self.quote_order_size, currency_str
                    )

                    total_message += exchanges_str
                    if flip_flop:
                        msg_str = "{}".format(indicator)
                        intermediate = " [FF"
                        already = []
                        # iterate through flop pairs
                        for ff in flop_pairs:
                            # check if already done
                            already_done = False
                            for x in already:
                                if ff[0] == x[1]:
                                    already_done = True
                            if not already_done:
                                already.append(ff)
                                intermediate += " #{} & #{},".format(
                                    spreads.index(ff[0]) + 1, spreads.index(ff[1]) + 1
                                )
                                # tqdm.write(len(msg_str))
                                # tqdm.write(msg_str, end=' '*35)
                                # tqdm.write(
                                #    colorGood('max speedup of {}% (found {} profitable pairs ****)'.format(self.max_speedup, len(spreads))))  # .rjust(self.width-6))
                        intermediate = intermediate[:-1] + "]"
                        total_message += msg_str + colorGood(intermediate) + "\n"
                    else:
                        total_message += indicator + "\n"  # , end="")
                        # tqdm.write(colorGood("max speedup of {}% (found {} profitable pairs ****)".format(self.max_speedup, len(spreads))).rjust(self.width + 7))
                    for i in range(len(spreads)):
                        item = spreads[i]
                        total_message += (
                            "{} Adjusted Spread: ${} (after fees: ${})\n  (buy on {} @ ${}, sell on {} @ ${} [speedup: {}%, liquidity: {}])".format(
                                colorGood("[PASSED #{}]".format(i + 1)),
                                colorThreshold(item["no_fees"]),
                                colorThreshold(item["spread_w_fees"]),
                                colorLow(item["buy"].name),
                                colorLow(
                                    "{}".format(
                                        round(item["buy_price"], self.precision)
                                    )
                                ),
                                colorHigh(item["sell"].name),
                                colorHigh(
                                    "{}".format(
                                        round(item["sell_price"], self.precision)
                                    )
                                ),
                                colorThreshold(
                                    item["speedup"], threshold=self.min_speedup
                                ),
                                colorLiquidity(item["liquidity"], threshold=1),
                            )
                            + "\n"
                        )
                else:
                    if self.loud:
                        total_message += total_header_str + "\n"
                        total_message += (
                            "[For {} w/ ${:,.3f}{}]:".format(
                                (self.symbol), self.quote_order_size, currency_str
                            )
                        ) + "\n"
                        total_message += exchanges_str
                        total_message += (indicator) + "\n"
                        if spread > 0 and spread <= self.margin:
                            msg = colorEh("[FAILED]")
                        else:
                            msg = colorBad("[FAILED]")
                        total_message += (
                            "{} Adjusted Spread: ${} (after fees: ${})\n (buy on {} @ ${}, sell on {} @ ${} [grs.dif: ${}])".format(
                                msg,
                                colorThreshold(no_fees),
                                colorThreshold(spread),
                                colorLow(buy.name),
                                colorLow("{}".format(round(low, self.precision))),
                                colorHigh(sell.name),
                                colorHigh("{}".format(round(high, self.precision))),
                                colorThreshold((high - low), 3, self.margin),
                            )
                            + "\n"
                        )
                if profitable:
                    self.saveDict(spreads)

                spreads_return = spreads
                error_return = False
                flip_flop_return = flip_flop
        except Exception as e:
            total_message += (
                colorBad("Error getting spread for {} ({})".format(self.symbol, e))
            ) + "\n"

        # tqdm.write EVERYTHING
        tqdm.write(total_message, end="")
        return spreads_return, error_return, flip_flop_return

    def switch(self, new_symbol):
        self.symbol = new_symbol

    def __str__(self):
        return f"Scanner @ {self.symbol}"