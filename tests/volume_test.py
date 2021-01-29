import ccxt
from pprint import pprint

exchange_id = 'bittrex'
exchange_class = getattr(ccxt, exchange_id)
exchange = exchange_class({
    'apiKey': '5dafcc7b67b749e387c815bd2e792281',
    'secret': 'd179938a1105475ea86b309008c82808',
})
print(exchange.markets)
# ticker for a random symbol
pprint(exchange.fetch_ticker('DOGE/USD'))
