import ccxt
import time
from datetime import datetime
import sys
import logging
from pprint import pprint
import multiprocessing
# define watched symbols
detail = 'logs/' + \
    datetime.now().strftime("%m-%d-%Y_%H-%M-%S")+'.log'
logging.basicConfig(format='%(asctime)s: %(message)s',
                    filename=detail, level=logging.INFO)


class Bouncer:
    def __init__(self, symbol):
        self.symbol = symbol  # ,
        # 'LTC/USD', 'XRP/USD',
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
            self.binanceus: self.binanceus.fetch_ticker(self.symbol),
            self.bittrex: self.bittrex.fetch_ticker(self.symbol),
            self.kraken: self.kraken.fetch_ticker(self.symbol)
        }
        # print('Recived from {} in {:.3f} s'.format(
        #    ', '.join(all_responses.keys()), time.time()-before))
        return all_responses

    def getSpread(self, responses=None):
        # get tickers for the watched symbols and return exchanges and spread
        if responses == None:
            responses = self.getWatched()

        print('/'+'-'*55+datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f"))
        print('For {}:'.format(self.symbol))

        spread = 0

        low = responses[self.binanceus]['ask']
        high = responses[self.binanceus]['ask']
        for exchange in responses:
            ask = responses[exchange]['ask']
            print('\t{}: {}'.format(exchange,
                                    ask))
            if ask > high:
                high = ask
            elif ask < low:
                low = ask
        spread = high-low
        print(
            'Spread (w/~fees): {:.5f} {}'.format(spread*(1-(0.0025*2)), self.symbol[4:]), end=' ')

        # find buy
        if low == responses[self.binanceus]['ask']:
            buy = self.binanceus
        elif low == responses[self.bittrex]['ask']:
            buy = self.bittrex
        elif low == responses[self.kraken]['ask']:
            buy = self.kraken
        # find sell
        if high == responses[self.binanceus]['ask']:
            sell = self.binanceus
        elif high == responses[self.bittrex]['ask']:
            sell = self.bittrex
        elif high == responses[self.kraken]['ask']:
            sell = self.kraken

        print('(buy on {}, sell on {})'.format(buy.name, sell.name))
        return spread, buy, sell, low, high

    def handleTransaction(self, quote_amount, buy_ex, sell_ex, low, high):
        # creating processes
        print('Creating buy order on {} for {} {} at {}'.format(
            buy_ex, low/quote_amount, self.symbol, low))
        buying = multiprocessing.Process(
            target=buy_ex.create_limit_buy_order, args=(self.symbol, low/quote_amount, low))
        print('Creating sell order on {} for {} {} at {}'.format(
            sell_ex, high/quote_amount, self.symbol, high))
        selling = multiprocessing.Process(
            target=sell_ex.create_limit_sell_order, args=(self.symbol, high/quote_amount, high))

        logging.info('Trades initiated')
        # starting process 1
        buying.start()
        # starting process 2
        selling.start()

        # wait until process 1 is finished
        buying.join()
        # wait until process 2 is finished
        selling.join()
        logging.info('Trades completed')

        binanceus_balances = self.binanceus.fetch_balance()
        bittrex_balances = self.bittrex.fetch_balance()
        # kraken_balances = self.kraken.fetch_balance()
        logging.info('Balances fetched')

        logging.info('Bittrex balances - [{}: {}, {}: {}]'.format(self.symbol[:3], bittrex_balances['free']
                                                                  [self.symbol[:3]], self.symbol[4:], bittrex_balances['free'][self.symbol[4:]]))
        logging.info('Binance balances - [{}: {}, {}: {}]'.format(self.symbol[:3], binanceus_balances['free']
                                                                  [self.symbol[:3]], self.symbol[4:], binanceus_balances['free'][self.symbol[4:]]))

        return 'Done'

    def performOneArbitrage(self, quote_amount):
        binanceus_balances = self.binanceus.fetch_balance()
        bittrex_balances = self.bittrex.fetch_balance()
        # kraken_balances = self.kraken.fetch_balance()

        logging.info('Bittrex balances - [{}: {}, {}: {}]'.format(self.symbol[:3], bittrex_balances['free']
                                                                  [self.symbol[:3]], self.symbol[4:], bittrex_balances['free'][self.symbol[4:]]))
        logging.info('Binance balances - [{}: {}, {}: {}]'.format(self.symbol[:3], binanceus_balances['free']
                                                                  [self.symbol[:3]], self.symbol[4:], binanceus_balances['free'][self.symbol[4:]]))

        print('Bittrex balances - [{}: {}, {}: {}]'.format(self.symbol[:3], bittrex_balances['free']
                                                           [self.symbol[:3]], self.symbol[4:], bittrex_balances['free'][self.symbol[4:]]))
        print('Binance balances - [{}: {}, {}: {}]'.format(self.symbol[:3], binanceus_balances['free']
                                                           [self.symbol[:3]], self.symbol[4:], binanceus_balances['free'][self.symbol[4:]]))
        # print('Kraken balances - [{}: {}, {}: {}]'.format(symbol[:3], kraken_balances['free']
        #                                                  [symbol[:3]], symbol[4:], kraken_balances['free'][symbol[4:]]))
        markets = self.getWatched()
        spread, buy_ex, sell_ex, low, high = self.getSpread(markets)
        '''
        if buy_ex.fetch_balance()['free'][symbol[4:]] > quote_amount and sell_ex.fetch_balance()['free'][symbol[:3]] > high/quote_amount:
            self.handleTransaction(symbol, quote_amount,
                                   buy_ex, sell_ex, low, high)
        '''


if __name__ == '__main__':
    watch = ['BTC/USD', 'ETH/USD']
    btcer = Bouncer(watch[0])
    ether = Bouncer(watch[1])
    # tester.performOneArbitrage(10)
    while True:
        btcer.getSpread()
        ether.getSpread()
        print()
        time.sleep(1)
