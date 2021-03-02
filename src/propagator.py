import ccxt
from tqdm import tqdm
from tqdm.std import trange
from helper import *
from threading import Thread
from datetime import datetime, timezone
from pprint import pprint
import json
import time
from os import error, listdir, path


class Propagtor:
    def __init__(self):
        self.exchanges = None

    def getAvailableExchanges(self):
        """
        Get all existing exchanges
        """
        # find exchanges from file structure
        file_list = listdir(KEYPATH)
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

    def loadExchanges(self, all_ex):
        """
        Create self.exchanges objects for all existing ones
        """

        self.exchanges = list()
        tqdm.write("Creating exchange objects for {} ...".format(stringitizeL(all_ex)))
        verified = []
        if path.exists(KEYPATH + "verified"):
            with open(KEYPATH + "verified", "r") as verified_f:
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
                    public = open(KEYPATH + exchstr + "_public").read().strip()
                    private = open(KEYPATH + exchstr + "_private").read().strip()

                    exchange_class = getattr(ccxt, exchstr)

                    if path.exists(KEYPATH + exchstr + "_password") and path.exists(
                        KEYPATH + exchstr + "_uid"
                    ):
                        password = open(KEYPATH + exchstr + "_password").read().strip()
                        uid = open(KEYPATH + exchstr + "_uid").read().strip()

                        current = exchange_class(
                            {
                                "apiKey": public,
                                "secret": private,
                                "password": password,
                                "uid": uid,
                            }
                        )
                    elif path.exists(KEYPATH + exchstr + "_uid"):
                        uid = open(KEYPATH + exchstr + "_uid").read().strip()

                        current = exchange_class(
                            {
                                "apiKey": public,
                                "secret": private,
                                "uid": uid,
                            }
                        )
                    elif path.exists(KEYPATH + exchstr + "_password"):
                        password = open(KEYPATH + exchstr + "_password").read().strip()

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
                        with open(KEYPATH + "verified", "a+") as verified_f:
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
                                exchstr, KEYPATH
                            )
                        )
                    )
            else:
                tqdm.write(
                    colorBad("Sorry, {} is not supported yet :(").format(exchstr)
                )

        tqdm.write(
            colorGood(
                "Done! Added exchanges {}.".format(stringitizeExc(self.exchanges))
            )
        )
        notify("Loaded {}".format(stringitizeExc(self.exchanges)))
        return self.exchanges

    def getDynamicCommons(self):
        """
        Get all symbols in common with minnum or more of the given self.exchanges.
        """
        tqdm.write("Getting shared symbols ...")
        # initialize keyset so loadmarkets not called twice
        keyset = {}
        alls = list()
        for exchange in tqdm(
            self.exchanges, unit="exc", leave=False, dynamic_ncols=True, desc="xchng"
        ):
            keyset[exchange] = list(exchange.load_markets().keys())
            x = keyset[exchange]
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
            for symbol in alls:
                if symbol in keyset[exchange]:
                    if symbol in compatibles:
                        compatibles[symbol].append(exchange)
                    else:  # initialize
                        compatibles[symbol] = [exchange]
        multiples = {}
        for key in compatibles:
            if len(compatibles[key]) >= 1:
                multiples[key] = compatibles[key]
        return multiples

    def getInvertedDynamicCommons(self, original=None):
        """
        Get all symbols in common with 3 or more of the given self.exchanges.
        """
        if not self.exchanges:
            self.exchanges = self.loadExchanges(self.getAvailableExchanges())
        if not original:
            original = self.getDynamicCommons(1)

        inverted = {}
        for symbol in original:
            for exchange in self.exchanges:
                if exchange in original[symbol]:
                    if exchange in inverted:
                        inverted[exchange].append(symbol)
                    else:
                        inverted[exchange] = [symbol]

        return inverted

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
            Prepare the data for the database inplace and make sure format fits
        +---------------+---------------+------+-----+---------+----------------+
        | Field         | Type          | Null | Key | Default | Extra          |
        +---------------+---------------+------+-----+---------+----------------+
        | id            | int           | NO   | PRI | NULL    | auto_increment |
        | symbol        | varchar(20)   | YES  |     | NULL    |                |
        | exchange      | varchar(40)   | YES  |     | NULL    |                |
        | timestamp     | bigint        | YES  |     | NULL    |                |
        | ask           | decimal(20,8) | YES  |     | NULL    |                |
        | askVolume     | decimal(20,8) | YES  |     | NULL    |                |
        | average       | decimal(20,8) | YES  |     | NULL    |                |
        | baseVolume    | decimal(20,8) | YES  |     | NULL    |                |
        | bid           | decimal(20,8) | YES  |     | NULL    |                |
        | close         | decimal(20,8) | YES  |     | NULL    |                |
        | datetime      | datetime      | YES  |     | NULL    |                |
        | batch         | datetime      | YES  |     | NULL    |                |
        | dx            | decimal(20,8) | YES  |     | NULL    |                |
        | high          | decimal(20,8) | YES  |     | NULL    |                |
        | last          | decimal(20,8) | YES  |     | NULL    |                |
        | low           | decimal(20,8) | YES  |     | NULL    |                |
        | open          | decimal(20,8) | YES  |     | NULL    |                |
        | percentage    | decimal(20,8) | YES  |     | NULL    |                |
        | previousClose | decimal(20,8) | YES  |     | NULL    |                |
        | quoteVolume   | decimal(20,8) | YES  |     | NULL    |                |
        | vwap          | decimal(20,8) | YES  |     | NULL    |                |
        +---------------+---------------+------+-----+---------+----------------+
        """
        # round to 5 d
        for k in response:
            if type(response[k]) == float or type(response[k]) == int:
                response[k] = round(response[k], 5)
        # add exchange in
        response["exchange"] = exchange
        # add batch in AND fix initial dating
        response["batch"] = self.batch.strftime(TIME_FORMAT)
        # delete info
        response.pop("info")
        # rename "change" for sql
        if "change" in response:
            response["dx"] = response.pop("change")

        # fix dating
        # handle timezone
        if response["datetime"]:
            # original format: 2021-02-21T04:21:57.585Z
            response["datetime"] = datetime.strptime(
                response["datetime"], "%Y-%m-%dT%H:%M:%S.%fZ"
            ).strftime(TIME_FORMAT)
        else:
            response["datetime"] = self.batch.strftime(TIME_FORMAT)
        if not response["timestamp"]:
            response["timestamp"] = self.batch.timestamp() * 1000

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
            return trans
        except:
            tqdm.write(
                colorBad(
                    f"Unknown error occured fetching batch tickers on {exchange.id}"
                )
            )
        return None

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
                self.timer(waittime)
                response = self._getSingleSymbol(
                    exchange, ticker, depth=depth + 1, inter=inter
                )
            except:
                tqdm.write(
                    colorBad(
                        f"Unknown error occured fetching single symbol on {exchange.id}"
                    )
                )
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
        self.batch = nowD().astimezone(tz=timezone.utc)
        exchanges = list(idynamics.keys())
        tqdm.write(colorEh("Fetching tickers ... "))
        self.props = {}
        total = 0
        for i in idynamics:
            total += len(idynamics[i])
        self.cycle_bar = tqdm(
            total=total, leave=False, unit="exc", dynamic_ncols=True, desc="fetch"
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
        return self.props, self.batch
