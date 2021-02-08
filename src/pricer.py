import asyncio
import json
import threading
import time
from pprint import pprint
from re import sub
from types import coroutine

import ccxt
import websockets

import hive

key = open("keys/cryptocompare").read().strip()

cc_aliases = {
    "coinbasepro": "Coinbase",
    "binance": "Binance",
    "binanceus": "binanceusa",
    "okcoin": "OKCoin",
    "huobipro": "HuobiPro",
    "bitstamp": "Bitstamp",
    "bittrex": "BitTrex",
    "bithumb": "Bithumb",
    "kraken": "Kraken",
    "bitfinex": "Bitfinex",
    "kucoin": "Kucoin",
}


def createSingleSub(args):
    """
    Args must be in format [{type}, {exchange}, {base}, {quote}]
    Ex (fetch ticker for BTC-USD on Coinbase): [2, "Coinbase", "BTC", "USD"]
    https://min-api.cryptocompare.com/documentation/websockets
    """
    return "~".join([str(i) for i in args])


def createAllSubs(commons):
    """
    Create list of subscriptions for a commons dict
    """
    subs = []
    for symbol in commons:
        for exchange in commons[symbol]:
            if exchange.id in cc_aliases:
                subs.append(
                    createSingleSub(
                        [
                            2,
                            cc_aliases[exchange.id],
                            symbol.split("/")[0],
                            symbol.split("/")[1],
                        ]
                    )
                )
            else:
                print(
                    f"ticker {symbol} not supported for {exchange.name} on cryptocompare"
                )
    print(f"creating {len(subs)} subs")
    return subs


async def checkData(subscriptions):
    uri = f"wss://streamer.cryptocompare.com/v2?api_key={key}"
    async with websockets.connect(uri) as websocket:
        await websocket.send(
            json.dumps(
                {
                    "action": "SubAdd",
                    "subs": subscriptions,
                }
            )
        )
        while True:
            greeting = await websocket.recv()
            pprint(json.loads(greeting))


async def main():
    h = hive.Hive()
    commons = h.getDynamicCommons()
    subs = createAllSubs(commons)
    asyncio.ensure_future(checkData(subs))
    print("holding 60")
    await asyncio.sleep(60)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
