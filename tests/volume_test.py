import ccxt
from pprint import pprint
from math import log, floor


exchange_id = 'binanceus'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': 'JKxGrTVB7F3gKOnOY9H9GeikIIhg83f8kuYh2AReK73SPmU2ZRxWXPnqBLvXtPoO',
    'secret': 'svRkNr0Y49w0wLeONnJitW2WuI39iUPmRwqnEPtWoJBw0sAPJSKIeosfCaaBA0HP',
})
print(exchange.markets)
x = exchange.fetch_ticker('BTC/USD')
pprint(x)
# pprint(exchange.fetch_order_book('DOGE/USD'))
value = x['quoteVolume']


def human_format(number):
    units = ['', 'K', 'M', 'G', 'T', 'P']
    k = 1000.0
    magnitude = int(floor(log(number, k)))
    return '%.2f%s' % (number / k**magnitude, units[magnitude])


print(human_format(value))
