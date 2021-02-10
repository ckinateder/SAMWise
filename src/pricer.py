import asyncio, aiohttp
import json
import threading
import time
from pprint import pformat, pprint

import ccxt
import concurrent.futures
import requests
import threading
from bs4 import BeautifulSoup

from hive import Hive

start = time.time()


class Pricer:
    def __init__(self):
        self.props = {}
        h = Hive()
        self.dynamics = h.getDynamicCommons()
        self.idynamics = h.transpose(self.dynamics)
        # set keys
        for key in list(self.dynamics.keys()):
            self.props[key] = {}

    def getOneSymbol(self, exchange, symbol, loud=False):
        """
        Get one single symbol. this may not be necessary
        """
        s = time.time()
        try_again = True
        timeout = 2
        count = 0
        while try_again and count < timeout:
            try:
                resp = exchange.fetchTicker(symbol)
                if exchange.id == "coinbasepro":
                    time.sleep(0.08)
                if loud:
                    print(f"got {symbol} on {exchange} in {time.time()-s:.2f}s")
                return resp
            except ccxt.RateLimitExceeded:
                print("RateLimitExceeded")
                try_again = True
                count += 1
                time.sleep(5)
        return {}

    def getMultipleSymbols(self, exchange, symbols):
        bulk = exchange.fetchTickers(symbols)
        for symbol in bulk:
            self.props[symbol][exchange] = bulk[symbol]
        return self.props

    def divideSymbols(self, exchange, symbols):
        """
        for exchanges that cant fetch all at once, divide up for each
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
            print(f"'{x}': ", end="")
            for exc in dic[x]:
                print(f"{exc}: " + "{ ... }")

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
    def propagate(self):
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

        for exchange in self.idynamics:
            if exchange.has["fetchTickers"]:
                print(f"quick {exchange}")
                self.getMultipleSymbols(exchange, self.idynamics[exchange])

            elif exchange.has["fetchTicker"]:
                print(f"slow {exchange} ...")
                inter = self.divideSymbols(exchange, self.idynamics[exchange])
                # merge inter into self.props
                self.mergeProps(inter, self.props)

        # pprint(self.props)
        print(f"data makes sense: {self.verify(test=self.props, sure=self.dynamics)}")


if __name__ == "__main__":
    pricer = Pricer()
    pricer.propagate()
    print(f"finished in {time.time()-start:.2f}s")