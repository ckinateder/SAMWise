import logging
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

from crayon import *

__author__ = "Calvin Kinateder"
__email__ = "calvinkinateder@gmail.com"

WIDTH = 100


class Bouncer:
    def __init__(
        self,
        symbol,
        quote_order_size,
        exchanges,
        initializeq=False,
        speedup=10,
        trading=False,
        margin=0.01,
        min_speedup=1,
        logging=True,
        loud=True,
        position=None,
    ):
        """
        Create the class.
        Params:
            symbol: market pair to run on
            quote_order_size: how much each trade should be worth
            exchanges: exchanges it should run on
            initializeq: initialize balances or not
            speedup: max percentage value of how tight the margin may be squeezed
            trading: determines if acting or scanning
            margin: min trade profit
            min_speedup: min percentage value of how tight the margin may be squeezed
            logging: log to file or not
            loud: print all pairs or just profitable
            position: optional, number assigned to object
        """
        self.start_time = datetime.now()
        self.position = position
        # mark which balance section to look at
        self.section = "total"
        # precision to display quotes
        self.precision = ":.3f"
        # speedup is used to narrow the price gap to enable trades to finish faster.
        self.max_speedup = speedup
        self.min_speedup = min_speedup
        self.exchanges = exchanges

        self.loud = loud
        self.logging = True  # log to file?
        # check if symbol supported by all
        if symbol in self.getCommons():
            self.symbol = symbol
            self.base_coin = symbol.split("/")[0]
            self.quote_coin = symbol.split("/")[1]
        else:
            print(
                "Symbol '{}' not supported by all platforms. Exiting ...".format(symbol)
            )
            sys.exit(0)

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
        self.sell = None
        self.buy = None

        # initialize
        self.trading = trading
        self.trade_count = 0
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

        for i in range(0, len(self.exchanges) - 1):
            exchanges_str += self.exchanges[i].name + ", "
        exchanges_str += "and " + self.exchanges[-1].name

        if self.trading:
            print(
                colorGood(
                    "Created Bouncer investing ${} on {} with speedup {}% to {}% and margin ${} - [{}]"
                ).format(
                    self.quote_order_size,
                    self.symbol,
                    self.min_speedup,
                    self.max_speedup,
                    self.margin,
                    exchanges_str,
                )
            )
        else:
            if logging:
                print(
                    colorGood(
                        "Scanning for {} with speedup {}% to {}% and margin ${} - [{}]"
                    ).format(
                        self.symbol,
                        self.min_speedup,
                        self.max_speedup,
                        self.margin,
                        exchanges_str,
                    )
                )
            else:
                print(
                    colorGood(
                        "Scanning for {} with speedup {}% to {}% and margin ${}. Logging disabled - [{}]"
                    ).format(
                        self.symbol,
                        self.min_speedup,
                        self.max_speedup,
                        self.margin,
                        exchanges_str,
                    )
                )

        # init balances
        self.balances = dict()
        self.net = 0

        # initialize balances
        if initializeq:
            print(
                "Initializing balances with ${} worth of {} in each account.".format(
                    self.quote_order_size, self.base_coin
                )
            )
            self.inititalizeBalances()
        if self.trading:
            (
                self.start_total_base_amount,
                self.start_total_quote_amount,
            ) = self.updateBalances(loud=False)
        else:
            self.start_total_base_amount = 0
            self.start_total_quote_amount = 0
        if self.trading:
            print(
                colorClock("Starting base amount [{:.8f} {}, {:.4f} {}]").format(
                    self.start_total_base_amount,
                    self.base_coin,
                    self.start_total_quote_amount,
                    self.quote_coin,
                )
            )
            print()

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

    def getCommons(self):
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
        #       print(i, '1', end=' ')
        return out

    def getWatched(self):
        """
        Get responses for each exchange for self.symbol.
        """
        all_responses = dict()
        for exchange in self.exchanges:
            all_responses[exchange] = exchange.fetch_ticker(self.symbol)
        # print('Recived from {} in {self.precison} s'.format(
        #    ', '.join(all_responses.keys()), time.time()-before))
        return all_responses

    def calculateLiquidity(self, test_buy, test_sell):
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
            # l = f'b{l1:.3f}  s{l2:.3f}'
            l = 0.5 * l1 + 0.5 * l2
        except:
            l = "unknown"
        return l

    def shorten(self, liquid):
        if liquid == "unknown":
            return liquid
        else:
            units = ["", "K", "M", "G", "T", "P"]
            k = 1000.0
            magnitude = int(floor(log(liquid, k)))
            return "%.2f%s" % (liquid / k ** magnitude, units[magnitude])

    def findFlipFlop(self, spreadlist):
        flops = []
        flops_bool = False
        for item in spreadlist:
            for compared in spreadlist:
                if item["buy"] == compared["sell"] and item["sell"] == compared["buy"]:
                    flops_bool = True
                    flops.append([item, compared])
        # print(flops)
        return flops_bool, flops

    def getSpread(self, responses=None):
        """
        Get tickers for the watched symbols and return exchanges and spread
        """
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

        # make ordered dict of spreads COUNTING fees

        spreads = dict()  # OrderedDict()
        for test_buy in response_items:
            for test_sell in response_items:
                buy_price = test_buy[1]["bid"]
                sell_price = test_sell[1]["ask"]
                if buy_price != 0 and sell_price != 0:
                    buy_volume = test_buy[1]["quoteVolume"]
                    sell_volume = test_sell[1]["quoteVolume"]
                    liquidity = self.calculateLiquidity(test_buy, test_sell)  # change

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
                        buy_price = test_buy[1]["bid"] * (1 + (actual_speedup / 200))
                        sell_price = test_sell[1]["ask"] * (1 - (actual_speedup / 200))
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
                    # print(actual_speedup)
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
                key=lambda x: (getitem(x, "speedup"), getitem(x, "spread_w_fees")),
            )  # as a list

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
            most_profitable = spreads[0]
            buy = most_profitable["buy"]
            sell = most_profitable["sell"]

            low = most_profitable["buy_price"]  # will remove soon
            high = most_profitable["sell_price"]  # ditto
            fees = most_profitable["fees"]
            no_fees = most_profitable["no_fees"]
            spread = most_profitable["spread_w_fees"]

            # find buy and sell and log
            exchanges_str = ""
            for i in range(0, len(responses)):
                ask = response_items[i][1]["ask"]
                bid = response_items[i][1]["bid"]
                exchange = response_items[i][0]
                if exchange == buy:
                    fee = exchange.calculateFee(
                        self.symbol,
                        "limit",
                        "buy",
                        self.quote_order_size / ask,
                        ask,
                        takerOrMaker="taker",
                        params={},
                    )["cost"]
                    logstr = colorLow(
                        "\t{}: ${:.3f} ask, ${:.3f} bid".format(exchange.name, ask, bid)
                    )
                elif exchange == sell:
                    fee = exchange.calculateFee(
                        self.symbol,
                        "limit",
                        "sell",
                        self.quote_order_size / ask,
                        ask,
                        takerOrMaker="taker",
                        params={},
                    )["cost"]
                    logstr = colorHigh(
                        "\t{}: ${:.3f} ask, ${:.3f} bid".format(exchange.name, ask, bid)
                    )
                elif exchange == sell and exchange == buy:
                    fee = exchange.calculateFee(
                        self.symbol,
                        "limit",
                        "sell",
                        self.quote_order_size / ask,
                        ask,
                        takerOrMaker="taker",
                        params={},
                    )["cost"]
                    logstr = colorEh(
                        "\t{}: ${:.3f} ask, ${:.3f} bid".format(exchange.name, ask, bid)
                    )
                else:
                    fee = exchange.calculateFee(
                        self.symbol,
                        "limit",
                        "buy",
                        self.quote_order_size / ask,
                        ask,
                        takerOrMaker="taker",
                        params={},
                    )["cost"]
                    logstr = "\t{}: ${:.3f} ask, ${:.3f} bid".format(
                        exchange.name, ask, bid
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
            else:
                profitable = False

            # show percentage
            perc_str = ""
            if not self.position == None:
                perc_str = colorPerc("{:2.0f}%".format(self.position))
            # have cycle counter
            currency_str = ""
            if self.currency_name:
                currency_str = f" ({self.currency_name})"

            uptime_str = colorUptime(
                strfdelta(datetime.now() - self.start_time, "%H:%M:%S")
            )
            clock_str = colorClock(datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f"))

            total_header_str = (
                "/"
                + "-" * (WIDTH - 46)
                + perc_str
                + "--"
                + colorTrades("{0:02d}".format(self.trade_count))
                + "--"
                + uptime_str
                + "--"
                + clock_str
            )

            flip_flop, flop_pairs = self.findFlipFlop(spreads)

            # indicates whether there are any open trades
            # format ** [buy, sell]
            if self.sell and self.buy:
                if self.anyOpen(self.buy) and self.anyOpen(self.sell):
                    indicator = colorEh("*") * 2
                elif self.anyOpen(self.buy) and not self.anyOpen(self.sell):
                    indicator = colorEh("*") + colorGood("*")
                elif not self.anyOpen(self.buy) and self.anyOpen(self.sell):
                    indicator = colorGood("*") + colorEh("*")
                else:
                    indicator = colorGood("*") * 2
            elif self.anyOpen():  # cant find the order but knows theres open orders
                indicator = colorEh("*") * 2
            else:  # all good
                indicator = colorGood("*") * 2

            if spreads:
                print(total_header_str)
                print(
                    "[For {} w/ ${:.3f}{}]:".format(
                        (self.symbol), self.quote_order_size, currency_str
                    )
                )
                print(exchanges_str, end="")
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
                        if ff[0] == ff[1]:
                            intermediate += " #{},".format(
                                spreads.index(ff[0]) + 1, spreads.index(ff[1]) + 1
                            )
                            # print(len(msg_str))
                            # print(msg_str, end=' '*41)
                            # print(
                            #    colorGood('max speedup of {}% (found {} profitable pairs ****)'.format(self.max_speedup, len(spreads))))  # .rjust(WIDTH-2))
                        elif not already_done:
                            already.append(ff)
                            intermediate += " #{} & #{},".format(
                                spreads.index(ff[0]) + 1, spreads.index(ff[1]) + 1
                            )
                            # print(len(msg_str))
                            # print(msg_str, end=' '*35)
                            # print(
                            #    colorGood('max speedup of {}% (found {} profitable pairs ****)'.format(self.max_speedup, len(spreads))))  # .rjust(WIDTH-6))
                    intermediate = intermediate[:-1] + "]"
                    print(msg_str + colorGood(intermediate))
                else:
                    print(indicator, end="")
                    print(
                        colorGood(
                            "max speedup of {}% (found {} profitable pairs ****)".format(
                                self.max_speedup, len(spreads)
                            )
                        ).rjust(WIDTH + 7)
                    )
                for i in range(len(spreads)):
                    item = spreads[i]
                    print(
                        "{} Adjusted Spread: ${} (after fees: ${})\n  (buy on {} @ ${}, sell on {} @ ${} [speedup: {}%, liquidity: {}])".format(
                            colorGood("[PASSED #{}]".format(i + 1)),
                            colorThreshold(item["no_fees"]),
                            colorThreshold(item["spread_w_fees"]),
                            colorLow(item["buy"].name),
                            colorLow("{:.3f}".format(item["buy_price"])),
                            colorHigh(item["sell"].name),
                            colorHigh("{:.3f}".format(item["sell_price"])),
                            colorThreshold(item["speedup"], threshold=self.min_speedup),
                            colorLiquidity(item["liquidity"], threshold=1),
                        )
                    )
            else:
                if self.loud:
                    print(total_header_str)
                    print(
                        "[For {} w/ ${:.3f}{}]:".format(
                            (self.symbol), self.quote_order_size, currency_str
                        )
                    )
                    print(exchanges_str, end="")
                    print(indicator)
                    if spread > 0 and spread <= self.margin:
                        msg = colorEh("[FAILED]")
                    else:
                        msg = colorBad("[FAILED]")
                    print(
                        "{} Adjusted Spread: ${} (after fees: ${})\n (buy on {} @ ${}, sell on {} @ ${} [grs.dif: ${}])".format(
                            msg,
                            colorThreshold(no_fees),
                            colorThreshold(spread),
                            colorLow(buy.name),
                            colorLow("{:.3f}".format(low)),
                            colorHigh(sell.name),
                            colorHigh("{:.3f}".format(high)),
                            colorThreshold((high - low), 3, self.margin),
                        )
                    )

            if logging and profitable:
                self.saveDict(spreads)

            return spreads, False
        else:
            return None, True

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
                    print(
                        colorBad(
                            "Balances for {} could not be fetched - setting trading to false.".format(
                                exchange.name
                            )
                        )
                    )
                    self.trading = False
                else:
                    print(
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
                print(
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
                print(
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
        Returns self.net as a percent and updates.
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
                    print(
                        "Creating buy order on {} for {} {}".format(
                            exchange, self.quote_order_size / price, self.symbol
                        )
                    )
                    exchange.create_market_buy_order(
                        self.symbol, self.quote_order_size / price
                    )
                    self.trade_count += 1
                    new_row = [
                        datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                        self.symbol,
                        "buy",
                        price,
                        exchange.name,
                        self.net,
                    ]
                    self.trades.loc[len(self.trades)] = new_row
                except ccxt.ExchangeNotAvailable:
                    print("Market on {} offline.".format(exchange.name))
            else:
                print(
                    "* Insufficient funds on {} to initialize balance".format(
                        exchange.name
                    )
                )

        self.blockTrades(5)

    def anyOpen(self, exchange=None):
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
        print("Cleaning up for {}...".format(self.symbol))
        responses = self.getWatched()
        self.updateBalances(loud=False)

        for exchange in responses:
            # sell remaining
            remaining = float(self.balances[exchange][self.section][self.base_coin])
            if remaining > 0 and not self.anyOpen(exchange):
                try:
                    print(
                        "Selling off {:.6f} {} on {}".format(
                            remaining, self.base_coin, exchange.name
                        )
                    )
                    exchange.create_market_sell_order(self.symbol, remaining)
                except Exception as e:
                    print(
                        "* Error in selling off {:.6f} {} on {}: {}".format(
                            remaining, self.base_coin, exchange.name, e
                        )
                    )
            else:
                print(
                    "No need to sell, no balance in {} on {}".format(
                        self.base_coin, exchange.name
                    )
                )
        """
        self.blockTrades(5)
        print('Final balances:')
        base, quote = self.updateBalances(loud=False)
        print('Sums: [{:.8f} {}, {:.3f} {}]'.format(
            base, self.base_coin, quote, self.quote_coin))
        self.updateNet()
        print('Net: {}%'.format(colorThreshold(self.net)))
        print('Done!\n')
        """
        print(colorEh("Trades sumbitted ... exiting."))

    def blockTrades(self, timewait):
        print(colorEh("Trades initiated ... blocking to completion"))

        open_trades = self.anyOpen()
        while open_trades:
            open_trades = self.anyOpen()
            time.sleep(timewait)

        print(colorGood("Trades completed! Moving on."))

    def handleTransaction(self, buy_ex, sell_ex, low, high):
        """
        Places the arbitrage transactions simultaneously.
        """
        amt = self.quote_order_size / high
        try:
            # creating processes
            print(
                "Creating buy order on {} for {:.6f} {} at ${}".format(
                    buy_ex, amt, self.symbol, low
                )
            )
            self.buy = buy_ex
            buy_ex.create_limit_buy_order(self.symbol, amt, low)
            self.trade_count += 1
            new_row = [
                datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                self.symbol,
                "buy",
                low,
                buy_ex.name,
                self.net,
            ]
            self.trades.loc[len(self.trades)] = new_row
            self.trades.to_csv(path_or_buf=self.trades_filename)

            print(
                "Creating sell order on {} for {:.6f} {} at ${}".format(
                    sell_ex, amt, self.symbol, high
                )
            )
            self.sell = sell_ex
            sell_ex.create_limit_sell_order(self.symbol, amt, high)
            self.trade_count += 1
            new_row = [
                datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                self.symbol,
                "sell",
                high,
                sell_ex.name,
                self.net,
            ]
            self.trades.loc[len(self.trades)] = new_row
            self.trades.to_csv(path_or_buf=self.trades_filename)

            # self.blockTrades(5)
            print(colorEh("Trades initiated... disabling arbitrage until completed."))
            # perform calculations for logging
        except ccxt.ExchangeNotAvailable:
            print(colorBad("Exchange not available."))

        # recalculate
        self.updateNet()

        # print('Balances fetched')
        self.updateBalances(loud=False)

        return "Done"

    def arbitrate(self):
        """
        Calculate spread and buy on low and sell on high.
        """
        try:
            spreads, error = self.getSpread()

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
                            print(
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
                            print(
                                colorBad(
                                    "* Insufficient balance (missing ${:.3f} on {}, {:.4f} {} on {})".format(
                                        self.quote_order_size - quote_balance,
                                        buy_ex.name,
                                        self.quote_order_size / high - base_balance,
                                        self.base_coin,
                                        sell_ex.name,
                                    )
                                )
                            )
                        elif quote_balance < self.quote_order_size:
                            print(
                                colorBad(
                                    "* Insufficient balance (missing ${:.3f} on {})".format(
                                        self.quote_order_size - quote_balance,
                                        buy_ex.name,
                                    )
                                )
                            )
                        elif base_balance < self.quote_order_size / high:
                            print(
                                colorBad(
                                    "* Insufficient balance (missing {:.4f} {} on {})".format(
                                        self.quote_order_size / high - base_balance,
                                        self.base_coin,
                                        sell_ex.name,
                                    )
                                )
                            )
                    elif pair["speedup"] < self.min_speedup:
                        print(
                            colorBad(
                                "Speedup too low ({} < {}) to place order ...".format(
                                    pair["speedup"], self.min_speedup
                                )
                            )
                        )
            elif error:
                print(
                    colorBad("* Error in symbol {} - price returned 0.").format(
                        self.symbol
                    )
                )

        except Exception as e:
            print(colorBad("Error in call ... trying again in 10 ({})").format(e))
            time.sleep(10)
            self.arbitrate()
