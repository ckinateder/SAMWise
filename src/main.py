import time
from datetime import datetime
import sys
import logging
import multiprocessing
import ccxt
from pprint import pformat, pprint
# define watched symbols
detail = 'logs/' + \
    datetime.now().strftime("%m-%d-%Y_%H-%M-%S")+'.log'
logging.basicConfig(format='%(asctime)s: %(message)s',
                    filename=detail, level=logging.INFO)

logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


class Bouncer:
    def __init__(self, symbol):
        '''
        Create exchanges.
        '''
        self.symbol = symbol  # ,
        self.base_coin = symbol[:3]
        self.quote_coin = symbol[4:]
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

        # load coinbase_pro key
        coinbase_pro_key = open('keys/coinbase_pro_public').read().strip()
        coinbase_pro_secret = open('keys/coinbase_pro_private').read().strip()
        coinbase_pro_passphrase = open(
            'keys/coinbase_pro_passphrase').read().strip()

        # create coinbase_pro exchange
        self.coinbase_pro = ccxt.coinbasepro({
            'apiKey': coinbase_pro_key,
            'secret': coinbase_pro_secret,
            'password': coinbase_pro_passphrase,
        })

        self.start_total_base_amount, self.start_total_quote_amount = self.getBalances()
        logging.info('Starting base amount [{} {}, {} {}]'.format(
            self.start_total_base_amount, self.base_coin, self.start_total_quote_amount, self.quote_coin))

    def getWatched(self):
        '''
        Get responses for each exchange for self.symbol.
        '''
        before = time.time()
        all_responses = {
            self.binanceus: self.binanceus.fetch_ticker(self.symbol),
            self.bittrex: self.bittrex.fetch_ticker(self.symbol),
            self.kraken: self.kraken.fetch_ticker(self.symbol),
            self.coinbase_pro: self.coinbase_pro.fetch_ticker(self.symbol)
        }
        # logging.info('Recived from {} in {:.3f} s'.format(
        #    ', '.join(all_responses.keys()), time.time()-before))
        return all_responses

    def getSpread(self, responses=None):
        # get tickers for the watched symbols and return exchanges and spread
        if responses == None:
            responses = self.getWatched()

        logging.info(
            '/'+'-'*55+datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f"))
        logging.info('For {}:'.format(self.symbol))

        spread = 0

        low = responses[self.binanceus]['ask']
        high = responses[self.binanceus]['ask']
        for exchange in responses:
            ask = responses[exchange]['ask']
            logging.info('\t{}: {}'.format(exchange,
                                           ask))
            if ask > high:
                high = ask
            elif ask < low:
                low = ask

        # find buy
        if low == responses[self.binanceus]['ask']:
            buy = self.binanceus
        elif low == responses[self.bittrex]['ask']:
            buy = self.bittrex
        elif low == responses[self.kraken]['ask']:
            buy = self.kraken
        elif low == responses[self.coinbase_pro]['ask']:
            buy = self.coinbase_pro
        # find sell
        if high == responses[self.binanceus]['ask']:
            sell = self.binanceus
        elif high == responses[self.bittrex]['ask']:
            sell = self.bittrex
        elif high == responses[self.kraken]['ask']:
            sell = self.kraken
        elif high == responses[self.coinbase_pro]['ask']:
            sell = self.coinbase_pro

        spread = high-low
        logging.info(
            'Spread (w/~fees): {:.5f} {} (buy on {}, sell on {})'.format(spread*(1-(0.0025*2)), self.quote_coin, buy.name, sell.name))

        return spread, buy, sell, low, high

    def getBalances(self):
        '''
        Log balances to file and return string.
        '''
        binanceus_balances = self.binanceus.fetch_balance()
        bittrex_balances = self.bittrex.fetch_balance()
        kraken_balances = self.kraken.fetch_balance()
        coinbase_pro_balances = self.coinbase_pro.fetch_balance()

        logging.debug(
            '{} balance response - {}'.format(self.binanceus, pformat(binanceus_balances)))
        logging.debug(
            '{} balance response - {}'.format(self.bittrex, pformat(bittrex_balances)))
        logging.debug(
            '{} balance response - {}'.format(self.kraken, pformat(kraken_balances)))
        logging.debug('{} balance response - {}'.format(self.coinbase_pro,
                                                        pformat(coinbase_pro_balances)))

        section = 'total'

        bittrex_string = ('Bittrex balances ({}) - [{}: {}, {}: {}]'.format(section, self.base_coin, bittrex_balances[section]
                                                                            [self.base_coin], self.quote_coin, bittrex_balances[section][self.quote_coin]))
        binance_string = ('Binance US balances ({}) - [{}: {}, {}: {}]'.format(section, self.base_coin, binanceus_balances[section]
                                                                               [self.base_coin], self.quote_coin, binanceus_balances[section][self.quote_coin]))
        kraken_string = ('Kraken balances ({}) - [{}: {}, {}: {}]'.format(section, self.base_coin, kraken_balances[section]
                                                                          [self.base_coin], self.quote_coin, kraken_balances[section][self.quote_coin]))
        coinbase_pro_string = ('Coinbase Pro balances ({}) - [{}: {}, {}: {}]'.format(section, self.base_coin, coinbase_pro_balances[section]
                                                                                      [self.base_coin], self.quote_coin, coinbase_pro_balances[section][self.quote_coin]))
        logging.info(bittrex_string)
        logging.info(binance_string)
        logging.info(kraken_string)
        logging.info(coinbase_pro_string)

        total_base_amount = binanceus_balances[section][self.base_coin]+bittrex_balances[section][self.base_coin] + \
            kraken_balances[section][self.base_coin] + \
            coinbase_pro_balances[section][self.base_coin]
        total_quote_amount = binanceus_balances[section][self.quote_coin]+bittrex_balances[section][self.quote_coin] + \
            kraken_balances[section][self.quote_coin] + \
            coinbase_pro_balances[section][self.quote_coin]
        # bittrex_string, binance_string, kraken_string, coinbase_pro_string
        return total_base_amount, total_quote_amount

    def handleTransaction(self, quote_amount, buy_ex, sell_ex, low, high):
        '''
        Places the arbitrage transactions simultaneously.
        '''
        section = 'total'
        # creating processes
        logging.info('Creating buy order on {} for {} {} at {}'.format(
            buy_ex, low/quote_amount, self.symbol, low))
        buying = multiprocessing.Process(
            target=buy_ex.create_limit_buy_order, args=(self.symbol, low/quote_amount, low))
        logging.info('Creating sell order on {} for {} {} at {}'.format(
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

        logging.info('Balances fetched')
        self.getBalances()

        return 'Done'

    def performOneArbitrage(self, quote_amount):
        '''
        Calculate spread and buy on low and sell on high.
        '''
        self.getBalances()
        markets = self.getWatched()
        spread, buy_ex, sell_ex, low, high = self.getSpread(markets)

        '''
        if buy_ex.fetch_balance()[section][self.quote_coin] > quote_amount and sell_ex.fetch_balance()[section][self.base_coin] > high/quote_amount:
            self.handleTransaction(quote_amount,
                                   buy_ex, sell_ex, low, high)
        '''


if __name__ == '__main__':
    watch = ['BTC/USD', 'ETH/USD']
    btcer = Bouncer(watch[0])
    ether = Bouncer(watch[1])
    btcer.performOneArbitrage(10)
    ether.performOneArbitrage(10)
    while True:
        btcer.getSpread()
        ether.getSpread()
        time.sleep(1)
