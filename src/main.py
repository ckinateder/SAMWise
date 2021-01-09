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
    def __init__(self, symbol, quote_amount):
        '''
        Create exchanges.
        '''
        self.symbol = symbol  # ,
        self.base_coin = symbol[:3]
        self.quote_coin = symbol[4:]
        self.quote_amount = quote_amount
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

        # add to exchange list
        self.exchanges = [self.bittrex, self.binanceus,
                          self.kraken, self.coinbase_pro]

        logging.info('Created Bouncer for {} investing {} {}'.format(
            self.symbol, self.quote_amount, self.quote_coin))

        self.start_total_base_amount, self.start_total_quote_amount = self.getBalances()
        logging.info('Starting base amount [{} {}, {} {}]'.format(
            self.start_total_base_amount, self.base_coin, self.start_total_quote_amount, self.quote_coin))

    def getWatched(self):
        '''
        Get responses for each exchange for self.symbol.
        '''
        before = time.time()
        all_responses = dict()
        for exchange in self.exchanges:
            all_responses[exchange] = exchange.fetch_ticker(self.symbol)
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
        for exchange in self.exchanges:
            if low == responses[exchange]['ask']:
                buy = exchange
        # find sell
        for exchange in self.exchanges:
            if high == responses[exchange]['ask']:
                sell = exchange

        #spread = self.quote_amount/(high-low)

        spread = (self.quote_amount/high)*(high-low)

        fees = (buy.calculateFee(self.symbol, 'limit', 'buy', self.quote_amount/low, low, takerOrMaker='taker', params={})['cost'] +
                sell.calculateFee(self.symbol, 'limit', 'sell', self.quote_amount/high, high, takerOrMaker='taker', params={})['cost'])
        logging.info(
            '\tSpread: {:.5f} {} (after fees: {:.5f} {}) (buy on {}, sell on {})'.format(spread, self.quote_coin, spread-fees, self.quote_coin, buy.name, sell.name))

        return spread, buy, sell, low, high

    def getBalances(self):
        '''
        Log balances to file and total base and quote amounts.
        '''
        balances = dict()
        for exchange in self.exchanges:
            balances[exchange] = exchange.fetch_balance()

        for exchange in self.exchanges:
            logging.debug(
                '{} balance response - {}'.format(exchange, pformat(balances[exchange])))

        section = 'total'
        for exchange in self.exchanges:
            logging.debug('\t{} balances ({}) - [{}: {}, {}: {}]'.format(exchange, section, self.base_coin, balances[exchange][section]
                                                                         [self.base_coin], self.quote_coin, balances[exchange][section][self.quote_coin]))
        total_base_amount = 0
        for exchange in self.exchanges:
            total_base_amount += balances[exchange][section][self.base_coin]

        total_quote_amount = 0
        for exchange in self.exchanges:
            total_quote_amount += balances[exchange][section][self.quote_coin]

        # bittrex_string, binance_string, kraken_string, coinbase_pro_string
        return total_base_amount, total_quote_amount

    def handleTransaction(self, buy_ex, sell_ex, low, high):
        '''
        Places the arbitrage transactions simultaneously.
        '''
        # creating processes
        logging.info('Creating buy order on {} for {} {} at {}'.format(
            buy_ex, low/self.quote_amount, self.symbol, low))
        buying = multiprocessing.Process(
            target=buy_ex.create_limit_buy_order, args=(self.symbol, low/self.quote_amount, low))
        logging.info('Creating sell order on {} for {} {} at {}'.format(
            sell_ex, high/self.quote_amount, self.symbol, high))
        selling = multiprocessing.Process(
            target=sell_ex.create_limit_sell_order, args=(self.symbol, high/self.quote_amount, high))

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

    def performOneArbitrage(self):
        '''
        Calculate spread and buy on low and sell on high.
        '''
        self.getBalances()
        markets = self.getWatched()
        spread, buy_ex, sell_ex, low, high = self.getSpread(markets)

        '''
        if buy_ex.fetch_balance()[section][self.quote_coin] > quote_amount and sell_ex.fetch_balance()[section][self.base_coin] > high/quote_amount:
            self.handleTransaction(
                                   buy_ex, sell_ex, low, high)
        '''


if __name__ == '__main__':
    watch = ['BTC/USD', 'ETH/USD']
    btcer = Bouncer(watch[0], 1000)
    btcer.performOneArbitrage()
    while True:
        btcer.getSpread()
        time.sleep(1)
