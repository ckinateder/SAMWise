import logging
import multiprocessing
import sys
import time
from datetime import datetime
from os import path, listdir
from getpass import getpass

import ccxt
import pandas as pd
from pprint import pformat, pprint

from crayon import *

__author__ = 'Calvin Kinateder'
__email__ = 'calvinkinateder@gmail.com'


class Bouncer:
    def __init__(self, symbol, quote_order_size, exchanges, initializeq, active=True, logging=True):
        '''
        Create the class.
        '''

        # add to exchange list
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
        # initialize balances
        if initializeq:
            self.inititalizeBalances()

        self.start_time = time.time()
        self.base_coin = symbol.split('/')[0]
        self.quote_coin = symbol.split('/')[1]
        self.quote_order_size = quote_order_size
        self.pro_filename = 'logs/'+self.base_coin+'-'+self.quote_coin+'.csv'
        self.trades_filename = 'logs/trades/'+datetime.now().strftime("%m-%d-%Y_%H-%M") + '_' + \
            self.base_coin+'-'+self.quote_coin + '_trades.csv'
        self.threshold = 0.009  # for trades

        # mark which balance section to look at
        self.section = 'total'

        exchanges_str = ''
        for i in range(0, len(self.exchanges)-1):
            exchanges_str += self.exchanges[i].name+', '
        exchanges_str += 'and '+self.exchanges[-1].name

        if active:
            print(colorGood('Created Bouncer for {} investing {} {}.\nActive on {}\nThreshold: {}\n').format(
                self.symbol, self.quote_order_size, self.quote_coin, exchanges_str, self.threshold))
        else:
            if logging:
                print(colorEh('Created Bouncer scanning for {}.').format(self.symbol))
            else:
                print(colorEh('Created Bouncer scanning for {}. Logging disabled.').format(
                    self.symbol))

        # init balances
        self.balances = dict()
        self.net = 0

        self.start_total_base_amount, self.start_total_quote_order_size = self.updateBalances(
            loud=False)

        if active:
            print(colorClock('Starting base amount [{:.8f} {}, {:.4f} {}]').format(
                self.start_total_base_amount, self.base_coin, self.start_total_quote_order_size, self.quote_coin))
            print()

        # set up file for logging
        self.pro_headers = ['Date', 'Symbol', 'Investment', 'High', 'Low', 'Adjusted Spread',
                            'Adj. Spread after fees', 'Fees', 'Profitable', 'Sell exchange', 'Buy exchange', 'Seq Profitable', 'All Prices']
        self.pro_frame = pd.DataFrame(columns=self.pro_headers)

        # set up trades file
        self.trades_headers = ['Date', 'Symbol',
                               'Side', 'Price', 'Exchange', 'Net Gain (%)']
        self.trades = pd.DataFrame(columns=self.trades_headers)

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
        # print('Recived from {} in {:.3f} s'.format(
        #    ', '.join(all_responses.keys()), time.time()-before))
        return all_responses

    def getSpread(self, responses=None):
        # get tickers for the watched symbols and return exchanges and spread
        if responses == None:
            responses = self.getWatched()

        spread = 0

        low = responses[self.exchanges[0]]['ask']
        high = responses[self.exchanges[0]]['ask']

        for exchange in responses:
            ask = responses[exchange]['ask']
            if ask > high:
                high = ask
            elif ask < low:
                low = ask

        if high > 0 and low > 0:
            # find buy and sell and log
            exchanges_str = ''
            for exchange in self.exchanges:
                ask = responses[exchange]['ask']

                logstr = '\t{}: {:.3f}'.format(exchange, ask)
                if low == ask:
                    buy = exchange
                    logstr = colorLow('\t{}: {:.3f}'.format(buy, ask))
                elif high == ask:
                    sell = exchange
                    logstr = colorHigh('\t{}: {:.3f}'.format(sell, ask))
                exchanges_str += logstr+'\n'

            spread = (self.quote_order_size/high)*(high-low)

            fees = (buy.calculateFee(self.symbol, 'limit', 'buy', self.quote_order_size/low, low, takerOrMaker='taker', params={})['cost'] +
                    sell.calculateFee(self.symbol, 'limit', 'sell', self.quote_order_size/high, high, takerOrMaker='taker', params={})['cost'])

            if spread - fees > self.threshold:
                msg = colorGood(
                    ' '*53+'found profitable pair ****\n' + '[PROFITABLE]')
                profitable = True
            else:
                msg = colorBad('[NOT PROFITABLE]')
                profitable = False

            if profitable or True:  # effectively disabled rn, print all # only print if profitable
                print(
                    '/'+'-'*55+colorClock(datetime.now().strftime("%m/%d/%Y-%H:%M:%S:%f")))
                print('[For {}]:'.format(self.symbol))

                print(exchanges_str, end='')

                print(
                    '{} Adjusted Spread: {} {} (after fees: {} {})\n(buy on {}: {}, sell on {}: {} [grs.dif: {}])'.format(msg,
                                                                                                                          colorProfit(
                                                                                                                              spread),
                                                                                                                          self.quote_coin,
                                                                                                                          colorProfit(
                                                                                                                              spread-fees),
                                                                                                                          self.quote_coin,
                                                                                                                          colorLow(
                                                                                                                              buy.name),
                                                                                                                          colorLow(
                                                                                                                              low),
                                                                                                                          colorHigh(
                                                                                                                              sell.name),
                                                                                                                          colorHigh(
                                                                                                                              high),
                                                                                                                          colorEh('{:.3f}'.format(high-low))))

            # check last row
            seq_profitable = False
            # not implementing yet
            all_prices = ''
            for exchange in responses:
                ask = responses[exchange]['ask']
                all_prices += '{}: {}, '.format(exchange.name, ask)

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

            return spread, buy, sell, low, high, profitable, fees, False
        else:
            print(colorBad('Error in currency {}: price returned 0.'.format(self.symbol)))
            return 0, self.exchanges[0], self.exchanges[0], low, high, False, 0, True

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
        for exchange in self.exchanges:
            if exchange.fetch_balance()[self.section] >= self.quote_order_size:
                print('Creating market buy order for {} {} on {}'.format(
                    self.quote_order_size, self.symbol, exchange.name))
                exchange.create_market_buy_order(
                    self.symbol, self.quote_order_size)
            else:
                print(
                    'Insufficient balance on {} to set up balance'.format(exchange.name))

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
            ask = responses[exchange]['ask']
            # sell remaining
            remaining = float(
                self.balances[exchange][self.section][self.base_coin])
            if remaining > 0 and not self.anyOpen(exchange):
                try:
                    print('Selling off {} {} on {}'.format(
                        remaining, self.base_coin, exchange.name))
                    exchange.create_limit_sell_order(
                        self.symbol, remaining, ask)
                except Exception as e:
                    print(
                        'Error in selling off {} {} on {}: {}'.format(remaining, self.base_coin, exchange.name, e))
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

    def handleTransaction(self, buy_ex, sell_ex, low, high):
        '''
        Places the arbitrage transactions simultaneously.
        '''
        # creating processes
        print('Creating buy order on {} for {} {} at {}'.format(
            buy_ex, self.quote_order_size/low, self.symbol, low))
        buy_ex.create_limit_buy_order(
            self.symbol, self.quote_order_size/low, low)
        new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                   self.symbol, 'buy', low, buy_ex.name, self.net]
        self.trades.loc[len(self.trades)] = new_row

        print('Creating sell order on {} for {} {} at {}'.format(
            sell_ex, self.quote_order_size/high, self.symbol, high))
        sell_ex.create_limit_sell_order(
            self.symbol, self.quote_order_size/high, high)
        new_row = [datetime.now().strftime("%m-%d-%Y_%H-%M-%S.%f"),
                   self.symbol, 'sell', high, sell_ex.name, self.net]
        self.trades.loc[len(self.trades)] = new_row

        self.blockTrades(5)
        # perform calculations for logging

        # recalculate
        self.updateNet()

        self.trades.to_csv(path_or_buf=self.trades_filename)
        print('Trades completed')

        print('Balances fetched')
        self.updateBalances(loud=False)

        return 'Done'

    def arbitrate(self):
        '''
        Calculate spread and buy on low and sell on high.
        '''
        try:
            markets = self.getWatched()
            spread, buy_ex, sell_ex, low, high, profitable, fees_applied, error = self.getSpread(
                markets)

            # add and subtract from mock balances herê

            if profitable and self.active and not error:
                self.updateBalances(loud=False)
                quote_balance = self.balances[buy_ex][self.section][self.quote_coin]
                base_balance = self.balances[sell_ex][self.section][self.base_coin]

                if quote_balance >= self.quote_order_size and base_balance >= self.quote_order_size/high:  # balances are good
                    # no open orders
                    if not self.anyOpen(buy_ex) and not self.anyOpen(sell_ex):
                        self.handleTransaction(
                            buy_ex, sell_ex, low, high)
                    else:
                        print(colorBad(
                            'Open orders - taking no action.'))
                else:
                    print(colorBad('Balances not sufficient to trade - [{:.4f} {} on {}, {:.4f} {} on {}]\n(needed [{:.4f} {} on {}, {:.4f} {} on {}])'.format(
                        quote_balance, self.quote_coin, buy_ex.name, base_balance, self.base_coin, sell_ex.name,
                        self.quote_order_size, self.quote_coin, buy_ex.name, self.quote_order_size/high, self.base_coin, sell_ex.name)))
        except Exception as e:
            print(colorBad('Error in call ... trying again in 10 ({})').format(e))
            time.sleep(10)
            self.arbitrate()
