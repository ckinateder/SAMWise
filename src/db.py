import sys
import time
from datetime import date
from pprint import pprint

import ccxt
import tqdm
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from tqdm import *
import hive
import propagator
from helper import *
from tables import TickerInfo, Base

USER = "test"
PASS = "test"


def buildEngine(connection, username, password, host, port, database):
    """
    Takes string params and returns a session.
    props[sym] call: createSession("mysql", "test", "test", "localhost", "3306", "symbols")
    """
    engine = create_engine(
        f"{connection}://{username}:{password}@{host}:{port}/{database}", echo=True
    )
    return engine


def resetTables(engine):
    """
    Drop all tables and create them again
    """
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)


def createSessionMaker(engine):
    """
    Create a session from an engine
    """
    maker = sessionmaker(bind=engine)
    return maker


def convertPropsToORM(props):
    """
    Converts props to set of TickerInfo's
    """
    tqdm.write("Packaging props ...")
    rows = []
    total = 0
    for i in props:
        total += len(props[i])
    with tqdm(
        total=total, leave=False, unit="tic", dynamic_ncols=True, desc="cycle"
    ) as bar:
        for sym in props:
            for exc in props[sym]:
                # create row object
                row = TickerInfo(
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
                rows.append(row)
                bar.update(1)
        return rows


# create engine
engine = buildEngine(
    connection="mysql",
    username="test",
    password="test",
    host="localhost",
    port="3306",
    database="symbols",
)

# reset database
# resetTables(engine)

# create session maker
Session = createSessionMaker(engine)
session = Session()

# create propagator
pgator = propagator.Propagtor()
inverteds = pgator.getInvertedDynamicCommons()

# create props
props = pgator.propagate(inverteds)
rows = convertPropsToORM(props)

# bulk save
session.bulk_save_objects(rows)
session.commit()