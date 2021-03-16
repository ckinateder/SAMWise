import argparse

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
    sessioner = createSessionMaker(engine)()
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
    uniques = table.symbol.drop_duplicates()

    counts_frame = pd.DataFrame(columns=["symbol", "profitable_pairs", "liquidity"])
    # print("*", counts_frame)

    counts_frame.symbol = list(uniques)
    counts_frame.set_index("symbol", inplace=True)

    counts_frame.profitable_pairs = 0
    counts_frame.liquidity = -1
    # count pairs
    for index, row in tqdm(
        table.iterrows(),
        total=len(table.index),
        leave=False,
        unit="row",
        dynamic_ncols=True,
        desc="count",
    ):
        sym = row.symbol
        counts_frame.loc[[sym], ["profitable_pairs"]] += 1 / timerange
    # count avg
    for index, row in tqdm(
        counts_frame.iterrows(),
        total=len(counts_frame.index),
        leave=False,
        unit="row",
        dynamic_ncols=True,
        desc="avg",
    ):
        sym = row.name
        symavg = table.loc[table.symbol == sym].liquidity.mean()
        counts_frame.loc[[sym], ["liquidity"]] = symavg

    counts_frame.sort_values(by="profitable_pairs", ascending=False, inplace=True)

    logs.debug(
        f"Top 10 symbols (symbol, profitable pairs per minute):\n{counts_frame.iloc[:10]}",
    )

    # scale liquidity
    scaler = MinMaxScaler(
        feature_range=(
            counts_frame.profitable_pairs.min(),
            counts_frame.profitable_pairs.max(),
        )
    )
    counts_frame["liquidity"] = scaler.fit_transform(counts_frame[["liquidity"]])

    with pd.option_context(
        "display.max_rows", None, "display.max_columns", None
    ):  # more options can be specified also
        logs.debug(counts_frame)
    top_50 = counts_frame.iloc[:50]
    """
    top_50.plot(
        # x=index,
        y="profitable_pairs",
        xlabel="symbol",
        ylabel="profitable pairs per minute",
        title=f"potential symbols to perform arbitrage on since {table.iloc[0]['batch']}",
        kind="bar",
        fontsize="7",
        figsize=(16, 9),
    )
    """
    # .figure
    # plot
    fig = plt.figure(
        figsize=(16, 9),
    )
    pairs_axis = fig.add_subplot(111)

    pairs_axis.bar((top_50.index), top_50.profitable_pairs, color=rgb(125, 166, 232))
    pairs_axis.set_xlabel("symbol")
    pairs_axis.set_ylabel("profitable pairs per minute")
    pairs_axis.set_xticklabels(list(top_50.index), rotation=90)
    pairs_axis.set_yscale("linear")
    pairs_axis.set_title(
        f"potential symbols to perform arbitrage on since {table.iloc[0]['batch']}"
    )

    liquid_axis = pairs_axis.twinx()
    liquid_axis.set_yscale("log")
    liquid_axis.set_ylabel("symbol liquidity")
    liquid_axis.set_yticks(np.arange(0, top_50.liquidity.max(), 1))
    liquid_axis.plot(
        top_50.index, top_50.liquidity, color=rgb(237, 66, 47), linewidth=2
    )
    plt.savefig(fname=f"{CHARTPATH}{imgname}.png")

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
