import ccxt
import time
from datetime import datetime
import sys
from pprint import pprint
# define watched symbols


class Spatial:
    def __init__(self):
        self.watch = ['BTC/USD', 'ETH/USD']  # ,
        #'LTC/USD', 'XRP/USD',
        # 'BCH/USD', 'ETC/USD']

        # load bittrex key
        bittrex_key = open('keys/bittrex_public').read().strip()
        bittrex_secret = open('keys/bittrex_private').read().strip()

        # create bittrex exchange
        self.bittrex = ccxt.bittrex({
            'apiKey': bittrex_key,
            'secret': bittrex_secret,
        })

        # load kraken key
        kraken_key = open('keys/kraken_public').read().strip()
        kraken_secret = open('keys/kraken_private').read().strip()

        # create kraken exchange
        self.kraken = ccxt.kraken({
            'apiKey': kraken_key,
            'secret': kraken_secret,
        })

    def getSpread(self, symbol, responses):
        # get tickers for the watched symbols

        print('For {}:'.format(symbol))

        spread = 0
        low = responses['kraken'][symbol]['ask']
        high = responses['kraken'][symbol]['ask']
        for exchange in responses:
            ask = responses[exchange][symbol]['ask']
            print('\t{}: {}'.format(exchange,
                                    ask))
            if ask > high:
                high = ask
            elif ask < low:
                low = ask
        spread = high-low
        print(
            'Spread (w/fees): {:.5f} {}'.format(spread*(1-(0.0025*2)), symbol[4:]), end=' ')

        if low == responses['kraken'][symbol]['ask']:
            buy = 'kraken'
            sell = 'bittrex'
        else:
            buy = 'bittrex'
            sell = 'kraken'
        print('(buy on {}, sell on {})'.format(buy, sell))
        return spread, buy, sell

    def getAllSpreads(self):
        before = time.time()
        all_responses = {
            'kraken': self.kraken.fetch_tickers(self.watch),
            'bittrex': self.bittrex.fetch_tickers(self.watch)
        }
        print('Recived from {} in {:.3f} s'.format(
            ', '.join(all_responses.keys()), time.time()-before))

        for symbol in self.watch:
            self.getSpread(symbol, all_responses)


if __name__ == '__main__':
    tester = Spatial()
    for i in range(1, 11):
        print('-'*56+datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f"))
        tester.getAllSpreads()
        time.sleep(1)
