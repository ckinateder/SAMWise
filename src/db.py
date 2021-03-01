import sys
import time
from datetime import date
from pprint import pprint

import ccxt, decimal
import json
from sqlalchemy.sql.sqltypes import DateTime
import tqdm
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker
from tqdm import *
import hive
import propagator
from helper import *
from tables import Results, Base

USER = "test"
PASS = "test"


def buildEngine(connection, username, password, host, port, database):
    """
    Takes string params and returns a session.
    props[sym] call: createSession("mysql", "test", "test", "localhost", "3306", "symbols")
    """
    engine = create_engine(
        f"{connection}://{username}:{password}@{host}:{port}/{database}"  # , echo=True
    )
    return engine


def resetTables(engine):
    """
    Drop all tables and create them again
    """
    print("Resetting database ...")
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
    Converts props to set of Results's
    """
    tqdm.write("Packaging props ...")
    rows = []
    total = countProps(props)
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


def saveProps(props, session):
    """
    Save props to database
    """
    start = now()
    rows = convertPropsToORM(props)
    session.bulk_save_objects(rows)
    session.commit()
    tqdm.write(f"Wrote {countProps(props)} records to DB in {now()-start:.2f}s.")


def serializeQuery(query):
    """
    take the RESPONSE from a query and convert to json
    """
    result = []
    for q in query:
        pre = q.__dict__
        pre.pop("_sa_instance_state")
        for post in pre:
            if type(pre[post]) == decimal.Decimal:
                pre[post] = float(pre[post])
            elif isinstance(pre[post], datetime):
                pre[post] = pre[post].strftime(TIME_FORMAT)
        result.append(pre)
    return result


# create engine
engine = buildEngine(
    connection="mysql",
    username="test",
    password="test",
    host="localhost",
    port="3306",
    database="symbols",
)

# create propagator
pgator = propagator.Propagtor()
inverteds = pgator.getInvertedDynamicCommons()

# reset database
resetTables(engine)

# create session maker and session
Session = createSessionMaker(engine)
session = Session()

# create props
props = pgator.propagate(inverteds)
saveProps(props, session)

query = session.query(Results).filter_by(symbol="ETH/USD")

pprint(serializeQuery(query.all()))