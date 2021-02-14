import ccxt
from tqdm import tqdm
from tqdm.std import trange
from helper import *


def rateLimit(waittime):
    for interval in trange(
        waittime * 1000,
        leave=False,
        desc="timer",
        dynamic_ncols=True,
        position=1,
    ):
        time.sleep(0.001)


def mergeProps(one, two):
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


def transposeBatchTickers(original, exchange):
    """
    Flip a dictionary of dictionaries
    """
    inverted = {}
    for symbol in original.values():
        act = symbol["symbol"]
        inverted[act] = {exchange: symbol}

    return inverted


def getBatchTickers(exchange, tickers):
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
    trans = transposeBatchTickers(resp, exchange)
    return trans


def divideBatchTickers(exchange, tickers):
    """
    Divide a bunch of tickers between one exchange
    """
    inter = {}
    for symbol in tickers:
        single = getSingleSymbol(exchange, symbol)
        if single:
            inter[symbol] = {exchange: single}
    return inter


def getSingleSymbol(exchange, ticker, depth=0):
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
        except ccxt.RateLimitExceeded:
            tqdm.write(
                colorBad(
                    f"Rate limit exceeded on {exchange} for {ticker} ... trying again in {waittime}"
                )
            )
            rateLimit(waittime)
            response = getSingleSymbol(exchange, ticker, depth + 1)
    else:
        tqdm.write(
            colorBad(f"Rate limit exceeded on {exchange} for {ticker} ... skipping")
        )

    return response


def propagate(idynamics):
    """
    Build one giant dictionary of dictionaries of all data recieved.
    """
    exchanges = list(idynamics.keys())
    tqdm.write(colorEh("Fetching tickers ... "))
    props = {}
    total = 0
    for i in idynamics:
        total += len(idynamics[i])
    with tqdm(
        total=total, leave=False, unit="exc", dynamic_ncols=True, desc="cycle"
    ) as total_bar:
        for exchange in exchanges:
            if exchange.has["fetchTickers"]:
                ###
                # fetch tickers and merge into props
                resp = getBatchTickers(exchange, idynamics[exchange])
                props = mergeProps(resp, props)
                ###
                total_bar.update(len(idynamics[exchange]))

            elif exchange.has["fetchTicker"]:
                inter = {}
                ###
                # fetch ticker for each and merge into props
                inter = divideBatchTickers(exchange, idynamics[exchange])
                props = mergeProps(inter, props)
                ###
                total_bar.update(1)

    # pprint(props)
    return props
