import sys
import time
from decimal import *
from getpass import getpass
from os import write
from pprint import pprint
import ccxt
import tqdm
from mysql.connector import Error, connect

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


def resetDatabase(db_name):
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
        cursor.execute(f"DROP DATABASE {db_name};")

    cursor.execute(f"CREATE DATABASE {db_name};")
    cursor.execute(f"USE {db_name};")
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


def writeProps(db, props, table, overwrite=False):
    """
    Writes props to both tables
    """
    cursor = db.cursor()
    start = now()
    query, valueset = createPropQuery(props)

    if overwrite:
        cursor.execute("truncate table latest")
    cursor.executemany(f"INSERT INTO {table} {query}", valueset)
    db.commit()
    tqdm.write(
        colorGood(
            f"{cursor.rowcount} records inserted into '{table}' in {now()-start:.2f}s"
        )
    )


def parseQuery(c):
    """
    Parse the query obj to dict
    """
    output = []
    for row in c:
        row_data = {}
        for key in row:
            if type(row[key]) is Decimal:
                row_data[key] = float(row[key])
            elif isinstance(row[key], datetime):
                row_data[key] = row[key].strftime(TIME_FORMAT)
            else:
                row_data[key] = row[key]
        output.append(row_data)
    return output


def getRowByID(db, table, id=1, special=None):
    """
    Gets a row by index or range and returns it as a dict. If all is passed as special, returns everything.
    EX:
        getRowByID(db, "results", 1)
        returns row 1
        getRowByID(db, "results", [5,10])
        returns rows 5-10

        Anything outside of said format will throw an error.

    """
    cursor = db.cursor(dictionary=True)
    if special == "all":
        cursor.execute(f"SELECT * FROM {table}")

    else:
        # setup types
        if type(id) == list and len(id) == 2:
            for x in range(len(id)):
                id[x] = int(id[x])
            if id[0] == id[1]:
                id = id[0]

        if type(id) == int:
            cursor.execute(f"SELECT * FROM {table} WHERE id={id}")
        elif type(id) == list:
            cursor.execute(
                f"SELECT * FROM {table} WHERE id between {id[0]} and {id[1]}"
            )
        else:
            # return none if wrong format
            raise TypeError

    c = cursor.fetchall()
    output = parseQuery(c)
    return output


def getDBSize(db):
    # get table size in mb
    cursor = db.cursor()
    cursor.execute(
        'SELECT table_name AS "Table", ROUND(((data_length + index_length) / 1024 / 1024), 2) AS "Size (MB)" FROM information_schema.TABLES WHERE table_schema = "symbols" ORDER BY (data_length + index_length) DESC'
    )
    db_size = 0
    # print(cursor.fetchall())
    for i in cursor.fetchall():
        db_size += float(i[1])
    return round(db_size, 2)


def getTableLength(db, table):
    # get table length
    cursor = db.cursor()
    cursor.execute(f"SELECT id FROM {table} ORDER BY id DESC LIMIT 1")
    number_of_rows = cursor.fetchall()[0][0]
    return number_of_rows


def initializeDB(db_name):
    db = connect(
        host="localhost",
        user=USER,
        password=PASS,
        database=db_name,
    )
    return db


def writePropsLoop(db=None, db_name="symbols", interval=1, times=None):
    """
    Loops times times and updates latest every query but results only every interval (in min)

    """
    # create propagator
    tool = propagator.Propagtor()
    id = tool.getInvertedDynamicCommons()

    last = 0
    interval = interval
    if db == None:
        db = initializeDB(db_name)
    if times == None:
        times = sys.maxsize
    for i in range(times):
        props = tool.propagate(id)
        if now() - last >= interval * 60:
            writeProps(db, props, "results")
            print(getRowByID(db, "results", 1))
            number_of_rows = getTableLength(db, "results")
            db_size = getDBSize(db)
            tqdm.write(
                colorGood(
                    f"* 'results' now {db_size} MB and {number_of_rows:,} rows long."
                )
            )

            last = now()

        writeProps(db, props, "latest", overwrite=True)

        time.sleep(10)


def main():
    """
    Main function
    """
    writePropsLoop(interval=1)


if __name__ == "__main__":
    # commandline args
    if "-r" in sys.argv:
        confirm = input("Are you sure you want to reset the DB? (Y/n) ").lower()
        if "y" in confirm:
            resetDatabase("symbols")
    main()
