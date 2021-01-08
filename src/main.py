import ccxt
import time
from datetime import datetime
import sys
from pprint import pprint
import multiprocessing
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

        # load binanceus key
        binanceus_key = open('keys/binanceus_public').read().strip()
        binanceus_secret = open('keys/binanceus_private').read().strip()

        # create binanceus exchange
        self.binanceus = ccxt.binanceus({
            'apiKey': binanceus_key,
            'secret': binanceus_secret,
        })
        # load kraken key
        kraken_key = open('keys/kraken_public').read().strip()
        kraken_secret = open('keys/kraken_private').read().strip()

        # create kraken exchange
        self.kraken = ccxt.kraken({
            'apiKey': kraken_key,
            'secret': kraken_secret,
        })

    def getWatched(self):
        before = time.time()
        all_responses = {
            self.binanceus: self.binanceus.fetch_tickers(self.watch),
            self.bittrex: self.bittrex.fetch_tickers(self.watch),
            # 'kraken': self.kraken.fetch_tickers(self.watch)
        }
        # print('Recived from {} in {:.3f} s'.format(
        #    ', '.join(all_responses.keys()), time.time()-before))
        return all_responses

    def getSpread(self, symbol, responses):
        # get tickers for the watched symbols and return exchanges and spread

        print('/'+'-'*55+datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f"))
        print('For {}:'.format(symbol))

        spread = 0
        low = responses[self.binanceus][symbol]['ask']
        high = responses[self.binanceus][symbol]['ask']
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
            'Spread (w/~fees): {:.5f} {}'.format(spread*(1-(0.0025*2)), symbol[4:]), end=' ')

        # find buy
        if low == responses[self.binanceus][symbol]['ask']:
            buy = self.binanceus
        elif low == responses[self.bittrex][symbol]['ask']:
            buy = self.bittrex
        # elif low == responses['kraken'][symbol]['ask']:
        #    buy = self.kraken
        # find sell
        if high == responses[self.binanceus][symbol]['ask']:
            sell = self.binanceus
        elif high == responses[self.bittrex][symbol]['ask']:
            sell = self.bittrex
        # elif high == responses['kraken'][symbol]['ask']:
        #    sell = self.kraken

        print('(buy on {}, sell on {})'.format(buy.name, sell.name))
        return spread, buy, sell, low, high

    def getAllSpreads(self):
        all_responses = self.getWatched()

        for symbol in self.watch:
            self.getSpread(symbol, all_responses)

    def handleTransaction(self, symbol, quote_amount, buy_ex, sell_ex, low, high):
        # creating processes
        buying = multiprocessing.Process(
            target=buy_ex.create_limit_buy_order, args=(symbol, quote_amount/low, low))
        selling = multiprocessing.Process(
            target=sell_ex.create_limit_sell_order, args=(symbol, quote_amount, high))

        # starting process 1
        buying.start()
        # starting process 2
        selling.start()

        # wait until process 1 is finished
        buying.join()
        # wait until process 2 is finished
        selling.join()
        return 'Done'

    def performArbitrage(self, symbol, quote_amount):
        binanceus_balances = self.binanceus.fetch_balance()
        bittrex_balances = self.bittrex.fetch_balance()
        #kraken_balances = self.kraken.fetch_balance()

        print('Bittrex balances - [{}: {}, {}: {}]'.format(symbol[:3], bittrex_balances['free']
                                                           [symbol[:3]], symbol[4:], bittrex_balances['free'][symbol[4:]]))
        print('Binance balances - [{}: {}, {}: {}]'.format(symbol[:3], binanceus_balances['free']
                                                           [symbol[:3]], symbol[4:], binanceus_balances['free'][symbol[4:]]))
        # print('Kraken balances - [{}: {}, {}: {}]'.format(symbol[:3], kraken_balances['free']
        #                                                  [symbol[:3]], symbol[4:], kraken_balances['free'][symbol[4:]]))
        markets = self.getWatched()
        spread, buy_ex, sell_ex, low, high = self.getSpread(symbol, markets)
        #self.handleTransaction(symbol, quote_amount, buy_ex, sell_ex, low, high)


if __name__ == '__main__':
    tester = Spatial()
    tester.performArbitrage(tester.watch[1], 10)
    for i in range(1, 11):
        tester.getAllSpreads()
        time.sleep(1)
