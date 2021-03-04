import argparse
import decimal
import json
import sys
import time
from datetime import date
from pprint import pprint

import ccxt
import tqdm
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.sqltypes import DateTime
from tqdm import *

import hive
import propagator
from helper import *
from tables import Base, Results, Spread

USER = "test"
PASS = "test"


def buildEngine(connection, username, password, host, port, database, echo=False):
    """
    Takes string params and returns an engine.
    props[sym] call: createSession("mysql", "test", "test", "localhost", "3306", "symbols")
    """
    engine = create_engine(
        f"{connection}://{username}:{password}@{host}:{port}/{database}", echo=echo
    )
    return engine


def resetTables(engine):
    """
    Drop all tables and create them again
    """
    tqdm.write(colorBad("Resetting database ..."))
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def createSessionMaker(engine):
    """
    Create a session from an engine
    """
    maker = sessionmaker(bind=engine)
    return maker


def getDBSize(session, dbname):
    """
    Get dbname size
    """
    x = session.execute(
        f'SELECT table_name AS "Table", (data_length + index_length) AS "Size (B)" FROM information_schema.TABLES WHERE table_schema = "{dbname}" ORDER BY (data_length + index_length) DESC'
    ).fetchall()
    db_size = 0
    for tup in x:
        db_size += tup[1]
    formatted = humanFormat(db_size) + "B"
    return formatted


def getTableLength(session, table):
    # get table length
    number_of_rows = session.execute(
        f"SELECT id FROM {table} ORDER BY id DESC LIMIT 1"
    ).fetchall()[0][0]
    return number_of_rows


def convertPropsToORM(props):
    """
    Converts props to set of Results's
    """
    tqdm.write(colorEh("Packaging props ..."))
    rows = []
    total = countNestedDicts(props)
    with tqdm(
        total=total, leave=False, unit="tic", dynamic_ncols=True, desc="cycle"
    ) as bar:
        for sym in props:
            for exc in props[sym]:
                # create row object
                result = Results(
                    symbol=props[sym][exc]["symbol"],
                    exchange=props[sym][exc]["exchange"],
                    timestamp=props[sym][exc]["timestamp"],
                    ask=props[sym][exc]["ask"],
                    askVolume=props[sym][exc]["askVolume"],
                    average=props[sym][exc]["average"],
                    baseVolume=props[sym][exc]["baseVolume"],
                    bid=props[sym][exc]["bid"],
                    close=props[sym][exc]["close"],
                    datetime=props[sym][exc]["datetime"],
                    batch=props[sym][exc]["batch"],
                    dx=props[sym][exc]["dx"],
                    high=props[sym][exc]["high"],
                    last=props[sym][exc]["last"],
                    low=props[sym][exc]["low"],
                    open=props[sym][exc]["open"],
                    percentage=props[sym][exc]["percentage"],
                    previousClose=props[sym][exc]["previousClose"],
                    quoteVolume=props[sym][exc]["quoteVolume"],
                    vwap=props[sym][exc]["vwap"],
                )
                rows.append(result)
                bar.update(1)
        return rows


def convertSpreadsToORM(spreads):
    """
    Converts spreads to set of spread table rows
    """
    tqdm.write(colorEh("Packaging spreads ..."))
    rows = []
    total = countNestedDicts(spreads)
    with tqdm(
        total=total, leave=False, unit="tic", dynamic_ncols=True, desc="cycle"
    ) as bar:
        for sym in spreads:
            for combo in spreads[sym]:
                # create row object
                result = Spread(
                    symbol=combo["symbol"],
                    buy=combo["buy"],
                    sell=combo["sell"],
                    time=combo["time"],
                    batch=combo["batch"],
                    timestamp=combo["timestamp"],
                    buy_ask=combo["buy_ask"],
                    buy_bid=combo["buy_bid"],
                    buy_price=combo["buy_price"],
                    sell_ask=combo["sell_ask"],
                    sell_bid=combo["sell_bid"],
                    sell_price=combo["sell_price"],
                    fees=combo["fees"],
                    no_fees=combo["no_fees"],
                    spread_w_fees=combo["spread_w_fees"],
                    liquidity=combo["liquidity"],
                    quote_order_size=combo["quote_order_size"],
                    speedup=combo["speedup"],
                )
                rows.append(result)
                bar.update(1)
        return rows


