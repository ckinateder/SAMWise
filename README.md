# SAMWise

### Spatial Arbitrage Method Wizard

Arbitrage is a way to generate passive income off of the price differences of a currency on multiple exchanges. The idea is that you buy on the lowest exchange, and simultaneously sell on the highest exchange. Since the prices move around and the high and low exchanges tend to flip-flop, there isn't a need to move assets between exchanges after each transaction.

## Findings

Currently, this is still a work in progress, but it looks incredibly promising. Because the high and low exchanges flip-flop and generally are in no way static, there seems to be potentional for passive income generation here. However, choosing which currency to act on will be an interesting challenge. Once I choose one, I will then run tests on the time it takes to execute a trade via a limit order. As long as both the buy and sell orders fill in relatively similar times, the strategy should remain viable.

## Process

The basic design of the program is pretty straightforward. The main class uses the [ccxt](https://github.com/ccxt/ccxt) library to connect to the API for each individual exchange. It polls the price for the given cryptocurrency pair on each connected exchange, finds the lowest and highest pair, and then runs a calculation to determine if selling on one and buying on the other will produce a profit after fees. If yes, then it checks if each account has the correct balances, and then submits a limit order (one for buy and one for sell) to each respective exchange. However, if the balances are too low, it also checks to see if the next highest and/or next lowest pairs are profitable as well, and so on until it either runs out of profitable pairs, or an action is taken. This way, it may still be able to turn a profit even if the ideal balances aren't in the right places. Additionally, I implemented a feature called speedup. It's a percent that tightens the margin by `speedup` percent, decreasing profit per trade, but increasing trade frequency. This is due to the time it takes to execute limit orders. Lastly, I added a parameter called liquidity. This uses a formula to determine the liquidity of a market, to help find the possible trade execution speed. It runs in a loop so this goes continuously. One important thing to note when looking at the output is the `FF` flag (in green). This flag means that selling at the ask on exhange 1 and buying at the bid on exchange 2 and selling at the ask on exchange 2 and buying at the bid on exchange 1 would both be profitable at the same point in time. This is incredibly important because it basically means that picking one of these `FF` pairs enables your profits to ONLY be limited by trade execution time. You can effectively bounce assets back and forth between the same exchanges.

Currently, speed has been greatly increased. Using a concurrency optimization algorithm I designed, the time it takes to fetch the symbols has been reduced from 10+ minutes to less than 1 second.

## API

The API is now partly functional.
Current endpoints:

* `/api/historical`
* `/api/latest`
* `/api/spreads` (not usable yet, will be integrated with hive)

`/api/historical/` params:
| identifier | format and type         | description                             |
| ---------- | ----------------------- | --------------------------------------- |
| key        | string                  | identifier of column to pick range from |
| bottom     | same type as `row[key]` | bottom end of range                     |
| top        | same type as `row[key]` | top end of range                        |

NOTE: if key is a datetime, top and bottom format MUST be `YY-MM-DD HH:MM:SS`

## Adding Exchanges

SAMWise supports all exchanges supported by ccxt. To add a new exchange, follow the prompts when running the program.

## Installation

Clone repository and install dependencies by using

```Bash
$ git clone https://github.com/ckinateder/SAMWise.git
$ cd SAMWise
(SAMWise)$ pip3 install -r requirements.txt
```

## Usage

All you have to do is run the server class and follow the prompts.

```Bash
(SAMWise)$ python3 src/server.py
```

## Running From a Server

If you are running from a remote session, run through a screen to make sure it won't disconnect.

```Bash
(SAMWise)$ screen
(SAMWise)$ python3 src/server.py
```

Then, Ctrl + A and then Ctrl + D to detach from the session. You can exit the ssh session and it will continue to run. You can later run `screen -r` to reconnect to the screen.

## Console Output

![demo](img/demo.png)

![scanner](img/scanner.png)

## Execution List

* Develop a triangular arbitrage framework
* Develop backtesting
* Develop API
* Design master symbol allocator using ML
* Test trade execution speed
* Test over a day
* Test over a week
* Develop UI