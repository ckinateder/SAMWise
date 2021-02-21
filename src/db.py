from getpass import getpass
from mysql.connector import connect, Error

import hive
import propagator

"""
Command to create indexes table:
    CREATE TABLE indexes (symbol VARCHAR(10), exchange VARCHAR(40));
Command to create results table:
    create table results (symbol VARCHAR(10), exchange VARCHAR(40), timestamp TIMESTAMP, datetime DATETIME, high decimal(9,5), low decimal(9,5), bid decimal(9,5), bidVolume decimal(9,5), ask decimal(9,5), askVolume decimal(9,5), vwap decimal(9,5), open decimal(9,5), close decimal(9,5), last decimal(9,5), previousClose decimal(9,5), percentage decimal(9,5), average decimal(9,5), baseVolume decimal(9,5), quoteVolume decimal(9,5), info JSON, dx decimal(9,5));
"""


def execute(con, s):
    with con.cursor(buffered=True) as cursor:
        cursor.execute(s)


try:
    with connect(
        host="localhost",
        user="root",
        password="MeHTMT02",
        database="symbols",
    ) as connection:
        print(connection)

except Error as e:
    print("f", e)

if __name__ == "__main__":
    # create hive
    hivee = hive.Hive(minnum=3)
    # create propagator
    tool = propagator.Propagtor()
    id = hivee.getInvertedDynamicCommons(hivee.dynamic_commons)
    props = tool.propagate(id)
