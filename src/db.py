from os import write
import time, sys
from getpass import getpass
from pprint import pprint

import ccxt
from decimal import *
from mysql.connector import Error, connect
import tqdm
import hive
import propagator
from helper import *

USER = "test"
PASS = "test"


def convertListOfTuples(ld):
    """
    Convert a list of single tuples to just a list
    Ex:
        input = [("results",),("latest",)]
        output = ["results", "latest"]
    """
    raws = []
    for i in ld:
        raws.append(i[0])
    return raws


def resetDatabase():
    """
    Reset the database.
    """
    db = connect(
        host="localhost",
        user=USER,
        password=PASS,
    )
    cursor = db.cursor()

    # see if exists
    cursor.execute("SELECT SCHEMA_NAME FROM INFORMATION_SCHEMA.SCHEMATA")
    raws = convertListOfTuples(cursor.fetchall())
    # drop if exists
    if "symbols" in raws:
        cursor.execute("DROP DATABASE symbols;")

    cursor.execute("CREATE DATABASE symbols;")
    cursor.execute("USE symbols;")
    cursor.execute(
        "CREATE TABLE results (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, symbol VARCHAR(20), exchange VARCHAR(40), timestamp BIGINT, ask decimal(20,8), askVolume decimal(20,2), average decimal(20,8), baseVolume decimal(20,2), bid decimal(20,8), bidVolume decimal(20,2), close decimal(20,8), datetime DATETIME, dx decimal(20,8), high decimal(20,8), last decimal(20,8), low decimal(20,8), open decimal(20,8), percentage decimal(20,8), previousClose decimal(20,8), quoteVolume decimal(20,2), vwap decimal(20,2));"
    )
    cursor.execute(
        "CREATE TABLE latest (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, symbol VARCHAR(20), exchange VARCHAR(40), timestamp BIGINT, ask decimal(20,8), askVolume decimal(20,2), average decimal(20,8), baseVolume decimal(20,2), bid decimal(20,8), bidVolume decimal(20,2), close decimal(20,8), datetime DATETIME, dx decimal(20,8), high decimal(20,8), last decimal(20,8), low decimal(20,8), open decimal(20,8), percentage decimal(20,8), previousClose decimal(20,8), quoteVolume decimal(20,2), vwap decimal(20,2));"
    )


def createPropQuery(props):
    """
    Creates a query to be used with the executemany command.
    """
    valueset = []
    for symbol in props:
        for exchange in props[symbol]:
            point = props[symbol][exchange]
            # set query and values dynamically
            values = ()
            query = "("
            for k in point:
                query += k + ", "
                # check if instance of exchange and fix
                if isinstance(point[k], ccxt.Exchange):
                    point[k] = point[k].id
                if k == "info":  # don't insert info to save space
                    point[k] = None
                values += (point[k],)
            valueset.append(values)
            # finish formatting command
            vs = ("%s, " * len(values))[:-2]
            query = query[:-2] + f") VALUES ({vs})"
    return query, valueset


def writeProps(db, props):
    """
    Writes props to both tables
    """
    cursor = db.cursor()
    start = now()
    query, valueset = createPropQuery(props)

    cursor.executemany("INSERT INTO results " + query, valueset)
    # delete whats in latest right now
    cursor.execute("truncate table latest")
    cursor.executemany("INSERT INTO latest " + query, valueset)
    ## to make final output we have to run the 'commit()' method of the database object
    db.commit()
    print(f"{cursor.rowcount} records inserted in {now()-start:.2f}s")


def getDBSize(db):
    # get table size in mb
    cursor = db.cursor()
    cursor.execute(
        'SELECT table_name AS "Table", ROUND(((data_length + index_length) / 1024 / 1024), 2) AS "Size (MB)" FROM information_schema.TABLES WHERE table_schema = "symbols" ORDER BY (data_length + index_length) DESC'
    )
    db_size = 0
    for i in cursor.fetchall():
        db_size += float(i[1])
    return round(db_size, 2)


def getTableLength(db, table):
    # get table length
    cursor = db.cursor()
    cursor.execute("SELECT id FROM results ORDER BY id DESC LIMIT 1")
    number_of_rows = cursor.fetchall()[0][0]
    return number_of_rows


def writePropsLoop(db=None, interval=1, times=None):
    """
    Loops times times and updates latest every query but results only every interval (in min)

    """
    # create propagator
    tool = propagator.Propagtor()
    id = tool.getInvertedDynamicCommons()

    last = 0
    interval = interval
    if db == None:
        db = connect(
            host="localhost",
            user=USER,
            password=PASS,
            database="symbols",
        )

    cursor = db.cursor()
    if times == None:
        times = sys.maxsize
    for i in range(times):
        props = tool.propagate(id)
        start = now()

        query, valueset = createPropQuery(props)

        if now() - last >= interval * 60:
            cursor.executemany("INSERT INTO results " + query, valueset)
            write_count = cursor.rowcount

            number_of_rows = getTableLength(db, "results")
            db_size = getDBSize(db)

            tqdm.write(
                colorGood(
                    f"{write_count} records inserted into 'results'; database now {db_size} MB and {number_of_rows:,} rows long."
                )
            )
            last = now()
        # delete whats in latest right now
        cursor.execute("truncate table latest")
        cursor.executemany("INSERT INTO latest " + query, valueset)
        ## to make final output we have to run the 'commit()' method of the database object
        db.commit()
        tqdm.write(
            colorGood(
                f"{cursor.rowcount} records overwritten to 'latest' in {now()-start:.2f}s"
            )
        )
        time.sleep(10)


if __name__ == "__main__":
    # commandline args
    if "-r" in sys.argv:
        resetDatabase()

    writePropsLoop(interval=1)
