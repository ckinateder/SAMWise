import logging
import multiprocessing
import sys
import time
from datetime import datetime
from os import path, listdir
from getpass import getpass
import operator

from collections import OrderedDict
from operator import getitem

import ccxt
import pandas as pd
from pprint import pformat, pprint

from crayon import *

__author__ = 'Calvin Kinateder'
__email__ = 'calvinkinateder@gmail.com'


class Bouncer:
    def __init__(self, symbol, quote_order_size, exchanges, initializeq=False, speedup=2, active=False, logging=True):
        '''
        Create the class.
        '''

        # mark which balance section to look at
        self.section = 'total'
        # precision to display quotes
        self.precision = ':.3f'
        # speedup is used to narrow the price gap to enable trades to finish faster.
        self.speedup = speedup
        self.exchanges = exchanges
        self.logging = True  # log to file?
        # check if symbol supported by all
        if symbol in self.getCommons():
            self.symbol = symbol
        else:
            print(
                'Symbol \'{}\' not supported by all platforms. Exiting ...'.format(symbol))
            sys.exit(0)

        self.active = active
        self.start_time = time.time()
        self.base_coin = symbol.split('/')[0]
        self.quote_coin = symbol.split('/')[1]
        self.quote_order_size = quote_order_size
        self.pro_filename = 'logs/'+self.base_coin+'-'+self.quote_coin+'.csv'
        self.trades_filename = 'logs/trades/'+datetime.now().strftime("%m-%d-%Y_%H-%M") + '_' + \
            self.base_coin+'-'+self.quote_coin + '_trades.csv'
        self.threshold = 0.009  # for trades
        exchanges_str = ''

        # set up file for logging
        self.pro_headers = ['Date', 'Symbol', 'Investment', 'High', 'Low', 'Adjusted Spread',
                            'Adj. Spread after fees', 'Fees', 'Profitable', 'Sell exchange', 'Buy exchange', 'Seq Profitable', 'All Prices']
        self.pro_frame = pd.DataFrame(columns=self.pro_headers)

        # set up trades file
        self.trades_headers = ['Date', 'Symbol',
                               'Side', 'Price', 'Exchange', 'Net Gain (%)']
        self.trades = pd.DataFrame(columns=self.trades_headers)

        for i in range(0, len(self.exchanges)-1):
            exchanges_str += self.exchanges[i].name+', '
        exchanges_str += 'and '+self.exchanges[-1].name

        if active:
            print(colorGood('Created Bouncer for {} investing {} {}.\nActive on {}\nThreshold: {}, Max speedup: {}%\n').format(
                self.symbol, self.quote_order_size, self.quote_coin, exchanges_str, self.threshold, self.speedup))
        else:
            if logging:
                print(colorEh('Created Bouncer scanning for {} with max {}% speedup.').format(
                    self.symbol, self.speedup))
            else:
                print(colorEh('Created Bouncer scanning for {} with max {}% speedup. Logging disabled.').format(
                    self.symbol, self.speedup))

        # init balances
        self.balances = dict()
        self.net = 0

        # initialize balances
        if initializeq:
            print('Initializing balances with ${} worth of {} in each account.'.format(
                self.quote_order_size, self.base_coin))
            self.inititalizeBalances()

        self.start_total_base_amount, self.start_total_quote_order_size = self.updateBalances(
            loud=False)

        if active:
            print(colorClock('Starting base amount [{:.8f} {}, {:.4f} {}]').format(
                self.start_total_base_amount, self.base_coin, self.start_total_quote_order_size, self.quote_coin))
            print()

    def getCommons(self):
        alls = list()
        for i in self.exchanges:
            x = list(i.load_markets().keys())
            for j in x:
                alls.append(j)
        out = list()

        for item in alls:
            if alls.count(item) == len(self.exchanges):
                out.append(item)
        out = set(out)
        # for i in out:
        #    if 'USD' in i:
        #       print(i, '1', end=' ')
        return out

    def getWatched(self):
        '''
        Get responses for each exchange for self.symbol.
        '''
        all_responses = dict()
        for exchange in self.exchanges:
            all_responses[exchange] = exchange.fetch_ticker(self.symbol)
        # print('Recived from {} in {self.precison} s'.format(
        #    ', '.join(all_responses.keys()), time.time()-before))
        return all_responses

    def getSpread(self, responses=None):
        # get tickers for the watched symbols and return exchanges and spread
        if responses == None:
            responses = self.getWatched()
        # not necessary to sort but it helps
        responses = OrderedDict(sorted(responses.items(),
                                       key=lambda x: getitem(x[1], 'ask')))
        response_items = list(responses.items())

        # set high and low
        '''
        Format on response_items
        [
            (exchange,{
                ask: 333,
                bid: 345,
                ...
            }),
            ...
        ]
        '''

        # make ordered dict of spreads COUNTING fees

        spreads = dict()
        for test_buy in response_items:
            for test_sell in response_items:
                buy_price = test_buy[1]['bid']*(1+(self.speedup/100))
                sell_price = test_sell[1]['ask']*(1-(self.speedup/100))
                actual_speedup = self.speedup
                if sell_price-buy_price <= 0:  # disable speedup
                    buy_price = test_buy[1]['bid']
                    sell_price = test_sell[1]['ask']
                    actual_speedup = 0

                if test_buy != test_sell:
                    test_spread = (self.quote_order_size /
                                   sell_price)*(sell_price-buy_price)
                    test_fee = (test_buy[0].calculateFee(self.symbol, 'limit', 'buy', self.quote_order_size/buy_price, buy_price, takerOrMaker='taker', params={})['cost'] +
                                test_sell[0].calculateFee(self.symbol, 'limit', 'sell', self.quote_order_size/sell_price, sell_price, takerOrMaker='taker', params={})['cost'])
                    spread_w_fee = test_spread-test_fee
                    spreads[spread_w_fee] = {
                        'buy': test_buy[0],
                        'buy_bid': test_buy[1]['bid'],
                        'buy_ask': test_buy[1]['ask'],
                        'buy_price': buy_price,
                        'sell': test_sell[0],
                        'sell_bid': test_sell[1]['bid'],
                        'sell_ask': test_sell[1]['ask'],
                        'sell_price': sell_price,
                        'fees': test_fee,
                        'no_fees': test_spread,
                        'spread_w_fees': spread_w_fee,
                        'speedup': actual_speedup  # a percent
                    }

        spreads = sorted(spreads.values(), key=lambda x: getitem(
            x, 'spread_w_fees'))  # as a list
        # pprint(spreads)
        # get last in list, sorted from low to high spread_w_fees
        '''
        sample from spreads:
        {
            'buy': ccxt.binanceus(),
            'buy_ask': 104.42,
            'buy_bid': 104.01,
            'buy_price': 104.01,
            'fees': 0.25096,
            'no_fees': 19.99230769230769,
            'sell': ccxt.bittrex(),
            'sell_ask': 130.0,
            'sell_bid': 100.0,
            'sell_price': 130.0,
            'spread_w_fees': 19.74134769230769,
            'speedup': 2
        }
        '''
        most_profitable = spreads[-1]
        buy = most_profitable['buy']
        sell = most_profitable['sell']

        low = most_profitable['buy_price']  # will remove soon
        high = most_profitable['sell_price']  # ditto
        fees = most_profitable['fees']
        no_fees = most_profitable['no_fees']
        spread = most_profitable['spread_w_fees']

        # find buy and sell and log
        exchanges_str = ''
        for i in range(0, len(responses)):
            ask = response_items[i][1]['ask']
            bid = response_items[i][1]['bid']
            exchange = response_items[i][0]
            if exchange == buy:
                fee = exchange.calculateFee(
                    self.symbol, 'limit', 'buy', self.quote_order_size/ask, ask, takerOrMaker='taker', params={})['cost']
                # logstr = colorLow('\t{}: ${:.3f} (fees on ${:.3f} order: ${:.3f})'.format(
                #    exchange.name, ask, self.quote_order_size, fee))
                logstr = colorLow('\t{}: ${:.3f} ask, ${:.3f} bid'.format(
                    exchange.name, ask, bid))
            elif exchange == sell:
                fee = exchange.calculateFee(
                    self.symbol, 'limit', 'sell', self.quote_order_size/ask, ask, takerOrMaker='taker', params={})['cost']
                # logstr = colorHigh('\t{}: ${:.3f} (fees on ${:.3f} order: ${:.3f})'.format(
                #    exchange.name, ask, self.quote_order_size, fee))
                logstr = colorHigh('\t{}: ${:.3f} ask, ${:.3f} bid'.format(
                    exchange.name, ask, bid))
            else:
                fee = exchange.calculateFee(
                    self.symbol, 'limit', 'buy', self.quote_order_size/ask, ask, takerOrMaker='taker', params={})['cost']
                # logstr = '\t{}: ${:.3f} (fees on ${:.3f} order: ${:.3f})'.format(
                #    exchange.name, ask, self.quote_order_size, fee)
                logstr = ('\t{}: ${:.3f} ask, ${:.3f} bid'.format(
                    exchange.name, ask, bid))
            exchanges_str += logstr+'\n'

        # remove all values less than threshold
        for i in range(0, len(spreads)):
            if spreads[i]['spread_w_fees'] <= self.threshold:
                spreads[i] = None
        spreads[:] = [x for x in spreads if x]

        # if empty, not profitable
        if spreads:
            profitable = True
        else:
            profitable = False

        if spreads:  # only print if profitable
            print('/'+'-'*55+colorClock(datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f")))
            print('[For {} w/ ${:.3f}]:'.format(self.symbol,
                                                self.quote_order_size))
            print(exchanges_str, end='')
            print(
                colorGood('max speedup of {}% (found {} profitable pairs ****)'.format(self.speedup, len(spreads))).rjust(90))
            for i in range(len(spreads)-1, -1, -1):
                item = spreads[i]
                print('{} Adjusted Spread: ${} (after fees: ${})\n  (buy on {} @ ${}, sell on {} @ ${} [speedup: {}%])'.format(
                    colorGood('[PROFITABLE {}]'.format(i+1)),
                    colorProfit(item['no_fees']),
                    colorProfit(
                        item['spread_w_fees']),
                    colorLow(
                        item['buy'].name),
                    colorLow(
                        '{:.3f}'.format(item['buy_price'])),
                    colorHigh(
                        item['sell'].name),
                    colorHigh(
                        '{:.3f}'.format(item['sell_price'])),
                    colorProfit(item['speedup'])))
        else:
            '''
            print('/'+'-'*55+colorClock(datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f")))
            print('[For {} w/ ${:.3f}]:'.format(self.symbol,
                                                self.quote_order_size))
            print(exchanges_str, end='')
            print('{} Adjusted Spread: ${} (after fees: ${})\n (buy on {} @ ${}, sell on {} @ ${} [grs.dif: ${}])'.format(colorBad('[NOT PROFITABLE]'),
                                                                                                                            colorProfit(
                                                                                                                                no_fees),
                                                                                                                            colorProfit(
                                                                                                                                spread),
                                                                                                                            colorLow(
                                                                                                                                buy.name),
                                                                                                                            colorLow(
                                                                                                                                '{:.3f}'.format(low)),
                                                                                                                            colorHigh(
                                                                                                                                sell.name),
                                                                                                                            colorHigh(
                                                                                                                                '{:.3f}'.format(high)),
                                                                                                                            colorProfit((high-low))))
                                                                                                                            '''
            pass
        # check last row
        seq_profitable = False
        # not implementing yet
        all_prices = spreads

        new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S"), self.symbol, self.quote_order_size,
                   high, low, spread, spread-fees, fees, profitable, sell.name, buy.name, seq_profitable, all_prices]
        self.pro_frame.loc[len(self.pro_frame)] = new_row

        if logging:
            if path.exists(self.pro_filename):  # if file exists, append
                self.pro_frame.iloc[[-1]].to_csv(
                    path_or_buf=self.pro_filename, mode='a', header=False, index=False)
            else:
                self.pro_frame.to_csv(
                    path_or_buf=self.pro_filename, index=False)

        return spreads, False

    def updateBalances(self, loud=True):
        '''
        Log balances to file and total base and quote amounts.
        '''
        for exchange in self.exchanges:
            self.balances[exchange] = exchange.fetch_balance()
        if loud:
            for exchange in self.exchanges:
                print(
                    '{} balance response - {}'.format(exchange, pformat(self.balances[exchange])))

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
                print('\t{} balances ({}) - [{}: {}, {}: {}]'.format(exchange, self.section, self.base_coin, self.balances[exchange][self.section]
                                                                     [self.base_coin], self.quote_coin, self.balances[exchange][self.section][self.quote_coin]))

        # bittrex_string, binance_string, kraken_string, coinbasepro_string
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
        # note, bc of fees it will buy 2 dollar higher.
        self.updateBalances(loud=False)

        for exchange in self.exchanges:
            price = (exchange.fetch_ticker(self.symbol))['bid']
            if self.balances[exchange][self.section][self.quote_coin] >= self.quote_order_size:
                try:
                    print('Creating buy order on {} for {} {} at {}'.format(
                        exchange, self.quote_order_size/price, self.symbol, price))
                    exchange.create_limit_buy_order(
                        self.symbol, self.quote_order_size/price, price)
                    new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                               self.symbol, 'buy', price, exchange.name, self.net]
                    self.trades.loc[len(self.trades)] = new_row
                except ccxt.ExchangeNotAvailable:
                    print('Market on {} offline.'.format(exchange.name))
            else:
                print(
                    '* Insufficient funds on {} to initialize balance'.format(exchange.name))

        self.blockTrades(5)

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
        print('Cleaning up for {}...'.format(self.symbol))
        responses = self.getWatched()
        self.updateBalances(loud=False)

        for exchange in responses:
            ask = responses[exchange]['ask']*.999
            # sell remaining
            remaining = float(
                self.balances[exchange][self.section][self.base_coin])
            if remaining > 0 and not self.anyOpen(exchange):
                try:
                    print('Selling off {:.6f} {} on {}'.format(
                        remaining, self.base_coin, exchange.name))
                    exchange.create_limit_sell_order(
                        self.symbol, remaining, ask)
                except Exception as e:
                    print(
                        '* Error in selling off {:.6f} {} on {}: {}'.format(remaining, self.base_coin, exchange.name, e))
            else:
                print(
                    'No need to sell, no balance in {} on {}'.format(self.base_coin, exchange.name))
        self.blockTrades(5)
        print('Final balances:')
        base, quote = self.updateBalances(loud=False)
        print('Sums: [{:.8f} {}, {:.3f} {}]'.format(
            base, self.base_coin, quote, self.quote_coin))
        self.updateNet()
        print('Net: {}%'.format(colorProfit(self.net)))
        print('Done!\n')

    def blockTrades(self, timewait):
        print(colorEh('Trades initiated ... blocking to completion'))

        open_trades = self.anyOpen()
        while open_trades:
            open_trades = self.anyOpen()
            time.sleep(timewait)

        print(colorGood('Trades completed! Moving on.'))

    def handleTransaction(self, buy_ex, sell_ex, low, high):
        '''
        Places the arbitrage transactions simultaneously.
        '''
        try:
            # creating processes
            print('Creating buy order on {} for {:.6f} {} at ${}'.format(
                buy_ex, self.quote_order_size/low, self.symbol, low))
            buy_ex.create_limit_buy_order(
                self.symbol, self.quote_order_size/low, low)
            new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                       self.symbol, 'buy', low, buy_ex.name, self.net]
            self.trades.loc[len(self.trades)] = new_row
            self.trades.to_csv(path_or_buf=self.trades_filename)

            print('Creating sell order on {} for {:.6f} {} at ${}'.format(
                sell_ex, self.quote_order_size/high, self.symbol, high))
            sell_ex.create_limit_sell_order(
                self.symbol, self.quote_order_size/high, high)
            new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                       self.symbol, 'sell', high, sell_ex.name, self.net]
            self.trades.loc[len(self.trades)] = new_row
            self.trades.to_csv(path_or_buf=self.trades_filename)

            self.blockTrades(5)
            # perform calculations for logging
        except ccxt.ExchangeNotAvailable:
            print(colorBad('Exchange not available.'))

        # recalculate
        self.updateNet()

        print('Balances fetched')
        self.updateBalances(loud=False)

        return 'Done'

    def arbitrate(self):
        '''
        Calculate spread and buy on low and sell on high.
        '''
        try:
            markets = self.getWatched()
            spreads, error = self.getSpread(markets)

            # add and subtract from mock balances here

            if spreads and self.active and not error:
                # get balances
                self.updateBalances(loud=False)

                action_taken = False
                for pair in spreads:
                    if not action_taken:
                        buy_ex = pair['buy']
                        sell_ex = pair['sell']
                        low = pair['buy_price']
                        high = pair['sell_price']

                        quote_balance = self.balances[buy_ex][self.section][self.quote_coin]
                        base_balance = self.balances[sell_ex][self.section][self.base_coin]
                        if quote_balance >= self.quote_order_size and base_balance >= self.quote_order_size/high:  # balances are good for original
                            self.handleTransaction(
                                buy_ex, sell_ex, low, high)
                            action_taken = True
                        elif quote_balance < self.quote_order_size and base_balance < self.quote_order_size/high:
                            print(colorBad('* Insufficient balance (missing ${:.3f} on {}, {:.4f} {} on {})'.format(
                                self.quote_order_size-quote_balance, buy_ex.name, self.quote_order_size/high-base_balance, self.base_coin, sell_ex.name)))
                        elif quote_balance < self.quote_order_size:
                            print(colorBad('* Insufficient balance (missing ${:.3f} on {})'.format(
                                self.quote_order_size-quote_balance, buy_ex.name)))
                        elif base_balance < self.quote_order_size/high:
                            print(colorBad('* Insufficient balance (missing {:.4f} {} on {})'.format(
                                self.quote_order_size/high-base_balance, self.base_coin, sell_ex.name)))

        except Exception as e:
            print(colorBad('Error in call ... trying again in 10 ({})').format(e))
            time.sleep(10)
            self.arbitrate()
