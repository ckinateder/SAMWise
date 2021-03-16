import argparse

import pandas as pd
from pandas.core.frame import DataFrame
from sqlalchemy import MetaData, create_engine
import math
from helper import FILE_TIME_FORMAT, getMemUsage, nowD, CHARTPATH, logs
from manager import (
    buildEngine,
    createSessionMaker,
    getDBSize,
    getTableLength,
    getTableSize,
)
from tqdm import *


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
    counts = {}

    timerange = getMinutes(table.iloc[0]["batch"], table.iloc[-1]["batch"])

    for index, row in tqdm(
        table.iterrows(),
        total=len(table.index),
        leave=False,
        unit="row",
        dynamic_ncols=True,
        desc="count",
    ):
        if row["symbol"] in counts:
            counts[row["symbol"]] += 1 / timerange
        else:
            counts[row["symbol"]] = 1 / timerange
    # df["weight"].mean()
    counts_frame = pd.DataFrame(counts.items(), columns=["symbol", "profitable_pairs"])
    counts_frame.sort_values(by="profitable_pairs", ascending=False, inplace=True)

    counts_frame["liquidity"] = -1
    for index, row in tqdm(
        counts_frame.iterrows(),
        total=len(counts_frame.index),
        leave=False,
        unit="row",
        dynamic_ncols=True,
        desc="avg",
    ):
        symavg = table.loc[
            table.symbol == row.symbol
        ].liquidity.mean()  # compute average
        idd = counts_frame.loc[counts_frame.symbol == row.symbol].index[0]  # get index
        print(symavg)
        print(counts_frame.at[idd, "symbol"])
        counts_frame.at[idd, "liquidity"] = float(symavg)  # set new value
        print(counts_frame[counts_frame.symbol == row.symbol].liquidity)

    logs.debug(
        f"Top 10 symbols (symbol, profitable pairs per minute):\n{counts_frame.iloc[:10]}",
    )

    counts_frame.iloc[:50].plot(
        x="symbol",
        y="profitable_pairs",
        xlabel="symbol",
        ylabel="profitable pairs per minute",
        title=f"potential symbols to perform arbitrage on since {table.iloc[0]['batch']}",
        kind="bar",
        fontsize="7",
        figsize=(16, 9),
    ).figure.savefig(f"{CHARTPATH}{imgname}.png")


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
