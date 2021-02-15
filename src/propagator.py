import ccxt
from tqdm import tqdm
from tqdm.std import trange
from helper import *


class Propagtor:
    def __init__(self):
        pass

    def _rateLimit(self, waittime):
        for interval in trange(
            waittime * 1000,
            leave=False,
            desc="timer",
            dynamic_ncols=True,
            position=1,
        ):
            time.sleep(0.001)

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
        resp = exchange.fetchTickers(tickers)
        trans = self._transposeBatchTickers(resp, exchange)
        return trans

    def _divideBatchTickers(self, exchange, tickers):
        """
        Divide a bunch of tickers between one exchange
        """
        inter = {}
        for symbol in tickers:
            single = self._getSingleSymbol(exchange, symbol)
            if single:
                inter[symbol] = {exchange: single}
            self.cycle_bar.update(1)
        return inter

    def _getSingleSymbol(self, exchange, ticker, depth=0):
        """
        Recursive function to get a single symbol and handlle errors
        """
        waittime = 4
        response = None
        if depth <= 2:  # don't waste too much time
            try:
                response = exchange.fetchTicker(ticker)
                if exchange.id == "coinbasepro":
                    time.sleep(0.1)
            except ccxt._rateLimitExceeded:
                tqdm.write(
                    colorBad(
                        f"Rate limit exceeded on {exchange} for {ticker} ... trying again in {waittime}"
                    )
                )
                self._rateLimit(waittime)
                response = self._getSingleSymbol(exchange, ticker, depth + 1)
        else:
            tqdm.write(
                colorBad(f"Rate limit exceeded on {exchange} for {ticker} ... skipping")
            )
        return response

    def propagate(self, idynamics):
        """
        Build one giant dictionary of dictionaries of all data recieved.
        """
        exchanges = list(idynamics.keys())
        tqdm.write(colorEh("Fetching tickers ... "))
        props = {}
        total = 0
        for i in idynamics:
            total += len(idynamics[i])
        self.cycle_bar = tqdm(
            total=total, leave=False, unit="exc", dynamic_ncols=True, desc="cycle"
        )
        for exchange in exchanges:
            tqdm.write(f"Querying {exchange.name} ...")
            if exchange.has["fetchTickers"]:
                ###
                # fetch tickers and merge into props
                resp = self._getBatchTickers(exchange, idynamics[exchange])
                props = self._mergeProps(resp, props)
                ###
                self.cycle_bar.update(len(idynamics[exchange]))

            elif exchange.has["fetchTicker"]:
                inter = {}
                ###
                # fetch ticker for each and merge into props
                inter = self._divideBatchTickers(exchange, idynamics[exchange])
                props = self._mergeProps(inter, props)
                ###
        self.cycle_bar.close()
        # pprint(props)
        return props