def saveProps(props, session):
    """
    Save props to database
    """
    start = now()
    rows = convertPropsToORM(props)
    session.bulk_save_objects(rows)
    session.commit()
    tqdm.write(
        colorGood(
            f"Wrote {countNestedDicts(props)} records to 'results' in {now()-start:.2f}s (now {getTableLength(session,'results'):,} records long). DB now {getDBSize(session,'symbols')}."
        )
    )


def saveSpreads(spreads, session):
    """
    Save spreads to database
    """
    start = now()
    rows = convertSpreadsToORM(spreads)
    session.bulk_save_objects(rows)
    session.commit()
    tqdm.write(
        colorGood(
            f"Wrote {countNestedDicts(spreads)} records to 'spreads' in {now()-start:.2f}s (now {getTableLength(session,'spreads'):,} records long). DB now {getDBSize(session,'symbols')}."
        )
    )


def saveBoth(props, spreads, session):
    """
    Save spreads to database
    """
    proptime = now()
    rows = convertSpreadsToORM(spreads)
    session.bulk_save_objects(rows)

    rows = convertPropsToORM(props)
    session.bulk_save_objects(rows)

    session.commit()

    proptime = now() - proptime
    tqdm.write(
        colorGood(
            f"Wrote {countNestedDicts(spreads)} records to 'spreads' (now {getTableLength(session,'spreads'):,} records long).\nWrote {countNestedDicts(props)} records to 'results' (now {getTableLength(session,'results'):,} records long).\n* Took {proptime:.2f}s, DB now {getDBSize(session,'symbols')}."
        )
    )


def saveIndefinitely(Session, interval=0):
    """
    Takes a sessionmaker object, create session, and save every interval seconds
    """
    session = Session()
    if interval < 10 and interval != 0:
        interval = 10
    start_time = nowD()
    # create propagator
    beehive = hive.Hive(2)
    while True:
        # create props
        props, globals()["latest_raw_batch"] = beehive.pgator.propagate(
            beehive.idynamics
        )
        saveProps(props, session)
        # scan one cycle
        spreads = beehive.scanFull(props)
        saveSpreads(spreads, session)
        globals()["latest_solved_batch"] = globals()[
            "latest_raw_batch"
        ]  # set latest batch once solved
        # saveBoth(props, spreads, session)
        print(f"* uptime: {nowD()-start_time}\n")
        timer(interval)


def getRawLatest(session):
    """
    Get latest data from the price tickers.
    """
    latest = None
    if globals()["latest_raw_batch"]:
        latest = Results.findBy(
            session, True, batch=globals()["latest_raw_batch"].strftime(TIME_FORMAT)
        )
    return latest


def getSpreadsLatest(session):
    """
    Get latest data from the
    """
    latest = None
    if globals()["latest_solved_batch"]:
        latest = Spread.findBy(
            session, True, batch=globals()["latest_solved_batch"].strftime(TIME_FORMAT)
        )
    return latest


def findNearestBatchTo(session, cls, batch):
    # batch must be in datetime string format
    batch = datetime.strptime(batch, TIME_FORMAT)
    uniques = cls.findUniqueBatches(session)
    closest = min(uniques, key=lambda d: abs(d - batch))
    return closest


def getNearestBatchTo(session, cls, batch):
    # batch must be in datetime string format
    closest = findNearestBatchTo(session, cls, batch)
    closest_record = cls.findBy(session, True, batch=closest.strftime(TIME_FORMAT))
    return closest_record


def getBatchesInRange(session, cls, start, end):
    betweens = cls.findBetweenDatetimes(session, True, start=start, end=end)
    return betweens


if __name__ == "__main__":
    latest_batch = None
    # Create the parser
    parser = argparse.ArgumentParser(
        description="Handle database connections for SAMWise"
    )
    parser.add_argument("-u", "--user", help="username", default="test")
    parser.add_argument("-p", "--pwd", help="password", default="test")
    parser.add_argument("-H", "--host", help="host", default="localhost")
    parser.add_argument("-P", "--port", help="port", default="3306")
    parser.add_argument("-d", "--database", help="database", default="symbols")
    parser.add_argument(
        "-r", "--reset", help="reset the database", default=False, action="store_true"
    )

    args = parser.parse_args()

    # create engine
    engine = buildEngine(
        connection="mysql",
        username=args.user,
        password=args.pwd,
        host=args.host,
        port=args.port,
        database=args.database,
    )

    # reset database
    if args.reset:
        resetTables(engine)

    # create session maker and session
    Session = createSessionMaker(engine)
    session = Session()
    # save indef
    saveIndefinitely(session)
