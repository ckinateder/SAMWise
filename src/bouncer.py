import csv
import logging
import sys
import time
from collections import OrderedDict
from datetime import date, datetime, timedelta
from math import floor, log
from operator import getitem
from os import path
from pprint import pformat, pprint

import ccxt
import pandas as pd

from helper import *
from scanner import Scanner

__author__ = "Calvin Kinateder"
__email__ = "calvinkinateder@gmail.com"


from tqdm import tqdm


class Bouncer(Scanner):
    """
    Extends the Scanner class to be able to actually make trades.
    """

    def __init__(
        self,
        symbol,
        quote_order_size,
        exchanges,
        initializeq=False,
        speedup=10,
        margin=0.01,
        min_speedup=1,
        silent=False,  # won't do anything here
        loud=True,
        position=None,
    ):
        """
        Create the class, extends Hive.
        Params:
            symbol: market pair to run on
            quote_order_size: how much each trade should be worth
            exchanges: exchanges it should run on
            initializeq: initialize balances or not
            speedup: max percentage value of how tight the margin may be squeezed
            trading: determines if acting or scanning
            margin: min trade profit
            min_speedup: min percentage value of how tight the margin may be squeezed
            loud: tqdm.write all pairs or just profitable
            position: optional, number assigned to object
        """
        super().__init__(
            symbol=symbol,
            quote_order_size=quote_order_size,
            exchanges=exchanges,
            speedup=speedup,
            margin=margin,
            min_speedup=min_speedup,
            loud=False,
            position=position,
        )
        self.trades_filename = (
            "logs/trades/"
            + nowD().strftime("%m-%d-%Y_%H-%M")
            + "_"
            + self.base_coin
            + "-"
            + self.quote_coin
            + "_trades.csv"
        )
        exchanges_str = ""
        self.trading = True
        # set up trades file
        self.trades_headers = [
            "Date",
            "Symbol",
            "Side",
            "Price",
            "Exchange",
            "Net Gain (%)",
        ]
        self.trades = pd.DataFrame(columns=self.trades_headers)
        self.trade_count = 0
        for i in range(0, len(self.exchanges) - 1):
            exchanges_str += self.exchanges[i].name + ", "
        exchanges_str += "and " + self.exchanges[-1].name
        self.ireq = (
            len(exchanges) * self.quote_order_size * 2
        )  # how much invested total

        tqdm.write(
            colorGood(
                "Spending ${:,.0f} for ${}: playing with ${:,.0f}, speedup {}% to {}%, margin ${} - [{}]"
            ).format(
                self.quote_order_size,
                self.symbol,
                self.ireq,
                self.min_speedup,
                self.max_speedup,
                self.margin,
                exchanges_str,
            )
        )

        # init balances
        self.balances = dict()
        self.net = 0
        self.section = "total"
        # initialize balances
        if initializeq:
            tqdm.write(
                "Initializing balances with ${} worth of {} in each account.".format(
                    self.quote_order_size, self.base_coin
                )
            )
            self.inititalizeBalances()
        (
            self.start_total_base_amount,
            self.start_total_quote_amount,
        ) = self.updateBalances(loud=False)

        tqdm.write(
            colorClock("Starting base amount [{:.8f} {}, {:.4f} {}]").format(
                self.start_total_base_amount,
                self.base_coin,
                self.start_total_quote_amount,
                self.quote_coin,
            )
        )

    def updateBalances(self, loud=True):
        """
        Log balances to file and total base and quote amounts.
        """
        for exchange in self.exchanges:
            try:
                self.balances[exchange] = exchange.fetch_balance()
                # pprint(self.balances[exchange])
            except Exception as e:
                if self.trading:
                    tqdm.write(
                        colorBad(
                            "Balances for {} could not be fetched - removing from exchanges. ({})".format(
                                exchange.name, e
                            )
                        )
                    )
                    self.exchanges.remove(exchange)
                else:
                    tqdm.write(
                        colorBad(
                            "Balances for {} could not be fetched.".format(
                                exchange.name
                            )
                        )
                    )
                self.balances[exchange] = {}
                self.balances[exchange][self.section] = {}

        if loud:
            for exchange in self.exchanges:
                tqdm.write(
                    "{} balance response - {}".format(
                        exchange, pformat(self.balances[exchange])
                    )
                )

        total_base_amount = 0
        for exchange in self.exchanges:
            if self.base_coin in self.balances[exchange][self.section]:
                total_base_amount += self.balances[exchange][self.section][
                    self.base_coin
                ]
            else:
                self.balances[exchange][self.section][self.base_coin] = 0

        total_quote_order_size = 0
        for exchange in self.exchanges:
            if self.quote_coin in self.balances[exchange][self.section]:
                total_quote_order_size += self.balances[exchange][self.section][
                    self.quote_coin
                ]
            else:
                self.balances[exchange][self.section][self.quote_coin] = 0
        if loud:
            for exchange in self.exchanges:
                tqdm.write(
                    "\t{} balances ({}) - [{}: {}, {}: {}]".format(
                        exchange,
                        self.section,
                        self.base_coin,
                        self.balances[exchange][self.section][self.base_coin],
                        self.quote_coin,
                        self.balances[exchange][self.section][self.quote_coin],
                    )
                )

        # bittrex_string, binance_string, kraken_string, coinbasepro_string
        return total_base_amount, total_quote_order_size

    def updateNet(self, loud=False):
        """
        Returns self.net as a percent and updates. CURRENTLY NOT IMPLEMENTED.
        """
        base, quote = self.updateBalances(loud)
        if self.start_total_base_amount == 0 or self.start_total_quote_amount == 0:
            self.net = 0
        else:
            self.net = 0
        return self.net

    def inititalizeBalances(self):
        """
        Optional function used to initialize the balances buying the crypto needed in each exchange.
        """
        # note, bc of fees it will buy 2 dollar higher.
        self.updateBalances(loud=False)

        for exchange in self.exchanges:
            price = (exchange.fetch_ticker(self.symbol))["bid"]
            if (
                self.balances[exchange][self.section][self.quote_coin]
                >= self.quote_order_size
            ):
                try:
                    tqdm.write(
                        "Creating buy order on {} for {} {}".format(
                            exchange, self.quote_order_size / price, self.symbol
                        )
                    )
                    exchange.create_market_buy_order(
                        self.symbol, self.quote_order_size / price
                    )
                    self.trade_count += 1
                    new_row = [
                        nowD().strftime(TIME_FORMAT),
                        self.symbol,
                        "buy",
                        price,
                        exchange.name,
                        self.net,
                    ]
                    self.trades.loc[len(self.trades)] = new_row
                except ccxt.ExchangeNotAvailable:
                    tqdm.write("Market on {} offline.".format(exchange.name))
            else:
                tqdm.write(
                    "* Insufficient funds on {} to initialize balance".format(
                        exchange.name
                    )
                )

        self.blockTrades(5)

    def anyOpen(self, exchange=None):
        """
        Checks if any trades are open. If given an exchange, it only checks for that exchange, otherwise it will check for all self.exchanges.
        """
        if exchange == None:
            for i in self.exchanges:
                x = i.fetch_open_orders(self.symbol)
                if len(x) > 0:
                    return True
        else:
            if len(exchange.fetch_open_orders(self.symbol)) > 0:
                return True

        return False

    def cleanup(self):
        """
        Cleans up by selling off any balances still left on platforms.
        """
        tqdm.write("Cleaning up for {}...".format(self.symbol))
        responses = self.getWatched()
        self.updateBalances(loud=False)

        for exchange in responses:
            # sell remaining
            remaining = float(self.balances[exchange][self.section][self.base_coin])
            if remaining > 0 and not self.anyOpen(exchange):
                try:
                    tqdm.write(
                        "Selling off {:.6f} {} on {}".format(
                            remaining, self.base_coin, exchange.name
                        )
                    )
                    exchange.create_market_sell_order(self.symbol, remaining)
                except Exception as e:
                    tqdm.write(
                        "* Error in selling off {:.6f} {} on {}: {}".format(
                            remaining, self.base_coin, exchange.name, e
                        )
                    )
            else:
                tqdm.write(
                    "No need to sell, no balance in {} on {}".format(
                        self.base_coin, exchange.name
                    )
                )
        """
        self.blockTrades(5)
        tqdm.write('Final balances:')
        base, quote = self.updateBalances(loud=False)
        tqdm.write('Sums: [{:.8f} {}, {} {}]'.format(
            base, self.base_coin, quote, self.quote_coin))
        self.updateNet()
        tqdm.write('Net: {}%'.format(colorThreshold(self.net)))
        tqdm.write('Done!\n')
        """
        tqdm.write(colorEh("Trades sumbitted ... exiting."))

    def blockTrades(self, timewait):
        """
        Blocks code until no active trades.
        """
        tqdm.write(colorEh("Trades initiated ... blocking to completion"))

        open_trades = self.anyOpen()
        while open_trades:
            open_trades = self.anyOpen()
            time.sleep(timewait)

        tqdm.write(colorGood("Trades completed! Moving on."))

    def handleTransaction(self, buy_ex, sell_ex, low, high):
        """
        Places the arbitrage transactions simultaneously.
        """
        amt = self.quote_order_size / high
        try:
            # creating processes
            tqdm.write(
                "Creating buy order on {} for {:.6f} {} at ${}".format(
                    buy_ex, amt, self.symbol, low
                )
            )
            self.buying = buy_ex
            buy_ex.create_limit_buy_order(self.symbol, amt, low)
            self.trade_count += 1
            new_row = [
                nowD().strftime(TIME_FORMAT),
                self.symbol,
                "buy",
                low,
                buy_ex.name,
                self.net,
            ]
            self.trades.loc[len(self.trades)] = new_row
            self.trades.to_csv(path_or_buf=self.trades_filename)

            tqdm.write(
                "Creating sell order on {} for {:.6f} {} at ${}".format(
                    sell_ex, amt, self.symbol, high
                )
            )
            self.selling = sell_ex
            sell_ex.create_limit_sell_order(self.symbol, amt, high)
            self.trade_count += 1
            new_row = [
                nowD().strftime(TIME_FORMAT),
                self.symbol,
                "sell",
                high,
                sell_ex.name,
                self.net,
            ]
            self.trades.loc[len(self.trades)] = new_row
            self.trades.to_csv(path_or_buf=self.trades_filename)

            # self.blockTrades(5)
            tqdm.write(
                colorEh("Trades initiated... disabling arbitrage until completed.")
            )
            # perform calculations for logging
        except ccxt.ExchangeNotAvailable:
            tqdm.write(colorBad("Exchange not available."))

        # recalculate
        self.updateNet()

        # tqdm.write('Balances fetched')
        self.updateBalances(loud=False)

        return "Done"

    def arbitrate(self):
        """
        Calculate spread and buy on low and sell on high, with checking for low balances and whatnot.
        """
        try:
            spreads, error, flip_flop = self.getSpread()

            # add and subtract from mock balances here

            if spreads and self.trading and not error and not self.anyOpen():
                # get balances
                self.updateBalances(loud=False)

                action_taken = False
                for pair in spreads:
                    if not action_taken and pair["speedup"] >= self.min_speedup:
                        buy_ex = pair["buy"]
                        sell_ex = pair["sell"]
                        low = pair["buy_price"]
                        high = pair["sell_price"]

                        quote_balance = self.balances[buy_ex][self.section][
                            self.quote_coin
                        ]
                        base_balance = self.balances[sell_ex][self.section][
                            self.base_coin
                        ]
                        if (
                            quote_balance >= self.quote_order_size
                            and base_balance >= self.quote_order_size / high
                        ):  # balances are good for original
                            tqdm.write(
                                colorGood(
                                    "Executing option {} ...".format(
                                        spreads.index(pair) + 1
                                    )
                                )
                            )
                            self.handleTransaction(buy_ex, sell_ex, low, high)
                            action_taken = True
                        elif (
                            quote_balance < self.quote_order_size
                            and base_balance < self.quote_order_size / high
                        ):
                            tqdm.write(
                                colorBad(
                                    "* Insufficient balance (missing ${} on {}, {:.4f} {} on {})".format(
                                        round(
                                            self.quote_order_size - quote_balance,
                                            self.precision,
                                        ),
                                        buy_ex.name,
                                        self.quote_order_size / high - base_balance,
                                        self.base_coin,
                                        sell_ex.name,
                                    )
                                )
                            )
                        elif quote_balance < self.quote_order_size:
                            tqdm.write(
                                colorBad(
                                    "* Insufficient balance (missing ${} on {})".format(
                                        round(
                                            self.quote_order_size - quote_balance,
                                            self.precision,
                                        ),
                                        buy_ex.name,
                                    )
                                )
                            )
                        elif base_balance < self.quote_order_size / high:
                            tqdm.write(
                                colorBad(
                                    "* Insufficient balance (missing {:.4f} {} on {})".format(
                                        self.quote_order_size / high - base_balance,
                                        self.base_coin,
                                        sell_ex.name,
                                    )
                                )
                            )
                    elif pair["speedup"] < self.min_speedup:
                        tqdm.write(
                            colorBad(
                                "Speedup too low ({} < {}) to place order ...".format(
                                    pair["speedup"], self.min_speedup
                                )
                            )
                        )
            elif error:
                tqdm.write(
                    colorBad("* Error in symbol {} - price returned 0.").format(
                        self.symbol
                    )
                )

        except Exception as e:
            tqdm.write(colorBad("Error in call ... moving on ({})").format(e))

    def __str__(self):
        return f"Bouncer @ {self.symbol}"
