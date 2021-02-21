import json, ccxt
from datetime import datetime
from pprint import pprint

import hive
import propagator

if __name__ == "__main__":
    # create hive
    hivee = hive.Hive(minnum=3)
    # create propagator
    tool = propagator.Propagtor()
    id = hivee.getInvertedDynamicCommons(hivee.dynamic_commons)
    props = tool.propagate(id)
    pprint(props)
    print("(", end="")

    print("symbol VARCHAR(10)", end=", ")
    print("exchange VARCHAR(40)", end=", ")
    for i in list(props["ZRX/USDT"][list(props["ZRX/USDT"].keys())[0]].keys()):
        if "info" in i:
            print(f"{i} JSON", end=", ")
        elif "datetime" in i:
            print(f"{i} DATETIME", end=", ")
        elif "timestamp" in i:
            print(f"{i} TIMESTAMP", end=", ")
        elif "exchange" in i:
            pass
        elif "symbol" in i:
            pass
        elif not "change" in i:
            print(f"{i} decimal(9,5)", end=", ")
    print(");")