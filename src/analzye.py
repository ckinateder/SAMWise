import argparse
from operator import getitem
from pprint import pprint

import pandas as pd
import numpy as np
import time
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

from tables import Analysis


def getMinutes(start, final):
    """
    Returns the time range of the database in minutes
    """
    days = (final - start).days
    minutes = (final - start).seconds / 60
    total = minutes + days * 60 * 24
    return total


def dfFromTable(session, table, chunksize=10000) -> DataFrame:
    """
    table_df = pd.read_sql_table(table, con=engine)

    return table_df
    """
    logs.debug(
        f"Loading table samwise.{table} ({getTableSize(session, 'samwise',table)})... "
    )

    length = getTableLength(session, table)
    chunks = pd.read_sql_table(table, con=engine, chunksize=chunksize)

    df = pd.DataFrame()
    chunkcount = 0
    for chunk in tqdm(
        chunks,
        total=math.ceil(length / chunksize),
        leave=False,
        unit="chunk",
        desc="load",
        dynamic_ncols=True,
    ):
        df = pd.concat([df, chunk])
        chunkcount += 1
        logs.debug(
            f"Loaded chunk {chunkcount} of {math.ceil(length / chunksize)} ({int(chunkcount/math.ceil(length / chunksize)*100)}%)"
        )
    return df


def plotPies(sym, values, labels):
    """
    Take values and labels and plot a pie chart for it
    Sample call:
    plotPies(sym, list(overview[sym].values()), list(overview[sym].keys()))
    """
    fig1, ax1 = plt.subplots()
    ax1.pie(
        values,
        labels=labels,
        autopct="%1.1f%%",
    )
    plt.savefig(fname=f"{CHARTPATH}detail/{sym.replace('/','-')}-distribution.png")
    logs.debug(
        f"Saved pie to '{CHARTPATH}detail/{sym.replace('/','-')}-distribution.png'"
    )
    plt.close()


def plotBars(since, df_to_plot, show=False):
    """
    Plot the given dataframe.
    """
    # plot
    # create figure
    fig = plt.figure()
    fig.set_size_inches(16, 9)
    pairs_axis = fig.add_subplot(111)

    # plot top 50 symbols and profitable pairs per min
    pairs_axis.bar(
        (df_to_plot.index), df_to_plot.profitable_pairs, color=rgb(150, 191, 232)
    )

    pairs_axis.bar((df_to_plot.index), df_to_plot.exchanges, color=rgb(125, 103, 166))
    pairs_axis.set_xlabel("symbol")
    pairs_axis.set_ylabel("profitable pairs per minute")
    pairs_axis.set_xticklabels(list(df_to_plot.index), rotation=80)
    pairs_axis.set_yscale("linear")
    pairs_axis.set_title(f"potential symbols to perform arbitrage on since {since}")

    # smooth
    # plot top 50 symbols and avg liquidity
    liquid_axis = pairs_axis.twinx()
    liquid_axis.set_yscale("log")
    liquid_axis.set_ylabel("symbol liquidity (LOG)")
    # liquid_axis.set_yticks(np.arange(0, df_to_plot.liquidity.max(), 1))
    liquid_axis.plot(
        df_to_plot.index, df_to_plot.liquidity, color=rgb(237, 66, 47), linewidth=2
    )

    # add margin

    plt.savefig(fname=f"{CHARTPATH}overview.png")
    logs.debug(f"Saved bar graph to '{CHARTPATH}overview.png'")
    if show:
        try:
            plt.show()
        except:
            logs.warn("Couldn't show graph")


def analyzeSpreads(session):
    """
    Analyzes the spreads and saves them to the database for plotting.
    """
    table = dfFromTable(session, "spreads")
    logs.debug("Created table.")

    logs.debug(f"Analyzing {len(table.index):,} rows ...")

    timerange = getMinutes(table.iloc[0]["batch"], table.iloc[-1]["batch"])
    uniques = list(table.symbol.drop_duplicates())

    overview = {}

    # count averages
    for sym in tqdm(
        uniques, leave=False, unit="row", dynamic_ncols=True, desc="count", position=1
    ):
        just_this_symbol = table.loc[table.symbol == sym]
        symavg = just_this_symbol.liquidity.mean()  # get average

        buys = set(just_this_symbol.buy.drop_duplicates())
        sells = set(just_this_symbol.sell.drop_duplicates())
        exnames = list(buys | sells)
        excount = len(exnames)  # get total number of unique exchanges

        sum_pp = round(len(just_this_symbol) / timerange, 2)  # get count

        # first set statics
        overview[sym] = {
            "profitable_pairs": sum_pp,
            "liquidity": symavg,
            "exchanges": excount,
            "makeup": {},
        }
        # then set percentages
        for exc in tqdm(
            exnames, leave=False, unit="exc", dynamic_ncols=True, desc="mkup"
        ):
            buys = len(just_this_symbol.loc[just_this_symbol.buy == exc])
            sells = len(just_this_symbol.loc[just_this_symbol.sell == exc])
            # print(buys, sells)
            portion = (buys + sells) / (len(just_this_symbol) * 2) * 100
            overview[sym]["makeup"][exc] = portion
    # create frame from dictionary

    # create ORMs for overview
    ORM_overview = []
    for symbol in overview:
        ORM_overview.append(
            Analysis(
                symbol=symbol,
                profitable_pairs=overview[symbol]["profitable_pairs"],
                liquidity=overview[symbol]["liquidity"],
                exchanges=overview[symbol]["exchanges"],
                makeup=overview[symbol]["makeup"],
            )
        )
    ORM_overview.sort(key=lambda x: x.profitable_pairs, reverse=True)  # sort
    session.query(Analysis).delete()
    session.bulk_save_objects(ORM_overview)  # write to DB
    session.commit()
    logs.debug("Overwrote overview to 'analysis'")


def analyzeIndefinitely(Session, waittime=30):
    """
    Analyze the spreads forever, with waittime in minutes. Takes a sessionmaker as an input
    """
    waittime = waittime * 60
    session = Session()
    while True:
        analyzeSpreads(session)
        time.sleep(waittime)


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

    # logs.debug(summary.info())
    Session = createSessionMaker(engine)
    session = Session()
    analyzeSpreads(session)
