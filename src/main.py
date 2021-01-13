import time
from datetime import datetime
import sys
import logging
import multiprocessing
import pandas as pd
import ccxt
from termcolor import colored
from pprint import pformat, pprint

__author__ = 'Calvin Kinateder'
__email__ = 'calvinkinateder@gmail.com'

# define watched symbols
detail = 'logs/detail/' + \
    datetime.now().strftime("%m-%d-%Y_%H-%M")+'.log'
logging.basicConfig(format='%(asctime)s: %(message)s',
                    filename=detail, level=logging.INFO)

logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


class Bouncer:
    def __init__(self, symbol, quote_order_size):
        '''
        Create exchanges.
        '''
        self.start_time = time.time()
        self.symbol = symbol  # ,
        self.base_coin = symbol.split('/')[0]
        self.quote_coin = symbol.split('/')[1]
        self.quote_order_size = quote_order_size
        self.pro_filename = 'logs/'+self.base_coin+'-'+self.quote_coin+'.csv'
        self.trades_filename = 'logs/trades/'+datetime.now().strftime("%m-%d-%Y_%H-%M") + '_' + \
            self.base_coin+'-'+self.quote_coin + '_trades.csv'
        self.threshold = 0.009  # for trades

        # mark which balance section to look at
        self.section = 'total'

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
        exchanges_str = ''
        for i in range(0, len(self.exchanges)-1):
            exchanges_str += self.exchanges[i].name+', '
        exchanges_str += 'and '+self.exchanges[-1].name
        logging.info('Created Bouncer for {} investing {} {}.\nActive on {}\nThreshold: {}\n'.format(
            self.symbol, self.quote_order_size, self.quote_coin, exchanges_str, self.threshold))

        # init balances
        self.balances = dict()
        self.net = 0

        self.start_total_base_amount, self.start_total_quote_order_size = self.updateBalances(
            loud=False)

        logging.info('Starting base amount [{:.8f} {}, {:.4f} {}]\n'.format(
            self.start_total_base_amount, self.base_coin, self.start_total_quote_order_size, self.quote_coin))

        # set up file for logging
        self.pro_headers = ['Date', 'Symbol', 'Investment', 'High', 'Low', 'Adjusted Spread',
                            'Adj. Spread after fees', 'Fees', 'Profitable', 'Sell exchange', 'Buy exchange']
        self.pro_frame = pd.DataFrame(columns=self.pro_headers)

        # set up trades file
        self.trades_headers = ['Date', 'Symbol',
                               'Side', 'Price', 'Exchange', 'Net Gain (%)']
        self.trades = pd.DataFrame(columns=self.trades_headers)

    def colorGood(self, strr):
        return colored(strr, 'green')

    def colorEh(self, strr):
        return colored(strr, 'yellow')

    def colorBad(self, strr):
        return colored(strr, 'red')

    def colorHigh(self, strr):
        return colored(strr, 'cyan')

    def colorLow(self, strr):
        return colored(strr, 'magenta')

    def colorProfit(self, number):
        '''
        Color code a number.
        '''
        number = round(number, 5)
        try:
            if number > 0:
                form = self.colorGood(number)
            elif number < 0:
                form = self.colorBad(number)
            else:
                form = self.colorEh(number)
        except:
            logging.warning('Couldn\'t colorize')
        return form

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
        logging.info('[For {}]:'.format(self.symbol))

        spread = 0

        low = responses[self.binanceus]['ask']
        high = responses[self.binanceus]['ask']

        for exchange in responses:
            ask = responses[exchange]['ask']
            if ask > high:
                high = ask
            elif ask < low:
                low = ask

        # find buy and sell and log
        for exchange in self.exchanges:
            ask = responses[exchange]['ask']

            logstr = '\t{}: {}'.format(exchange, ask)
            if low == responses[exchange]['ask']:
                buy = exchange
                logstr = self.colorLow('\t{}: {}'.format(buy, ask))
            elif high == responses[exchange]['ask']:
                sell = exchange
                logstr = self.colorHigh('\t{}: {}'.format(sell, ask))
            logging.info(logstr)

        spread = (self.quote_order_size/high)*(high-low)

        fees = (buy.calculateFee(self.symbol, 'limit', 'buy', self.quote_order_size/low, low, takerOrMaker='taker', params={})['cost'] +
                sell.calculateFee(self.symbol, 'limit', 'sell', self.quote_order_size/high, high, takerOrMaker='taker', params={})['cost'])

        if spread - fees > self.threshold:
            msg = self.colorGood(
                ' '*53+'found profitable pair ****\n' + '[PROFITABLE]')
            profitable = True
        else:
            msg = self.colorBad('[NOT PROFITABLE]')
            profitable = False
        logging.info(
            '{} Adjusted Spread: {} {} (after fees: {} {})\n(buy on {}, sell on {})'.format(msg, self.colorProfit(spread), self.quote_coin, self.colorProfit(spread-fees), self.quote_coin, self.colorLow(buy.name), self.colorHigh(sell.name)))

        # if self.anyOpen():
        #    logging.info(self.colorEh('Note: currently open trades.'))

        new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S"), self.symbol, self.quote_order_size,
                   high, low, spread, spread-fees, fees, profitable, sell.name, buy.name]
        self.pro_frame.loc[len(self.pro_frame)] = new_row
        self.pro_frame.to_csv(path_or_buf=self.pro_filename)

        return spread, buy, sell, low, high, profitable, fees

    def updateBalances(self, loud=True):
        '''
        Log balances to file and total base and quote amounts.
        '''
        for exchange in self.exchanges:
            self.balances[exchange] = exchange.fetch_balance()
        if loud:
            for exchange in self.exchanges:
                logging.info(
                    '{} balance response - {}'.format(exchange, pformat(self.balances[exchange])))

        self.section = 'total'

        total_base_amount = 0
        for exchange in self.exchanges:
            if self.base_coin in self.balances[exchange][self.section]:
                total_base_amount += self.balances[exchange][self.section][self.base_coin]
            else:
                self.balances[exchange][self.section][self.base_coin] = 0

        total_quote_order_size = 0
        for exchange in self.exchanges:
            if self.quote_coin in self.balances[exchange][self.section]:
                total_quote_order_size += self.balances[exchange][self.section][self.quote_coin]
            else:
                self.balances[exchange][self.section][self.quote_coin] = 0
        if loud:
            for exchange in self.exchanges:
                logging.info('\t{} balances ({}) - [{}: {}, {}: {}]'.format(exchange, self.section, self.base_coin, self.balances[exchange][self.section]
                                                                            [self.base_coin], self.quote_coin, self.balances[exchange][self.section][self.quote_coin]))

        # bittrex_string, binance_string, kraken_string, coinbase_pro_string
        return total_base_amount, total_quote_order_size

    def updateNet(self, loud=False):
        '''
        Returns self.net as a percent and updates.
        '''
        base, quote = self.updateBalances(loud)
        if self.start_total_base_amount == 0 or self.start_total_quote_order_size == 0:
            self.net = 0
        else:
            self.net = 0
        return self.net

    def inititalizeBalances(self):
        '''
        Optional function used to initialize the balances buying the crypto needed in each exchange.
        '''
        for exchange in self.exchanges:
            if exchange.fetch_balance()[self.section] >= self.quote_order_size/2:
                exchange.create_market_buy_order(
                    self.symbol, self.quote_order_size/2)
            else:
                logging.warning(
                    'Insufficient balance on {} to set up balance'.format(exchange.name))
        return False

    def anyOpen(self, exchange=None):
        if exchange == None:
            for i in self.exchanges:
                x = i.fetch_open_orders(self.symbol)
                if len(x) > 0:
                    return True
        else:
            if len(exchange.fetch_open_orders(self.symbol)) > 0:
                return True

        return False

    def cleanup(self):
        logging.info('Cleaning up for {}...'.format(self.symbol))
        responses = self.getWatched()
        self.updateBalances(loud=False)

        for exchange in responses:
            ask = responses[exchange]['ask']
            # sell remaining
            remaining = float(
                self.balances[exchange][self.section][self.base_coin])
            if remaining > 0 and not self.anyOpen(exchange):
                try:
                    logging.info('Selling off {} {} on {}'.format(
                        remaining, self.base_coin, exchange.name))
                    exchange.create_limit_sell_order(
                        self.symbol, remaining, ask)
                except Exception as e:
                    logging.warning(
                        'Error in selling off {} {} on {}: {}'.format(remaining, self.base_coin, exchange.name, e))
            else:
                logging.info(
                    'No need to sell, no balance in {} on {}'.format(self.base_coin, exchange.name))

        logging.info('Final balances:')
        base, quote = self.updateBalances(loud=False)
        logging.info('Sums: [{:.8f} {}, {:.3f} {}]'.format(
            base, self.base_coin, quote, self.quote_coin))
        self.updateNet()
        logging.info('Net: {}%'.format(self.colorProfit(self.net)))
        logging.info('Done!\n')

    def handleTransaction(self, buy_ex, sell_ex, low, high):
        '''
        Places the arbitrage transactions simultaneously.
        '''
        # creating processes
        logging.info('Creating buy order on {} for {} {} at {}'.format(
            buy_ex, self.quote_order_size/low, self.symbol, low))
        buy_ex.create_limit_buy_order(
            self.symbol, self.quote_order_size/low, low)
        new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                   self.symbol, 'buy', low, buy_ex.name, self.net]
        self.trades.loc[len(self.trades)] = new_row

        logging.info('Creating sell order on {} for {} {} at {}'.format(
            sell_ex, self.quote_order_size/high, self.symbol, high))
        sell_ex.create_limit_sell_order(
            self.symbol, self.quote_order_size/high, high)
        new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                   self.symbol, 'sell', high, sell_ex.name, self.net]
        self.trades.loc[len(self.trades)] = new_row

        logging.info('Trades initiated')

        # perform calculations for logging

        self.updateNet()

        # recalculate
        self.updateNet()

        self.trades.to_csv(path_or_buf=self.trades_filename)
        logging.info('Trades completed')

        logging.info('Balances fetched')
        self.updateBalances(loud=False)

        return 'Done'

    def arbitrate(self):
        '''
        Calculate spread and buy on low and sell on high.
        '''
        markets = self.getWatched()
        spread, buy_ex, sell_ex, low, high, profitable, fees_applied = self.getSpread(
            markets)

        if profitable:
            self.updateBalances(loud=False)
            quote_balance = self.balances[buy_ex][self.section][self.quote_coin]
            base_balance = self.balances[sell_ex][self.section][self.base_coin]

            if self.anyOpen(buy_ex) or self.anyOpen(sell_ex):
                logging.warning(self.colorBad(
                    'Open orders - taking no action.'))
            elif quote_balance >= self.quote_order_size and base_balance >= self.quote_order_size/high:
                self.handleTransaction(
                    buy_ex, sell_ex, low, high)
            else:
                logging.warning(self.colorBad('Balances not sufficient to trade - [{} {} on {}, {} {} on {}]\n(needed [{} {} on {}, {} {} on {}])'.format(
                    quote_balance, self.quote_coin, buy_ex.name, base_balance, self.base_coin, sell_ex.name,
                    self.quote_order_size, self.quote_coin, buy_ex.name, self.quote_order_size/high, self.base_coin, sell_ex.name)))


if __name__ == '__main__':
    watch = ['BTC/USD', 'ETH/USD', 'XRP/USD', 'BCH/USD', 'LTC/USD', 'LINK/USD']

    currencies = list()
    if len(sys.argv) > 1:
        for i in range(1, len(sys.argv), 2):
            currencies.append(Bouncer(sys.argv[i], float(sys.argv[i+1])))
    else:
        size = 15
        currencies = [Bouncer('BCH/USD', size)]

    while True:
        try:
            for i in currencies:
                # i.getSpread()
                i.arbitrate()
            time.sleep(2/len(sys.argv))
        except KeyboardInterrupt:
            logging.warning('\nQuitting\n')
            todo = input('Cleanup balances? (Y/n) ')
            if 'Y' in todo:
                for i in currencies:
                    i.cleanup()
            sys.exit(0)
