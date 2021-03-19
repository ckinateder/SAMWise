import argparse
from pprint import pprint

import pandas as pd
import numpy as np
from scipy.interpolate import make_interp_spline, BSpline

from pandas.core.frame import DataFrame
from sklearn.preprocessing import MinMaxScaler
from sqlalchemy import MetaData, create_engine
import math
from helper import FILE_TIME_FORMAT, getMemUsage, nowD, CHARTPATH, logs, rgb
from manager import (
    buildEngine,
    createSessionMaker,
    getDBSize,
    getTableLength,
    getTableSize,
)
from tqdm import *

import matplotlib.pyplot as plt


def getMinutes(start, final):
    """
    Returns the time range of the database in minutes
    """
    days = (final - start).days
    minutes = (final - start).seconds / 60
    total = minutes + days * 60 * 24
    return total


def dfFromTable(engine, table, chunksize=10000) -> DataFrame:
    """
    table_df = pd.read_sql_table(table, con=engine)

    return table_df
    """
    sessioner = createSessionMaker(
        engine
    )()  # creates sessionmaker and calls its constructor
    logs.debug(
        f"Loading table samwise.{table} with {engine} ({getTableSize(sessioner, 'samwise',table)})... "
    )

    length = getTableLength(sessioner, table)
    chunks = pd.read_sql_table(table, con=engine, chunksize=chunksize)

    df = pd.DataFrame()
    for chunk in tqdm(
        chunks,
        total=math.ceil(length / chunksize),
        leave=False,
        unit="chunk",
        desc="load",
        dynamic_ncols=True,
    ):
        df = pd.concat([df, chunk])
    return df


def analyzeSpreads(table, imgname=nowD().strftime(FILE_TIME_FORMAT)):
    logs.debug(f"Analyzing {len(table.index):,} rows ...")

    timerange = getMinutes(table.iloc[0]["batch"], table.iloc[-1]["batch"])
    uniques = list(table.symbol.drop_duplicates())

    overview = {}
    pies = {}
    # count averages
    for sym in tqdm(
        uniques,
        leave=False,
        unit="row",
        dynamic_ncols=True,
        desc="count",
    ):
        just_this_symbol = table.loc[table.symbol == sym]
        symavg = just_this_symbol.liquidity.mean()  # get average

        buys = set(just_this_symbol.buy.drop_duplicates())
        sells = set(just_this_symbol.sell.drop_duplicates())
        exnames = list(buys | sells)
        excount = len(exnames)  # get total number of unique exchanges

        sum_pp = len(just_this_symbol) / timerange  # get count

        # first set statics
        overview[sym] = {
            "profitable_pairs": sum_pp,
            "liquidity": symavg,
            "exchanges": excount,
            "exchanges_names": exnames,
        }
        # then set percentages

        for exc in exnames:
            buys = len(just_this_symbol.loc[just_this_symbol.buy == exc])
            sells = len(just_this_symbol.loc[just_this_symbol.sell == exc])
            # print(buys, sells)
            portion = (buys + sells) / (len(just_this_symbol) * 2) * 100
            overview[sym][exc] = portion

    # create frame from dictionary
    overview_frame = pd.DataFrame.from_dict(overview, orient="index")
    overview_frame.sort_values(
        by="profitable_pairs", ascending=False, inplace=True
    )  # sort

    logs.debug(
        f"Top 10 symbols (symbol, profitable pairs per minute):\n{overview_frame.iloc[:10]}",
    )

    top_50 = overview_frame.iloc[:50]  # get top 50
    # plot

    fig = plt.figure(
        figsize=(16, 9),
    )
    pairs_axis = fig.add_subplot(111)

    # plot top 50 symbols and profitable pairs per min
    pairs_axis.bar((top_50.index), top_50.profitable_pairs, color=rgb(150, 191, 232))

    pairs_axis.bar((top_50.index), top_50.exchanges, color=rgb(125, 103, 166))
    pairs_axis.set_xlabel("symbol")
    pairs_axis.set_ylabel("profitable pairs per minute")
    pairs_axis.set_xticklabels(list(top_50.index), rotation=80)
    pairs_axis.set_yscale("linear")
    pairs_axis.set_title(
        f"potential symbols to perform arbitrage on since {table.iloc[0]['batch']}"
    )

    # smooth
    # plot top 50 symbols and avg liquidity
    liquid_axis = pairs_axis.twinx()
    liquid_axis.set_yscale("log")
    liquid_axis.set_ylabel("symbol liquidity (LOG)")
    # liquid_axis.set_yticks(np.arange(0, top_50.liquidity.max(), 1))
    liquid_axis.plot(
        top_50.index, top_50.liquidity, color=rgb(237, 66, 47), linewidth=2
    )

    # add margin

    plt.savefig(fname=f"{CHARTPATH}overview.png")
    try:
        plt.show()
    except:
        pass


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(
        description="Handle database connections for SAMWise"
    )
    parser.add_argument("-u", "--user", help="username", default="test")
    parser.add_argument("-p", "--pwd", help="password", default="test")
    parser.add_argument("-H", "--host", help="host", default="localhost")
    parser.add_argument("-P", "--port", help="port", default="3306")
    parser.add_argument("-d", "--database", help="database", default="samwise")
    args = parser.parse_args()

    # mark start time
    start_time = nowD()
    # create engine
    engine = buildEngine(
        connection="mysql",
        username=args.user,
        password=args.pwd,
        host=args.host,
        port=args.port,
        database=args.database,
    )
    summary = dfFromTable(engine, "spreads")
    # logs.debug(summary.info())
    logs.debug("Created table.")
    analyzeSpreads(summary)
