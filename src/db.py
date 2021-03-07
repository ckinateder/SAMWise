import tqdm
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from helper import *
from tables import Base, Results, Spread, Summary

USER = "test"
PASS = "test"


def buildEngine(connection, username, password, host, port, database, echo=False):
    """
    Takes string params and returns an engine.
    props[sym] call: createSession("mysql", "test", "test", "localhost", "3306", "samwise")
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
