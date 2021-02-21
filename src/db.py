import time
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
    CREATE TABLE results (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, symbol VARCHAR(10), exchange VARCHAR(40), timestamp BIGINT, ask decimal(20,5), askVolume decimal(20,5), average decimal(20,5), baseVolume decimal(20,5), bid decimal(20,5), bidVolume decimal(20,5), close decimal(20,5), datetime DATETIME, dx decimal(20,5), high decimal(20,5), info JSON, last decimal(20,5), low decimal(20,5), open decimal(20,5), percentage decimal(20,5), previousClose decimal(20,5), quoteVolume decimal(20,5), vwap decimal(20,5));
"""


def resetDatabase():
    db = connect(
        host="localhost",
        user="root",
        password="MeHTMT02",
    )
    cursor = db.cursor()

    cursor.execute("DROP DATABASE symbols;")
    cursor.execute("CREATE DATABASE symbols;")
    cursor.execute("USE symbols;")
    cursor.execute(
        "CREATE TABLE results (id INT(11) NOT NULL AUTO_INCREMENT PRIMARY KEY, symbol VARCHAR(10), exchange VARCHAR(40), timestamp BIGINT, ask decimal(20,5), askVolume decimal(20,5), average decimal(20,5), baseVolume decimal(20,5), bid decimal(20,5), bidVolume decimal(20,5), close decimal(20,5), datetime DATETIME, dx decimal(20,5), high decimal(20,5), info JSON, last decimal(20,5), low decimal(20,5), open decimal(20,5), percentage decimal(20,5), previousClose decimal(20,5), quoteVolume decimal(20,5), vwap decimal(20,5));"
    )


def writeProps(cursor, props):
    counter = 0
    start = now()
    for symbol in props:
        for exchange in props[symbol]:
            point = props[symbol][exchange]
            # set query and values dynamically
            values = ()
            query = "INSERT INTO results ("
            for k in point:
                query += k + ", "
                # check if instance of exchange and fix
                if isinstance(point[k], ccxt.Exchange):
                    point[k] = point[k].id
                values += (point[k],)

            # finish formatting command
            vs = ("%s, " * len(values))[:-2]
            query = query[:-2] + f") VALUES ({vs})"

            cursor.execute(query, values)
            ## to make final output we have to run the 'commit()' method of the database object
            db.commit()
            counter += 1

    print(f"{counter} records inserted in {now()-start}s")


if __name__ == "__main__":
    ###
    # create hive
    hivee = hive.Hive(minnum=3)
    # create propagator
    tool = propagator.Propagtor()
    id = hivee.getInvertedDynamicCommons(hivee.dynamic_commons)
    # resetDatabase()
    db = connect(
        host="localhost",
        user="root",
        password="MeHTMT02",
        database="symbols",
    )
    cursor = db.cursor()
    for i in range(10):
        props = tool.propagate(id)
        writeProps(cursor, props)
        time.sleep(10)
