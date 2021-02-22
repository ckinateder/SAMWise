import time, sys
from getpass import getpass
from pprint import pprint

import ccxt
from mysql.connector import Error, connect

import hive
import propagator
from helper import *

"""
Command to create database:
    CREATE DATABASE IF NOT EXISTS symbols;
Command to check if database exists:
    show databases like 'symbols';
Command to create results table:
    CREATE TABLE results (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, symbol VARCHAR(20), exchange VARCHAR(40), timestamp BIGINT, ask decimal(20,8), askVolume decimal(20,2), average decimal(20,8), baseVolume decimal(20,2), bid decimal(20,8), bidVolume decimal(20,2), close decimal(20,8), datetime DATETIME, dx decimal(20,8), high decimal(20,8), info JSON, last decimal(20,8), low decimal(20,8), open decimal(20,8), percentage decimal(20,8), previousClose decimal(20,8), quoteVolume decimal(20,2), vwap decimal(20,2));
"""

USER = "test"
PASS = "test"


def resetDatabase():
    db = connect(
        host="localhost",
        user=USER,
        password=PASS,
    )
    cursor = db.cursor()

    cursor.execute("DROP DATABASE symbols;")
    cursor.execute("CREATE DATABASE symbols;")
    cursor.execute("USE symbols;")
    cursor.execute(
        "CREATE TABLE results (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, symbol VARCHAR(20), exchange VARCHAR(40), timestamp BIGINT, ask decimal(20,8), askVolume decimal(20,2), average decimal(20,8), baseVolume decimal(20,2), bid decimal(20,8), bidVolume decimal(20,2), close decimal(20,8), datetime DATETIME, dx decimal(20,8), high decimal(20,8), info JSON, last decimal(20,8), low decimal(20,8), open decimal(20,8), percentage decimal(20,8), previousClose decimal(20,8), quoteVolume decimal(20,2), vwap decimal(20,2));"
    )
    cursor.execute(
        "CREATE TABLE latest (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, symbol VARCHAR(20), exchange VARCHAR(40), timestamp BIGINT, ask decimal(20,8), askVolume decimal(20,2), average decimal(20,8), baseVolume decimal(20,2), bid decimal(20,8), bidVolume decimal(20,2), close decimal(20,8), datetime DATETIME, dx decimal(20,8), high decimal(20,8), info JSON, last decimal(20,8), low decimal(20,8), open decimal(20,8), percentage decimal(20,8), previousClose decimal(20,8), quoteVolume decimal(20,2), vwap decimal(20,2));"
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


def writePropsLoop(db, interval, times=None):
    """
    Loops times times and updates latest every query but results only every interval (in min)

    """

    hivee = hive.Hive(minnum=2)
    # create propagator
    tool = propagator.Propagtor()
    id = hivee.getInvertedDynamicCommons(hivee.dynamic_commons)

    fstart = 0
    cursor = db.cursor()
    interval = interval
    if times == None:
        times = sys.maxsize
    for i in range(times):
        props = tool.propagate(id)
        start = now()

        query, valueset = createPropQuery(props)
        if now() - fstart >= interval * 60:
            cursor.executemany("INSERT INTO results " + query, valueset)
            print(f"{cursor.rowcount} records inserted into 'results' ")
            fstart = now()
        # delete whats in latest right now
        cursor.execute("truncate table latest")
        cursor.executemany("INSERT INTO latest " + query, valueset)
        ## to make final output we have to run the 'commit()' method of the database object
        db.commit()
        print(
            f"{cursor.rowcount} records overwritten to 'latest' in {now()-start:.2f}s"
        )
        time.sleep(10)


if __name__ == "__main__":
    ###
    # create hive
    # hivee = hive.Hive(minnum=3)
    # create propagator
    # tool = propagator.Propagtor()
    # id = hivee.getInvertedDynamicCommons(hivee.dynamic_commons)
    # resetDatabase()
    db = connect(
        host="localhost",
        user=USER,
        password=PASS,
        database="symbols",
    )
    # props = tool.propagate(id)
    writePropsLoop(db, interval=1)
