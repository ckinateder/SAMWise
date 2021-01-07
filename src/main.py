import ccxt
import time
import sys
from pprint import pprint
# define watched symbols


class Spatial:
    def __init__(self):
        self.watch = ['BTC/USD', 'ETH/BTC', 'ETH/USD',
                      'LTC/USD', 'LTC/ETH',
                      'LTC/BTC', 'XRP/ETH', 'XRP/USD',
                      'ETC/BTC', 'BCH/USD', 'ETC/USD']

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

    def getSpread(self):
        # get tickers for the watched symbols
        before = time.time()
        all_responses = {
            'kraken': self.kraken.fetch_tickers(self.watch),
            'bittrex': self.bittrex.fetch_tickers(self.watch)
        }
        print('Recived from {} in {:.3f} s'.format(
            ', '.join(all_responses.keys()), time.time()-before))

        for symbol in self.watch:
            print('For {}:'.format(symbol))
            low = all_responses['kraken'][symbol]['ask']
            high = all_responses['kraken'][symbol]['ask']
            spread = 0
            for exchange in all_responses:
                ask = all_responses[exchange][symbol]['ask']
                print('\t{}: {}'.format(exchange,
                                        ask))
                if ask > high:
                    high = ask
                elif ask < low:
                    low = ask
            spread = high-low
            print('Spread (w/fees): {:.5f}'.format(spread*(1-(0.0025*2))))


if __name__ == '__main__':
    tester = Spatial()
    tester.getSpread()
