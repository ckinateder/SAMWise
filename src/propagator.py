import ccxt
from tqdm import tqdm
from tqdm.std import trange
from helper import *
from threading import Thread
from datetime import datetime
from pprint import pprint
import json
import time


class Propagtor:
    def __init__(self):
        pass

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

    def _rateLimit(self, waittime):
        for interval in trange(
            waittime * 1000,
            leave=False,
            desc="timer",
            dynamic_ncols=True,
            position=1,
        ):
            time.sleep(0.001)

    def distribute(self, procs):
        """
        Takes a list of Thread objects and runs them simeultaneous, and waits til the last completion.
        """
        # start
        for proc in procs:
            proc.start()
        # join
        for proc in procs:
            proc.join()

    def prepareSQL(self, response, exchange):
        """
            Prepare the data for the database and make sure format fits
        +---------------+--------------+------+-----+---------+----------------+
        | Field         | Type         | Null | Key | Default | Extra          |
        +---------------+--------------+------+-----+---------+----------------+
        | id            | int          | NO   | PRI | NULL    | auto_increment |
        | symbol        | varchar(10)  | YES  |     | NULL    |                |
        | exchange      | varchar(40)  | YES  |     | NULL    |                |
        | timestamp     | timestamp    | YES  |     | NULL    |                |
        | ask           | decimal(9,5) | YES  |     | NULL    |                |
        | askVolume     | decimal(9,5) | YES  |     | NULL    |                |
        | average       | decimal(9,5) | YES  |     | NULL    |                |
        | baseVolume    | decimal(9,5) | YES  |     | NULL    |                |
        | bid           | decimal(9,5) | YES  |     | NULL    |                |
        | close         | decimal(9,5) | YES  |     | NULL    |                |
        | datetime      | datetime     | YES  |     | NULL    |                |
        | dx            | decimal(9,5) | YES  |     | NULL    |                |
        | high          | decimal(9,5) | YES  |     | NULL    |                |
        | info          | json         | YES  |     | NULL    |                |
        | last          | decimal(9,5) | YES  |     | NULL    |                |
        | low           | decimal(9,5) | YES  |     | NULL    |                |
        | open          | decimal(9,5) | YES  |     | NULL    |                |
        | percentage    | decimal(9,5) | YES  |     | NULL    |                |
        | previousClose | decimal(9,5) | YES  |     | NULL    |                |
        | quoteVolume   | decimal(9,5) | YES  |     | NULL    |                |
        | vwap          | decimal(9,5) | YES  |     | NULL    |                |
        +---------------+--------------+------+-----+---------+----------------+
        """
        # round to 5 d
        for k in response:
            if type(response[k]) == float or type(response[k]) == int:
                response[k] = round(response[k], 5)
        # add exchange in
        response["exchange"] = exchange
        response["info"] = json.dumps(response["info"])
        # rename "change" for sql
        if "change" in response:
            response["dx"] = response.pop("change")

        # fix dating
        if not response["timestamp"] == None:
            response["datetime"] = datetime.fromtimestamp(
                response["timestamp"] / 1e3
            ).strftime(TIME_FORMAT)
        elif not response["datetime"] == None:
            # original format: 2021-02-21T04:21:57.585Z
            response["datetime"] = datetime.strptime(
                response["datetime"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).strftime(TIME_FORMAT)
        else:
            response["datetime"] = nowD().strftime(TIME_FORMAT)
            response["timestamp"] = now() * 1000

    def _mergeProps(self, one, two):
        """
        Merge one
        {
            'BTC/USD': {
                ccxt.coinbasepro(): {...},
                ccxt.kraken(): {...},
                ccxt.binanceus(): {...},
                ...etc
            }
        }
        into two
        {
            'BTC/USD': {
                ccxt.bitfinex(): {...},
                ccxt.binance(): {...},
                ccxt.phemex(): {...},
                ...etc
            }
        }
        """
        final_out = two.copy()
        for symbol in one:
            if symbol in final_out:
                for exchange in one[symbol]:
                    final_out[symbol][exchange] = one[symbol][exchange]
            else:
                final_out[symbol] = {}
                for exchange in one[symbol]:
                    final_out[symbol][exchange] = one[symbol][exchange]
        return final_out

    def _transposeBatchTickers(self, original, exchange):
        """
        Flip a dictionary of dictionaries
        """
        inverted = {}

        for symbol in original.values():
            act = symbol["symbol"]
            inverted[act] = {exchange: symbol}

        return inverted

    def _getBatchTickers(self, exchange, tickers):
        """
        Get a batch of tickers from exchange and transpose it.
        Example return:
        {
            'BTC/USD': {
                ccxt.binance(): {...}
            },
            'ETH/USD': {
                ccxt.binance(): {...}
            },
            ... etc
        }
        """
        try:
            resp = exchange.fetchTickers(tickers)
            for i in resp:
                self.prepareSQL(resp[i], exchange)
            trans = self._transposeBatchTickers(resp, exchange)
        except:
            tqdm.write(
                colorBad(
                    f"Unknown error occured fetching batch tickers on {exchange.id}"
                )
            )
        return trans

    def _divideBatchTickers(self, exchange, tickers):
        """
        Divide a bunch of tickers between one exchange
        """
        inter = {}

        procs = []
        for symbol in tickers:
            procs.append(
                Thread(
                    target=self._getSingleSymbol,
                    args=(
                        exchange,
                        symbol,
                        0,
                        inter,
                    ),
                )
            )
            # if single:
            #    inter[symbol] = {exchange: single}
            self.cycle_bar.update(1)

        self.distribute(procs)
        return inter

    def _getSingleSymbol(self, exchange, ticker, depth=0, inter=None):
        """
        Recursive function to get a single symbol and handlle errors
        """
        waittime = 4
        response = None
        if depth <= 2:  # don't waste too much time
            try:
                response = exchange.fetchTicker(ticker)
                if inter and response:
                    inter[ticker] = {exchange: response}
                if exchange.id == "coinbasepro":
                    time.sleep(0.1)
            except ccxt.RateLimitExceeded:
                tqdm.write(
                    colorBad(
                        f"Rate limit exceeded on {exchange} for {ticker} ... trying again in {waittime}"
                    )
                )
                self._rateLimit(waittime)
                response = self._getSingleSymbol(
                    exchange, ticker, depth=depth + 1, inter=inter
                )
            except:
                tqdm.write(
                    colorBad(
                        f"Unknown error occured fetching single symbol on {exchange.id}"
                    )
                )
                return None
        else:
            tqdm.write(
                colorBad(f"Rate limit exceeded on {exchange} for {ticker} ... skipping")
            )
        self.prepareSQL(response, exchange)
        return response

    def _doTickers(self, exchange, idynamics):
        if exchange.has["fetchTickers"]:
            ###
            # fetch tickers and merge into props
            resp = self._getBatchTickers(exchange, idynamics[exchange])
            self.props = self._mergeProps(resp, self.props)
            ###
            self.cycle_bar.update(len(idynamics[exchange]))

        elif exchange.has["fetchTicker"]:
            inter = {}
            ###
            # fetch ticker for each and merge into props
            inter = self._divideBatchTickers(exchange, idynamics[exchange])
            self.props = self._mergeProps(inter, self.props)
            ###

    def propagate(self, idynamics):
        """
        Build one giant dictionary of dictionaries of all data recieved.
        Example return:
        {
            'BTC/USD': {
                ccxt.binance(): {...},
                ccxt.coinbasepro(): {...},
                ccxt.binanceus(): {...},
            },
            'ETH/USD': {
                ccxt.bitfinex(): {...},
                ccxt.coinbasepro(): {...},
                ccxt.huobipro(): {...},
                ccxt.binanceus(): {...},
            },
            ... etc
        }

        """
        exchanges = list(idynamics.keys())
        tqdm.write(colorEh("Fetching tickers ... "))
        self.props = {}
        total = 0
        for i in idynamics:
            total += len(idynamics[i])
        self.cycle_bar = tqdm(
            total=total, leave=False, unit="exc", dynamic_ncols=True, desc="cycle"
        )
        procs = []
        for exchange in exchanges:
            # tqdm.write(f"Querying {exchange.name} ...")
            procs.append(
                Thread(
                    target=self._doTickers,
                    args=(
                        exchange,
                        idynamics,
                    ),
                )
            )
        self.distribute(procs)
        self.cycle_bar.close()
        return self.props
