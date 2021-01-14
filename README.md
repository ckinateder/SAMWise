# SAMWise
Spatial Arbitrage Method Wizard

## Findings

Currently, this is still a work in progress, but it looks incredibly promising. Because the high and low exchanges flip flop and generally are in no way static, there seems to be potentional for passive income generation here. However, choosing which currency to act on will be an interesting challenge. Once I choose one, I will then run tests on the time it takes to execute a trade via a limit order. As long as both the buy and sell orders fill in relatively similar times, the strategy should remain viable.

## Installation

Clone repository and install dependencies by using 

```
$ git clone https://github.com/ckinateder/SAMWise.git
$ cd SAMWise
(SAMWise)$ pip3 install -r requirements.txt
```

## Console Output
```
(SAMWise)$ python3 src/main.py BCH/USD 30

/-------------------------------------------------------01/11/2021-12:41:27:959965
For BCH/USD:
        Bittrex: 452.869
        Binance US: 451.22
        Kraken: 450.25
        Coinbase Pro: 450.99
        [PROFITABLE] Adjusted Spread: 0.17349 USD (after fees: 0.02049 USD)
        (buy on Kraken, sell on Bittrex)
/-------------------------------------------------------01/11/2021-12:41:28:982259
For BCH/USD:
        Bittrex: 452.869
        Binance US: 451.22
        Kraken: 450.4
        Coinbase Pro: 453.03
        [NOT PROFITABLE] Adjusted Spread: 0.17416 USD (after fees: -0.05384 USD)
        (buy on Kraken, sell on Coinbase Pro)
/-------------------------------------------------------01/11/2021-12:41:29:981777
For BCH/USD:
        Bittrex: 452.869
        Binance US: 454.05
        Kraken: 450.4
        Coinbase Pro: 453.03
        [PROFITABLE] Adjusted Spread: 0.24116 USD (after fees: 0.13316 USD)
        (buy on Kraken, sell on Binance US)
/-------------------------------------------------------01/11/2021-12:41:30:876675
For BCH/USD:
        Bittrex: 452.869
        Binance US: 454.04
        Kraken: 450.4
        Coinbase Pro: 453.03
        [PROFITABLE] Adjusted Spread: 0.24051 USD (after fees: 0.13251 USD)
        (buy on Kraken, sell on Binance US)
/-------------------------------------------------------01/11/2021-12:41:31:964030
For BCH/USD:
        Bittrex: 452.87
        Binance US: 454.02
        Kraken: 452.2
        Coinbase Pro: 452.34
        [PROFITABLE] Adjusted Spread: 0.12026 USD (after fees: 0.01226 USD)
        (buy on Kraken, sell on Binance US)
/-------------------------------------------------------01/11/2021-12:41:32:818400
For BCH/USD:
        Bittrex: 452.87
        Binance US: 454.02
        Kraken: 452.2
        Coinbase Pro: 452.34
        [PROFITABLE] Adjusted Spread: 0.12026 USD (after fees: 0.01226 USD)
        (buy on Kraken, sell on Binance US)
```