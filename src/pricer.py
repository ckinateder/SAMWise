import asyncio, aiohttp
import json
import threading
import time
from tqdm import tqdm
from pprint import pformat, pprint

import ccxt
import concurrent.futures
import requests
import threading
from bs4 import BeautifulSoup

from hive import Hive
from helper import *

start = now()


class Pricer:
    def __init__(self):
        self.props = {}
        h = Hive()
        self.exchanges = h.exchanges
        self.dynamics = h.getDynamicCommons()
        self.idynamics = h.transpose(self.dynamics)
        # set keys
        for key in list(self.dynamics.keys()):
            self.props[key] = {}

    def getOneSymbol(self, exchange, symbol, loud=False):
        """
        Get one single symbol on one exchange.
        """
        s = now()
        try_again = True
        timeout = 2
        count = 0
        while try_again and count < timeout:
            try:
                resp = exchange.fetchTicker(symbol)
                if exchange.id == "coinbasepro":
                    time.sleep(0.08)
                if loud:
                    tqdm.write(f"got {symbol} on {exchange} in {now()-s:.2f}s")
                return resp
            except ccxt.RateLimitExceeded:
                tqdm.write("RateLimitExceeded")
                try_again = True
                count += 1
                time.sleep(5)
        return {}

    def getMultipleSymbols(self, exchange, symbols):
        """
        Get multiple symbols in a bulk call on one exchange.
        """
        out = {}
        for key in list(self.dynamics.keys()):
            out[key] = {}

        bulk = exchange.fetchTickers(symbols)
        for symbol in bulk:
            out[symbol][exchange] = bulk[symbol]
        return out

    def divideSymbols(self, exchange, symbols):
        """
        For exchanges that cant fetch all at once, divide up for each
        """
        intermediate = {}
        for symbol in symbols:
            resp = self.getOneSymbol(exchange, symbol)
            # self.props[symbol].append({exchange: resp})
            if symbol in intermediate:
                intermediate[symbol][exchange] = resp
            else:
                intermediate[symbol] = {exchange: resp}
        return intermediate

    def mergeProps(self, one, two):
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
        inplace = two
        final_out = {}
        for symbol in one:
            if symbol in two:
                inplace[symbol].update(one[symbol])
                final_out[symbol] = inplace[symbol]
                inplace = two
            else:
                final_out[symbol] = one[symbol]
        return final_out

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

    # get slugs
    def propagate(self, exchange):
        """
        Get all tickers for each exchange, then propagate into dictionary. EACH CALL TO EACH EXCHANGE WILL BE ASYNC
        Ex:
        {
            'BTC/USD': {
                ccxt.coinbasepro(): {...},
                ccxt.kraken(): {...},
                ccxt.binanceus(): {...},
                ...etc
            }
        }
        """  # pprint(self.idynamics)
        # fetch for each

        # for exchange in self.idynamics:
        tqdm.write(exchange)
        if exchange.has["fetchTickers"]:
            tqdm.write(f"quick {exchange}")
            tqdm.write(self.idynamics.keys())
            inter = self.getMultipleSymbols(exchange, self.idynamics[exchange])
            self.mergeProps(inter, self.props)

        elif exchange.has["fetchTicker"]:
            tqdm.write(f"slow {exchange} ...")
            inter = self.divideSymbols(exchange, self.idynamics[exchange])
            self.mergeProps(inter, self.props)

        # pprint(self.props)
        tqdm.write(
            f"data makes sense: {self.verify(test=self.props, sure=self.dynamics)}"
        )

    def spread(self):
        for exchange in self.exchanges:
            self.propagate(exchange)
        return self.props


if __name__ == "__main__":
    pricer = Pricer()
    pricer.spread()
    pprint(pricer.props)
    tqdm.write(f"finished in {now()-start:.2f}s")