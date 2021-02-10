import asyncio, aiohttp
import json
import threading
import time
from pprint import pformat, pprint

import ccxt
import requests
from bs4 import BeautifulSoup

from hive import Hive

alls = {}


PROPS = {}


async def getOneSymbol(exchange, symbol):
    s = time.time()
    x = exchange.fetchTicker(symbol)
    if exchange.id == "coinbasepro":
        time.sleep(0.08)
    print(f"got {symbol} symbols on {exchange} in {time.time()-s:.2f}s")
    PROPS[symbol].append({exchange: x})


async def divideSymbols(exchange, symbols):
    tasks = []
    for x in symbols:
        tasks.append(asyncio.ensure_future(getOneSymbol(exchange, x)))
    await asyncio.gather(*tasks, return_exceptions=True)


# get slugs
async def propagate():
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
    """
    h = Hive()
    dynamics = h.getDynamicCommons()
    idynmaics = h.transpose(dynamics)
    # set keys
    for key in list(dynamics.keys()):
        PROPS[key] = []

    # pprint(idynmaics)
    # fetch for ecah
    for x in idynmaics:
        if x.has["fetchTickers"]:
            print(f"quick {x}")
            y = x.fetchTickers(idynmaics[x])
            for z in y:
                PROPS[z].append({x: y[z]})
        elif x.has["fetchTicker"]:
            print(f"slow {x}")
            await divideSymbols(x, idynmaics[x])
    pprint(PROPS)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(propagate())
