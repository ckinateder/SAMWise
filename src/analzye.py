import argparse

import pandas as pd
from pandas.core.frame import DataFrame
from sqlalchemy import MetaData, create_engine
from pprint import pprint
from helper import nowD
from manager import buildEngine
from tqdm import *


def dfFromTable(engine, table) -> DataFrame:
    table_df = pd.read_sql_table(table, con=engine)
    return table_df


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
    print("Loading table ... ")
    summary = dfFromTable(engine, "summary")
    print("Created table. \nCounting ...")
    uniques = summary.symbol.unique()
    counts = {}
    for index, row in tqdm(
        summary.iterrows(),
        total=len(summary.index),
        leave=False,
        unit="row",
        dynamic_ncols=True,
        desc="count",
    ):
        if row["symbol"] in counts:
            counts[row["symbol"]] += row["profitable_pairs"]
        else:
            counts[row["symbol"]] = row["profitable_pairs"]
    counts_frame = pd.DataFrame(counts.items(), columns=["symbol", "profitable_pairs"])
    counts_frame.sort_values(by="profitable_pairs", ascending=False)
    print(counts_frame)
