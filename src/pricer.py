from re import sub
from types import coroutine
import websockets, asyncio, json, time
from pprint import pprint
import threading

key = open("keys/cryptocompare").read().strip()

cc_aliases = {
    "coinbasepro": "coinbase",
    "binance": "Binance",
    "binanceus": "binanceusa",
    "okcoin": "OKCoin",
    "huobipro": "HuobiPro",
    "bitstamp": "Bitstamp",
    "bittrex": "BitTrex",
    "bithumb": "Bithumb",
    "kraken": "Kraken",
    "bitfinex": "Bitfinex",
}


def createNewSub(args):
    return "~".join([str(i) for i in args])


def createAllSubs(commons):
    for sym in commons:
        pass


async def checkData():
    uri = f"wss://streamer.cryptocompare.com/v2?api_key={key}"
    async with websockets.connect(uri) as websocket:
        subscriptions = []
        subscriptions.append(createNewSub([2, "Coinbase", "BTC", "USD"]))

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
    asyncio.ensure_future(checkData())
    print("holding 10")
    await asyncio.sleep(10)


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())