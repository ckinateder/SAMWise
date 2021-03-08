import argparse

import pandas as pd
from pandas.core.frame import DataFrame
from sqlalchemy import MetaData, create_engine

from helper import nowD
from manager import buildEngine


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
    results = dfFromTable(engine, "results")
    print(results.info())