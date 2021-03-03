from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.sqltypes import BIGINT, DECIMAL, Float, VARCHAR, DateTime

Base = declarative_base()
import decimal
from datetime import *

from helper import *


class Results(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, autoincrement=True)

    symbol = Column(VARCHAR(40))
    exchange = Column(VARCHAR(40))
    timestamp = Column(BIGINT)

    ask = Column(Float)
    askVolume = Column(Float)
    average = Column(Float)
    baseVolume = Column(Float)
    bid = Column(Float)
    close = Column(Float)

    datetime = Column(DateTime)
    batch = Column(DateTime)

    dx = Column(Float)
    high = Column(Float)
    last = Column(Float)
    low = Column(Float)
    open = Column(Float)
    percentage = Column(Float)
    previousClose = Column(Float)
    quoteVolume = Column(Float)
    vwap = Column(Float)

    @classmethod
    def findBy(cls, session, serialize, **kwargs):
        q = session.query(cls).filter_by(**kwargs).all()
        if serialize:
            q = serializeQuery(q)
        return q

    @classmethod
    def findUniqueBatches(cls, session):
        query = session.query(cls.batch.distinct().label("batch"))
        uniques = [row.batch for row in query.all()]
        return uniques

    def __repr__(self):
        tostr = f"<RESULTS @ id={self.id}, symbol={self.symbol}, exchange={self.exchange}, ask={float(self.ask)}, bid={float(self.bid)}>"
        return tostr


class Spread(Base):
    __tablename__ = "spreads"

    id = Column(Integer, primary_key=True, autoincrement=True)

    symbol = Column(VARCHAR(20))

    buy = Column(VARCHAR(40))
    sell = Column(VARCHAR(40))

    time = Column(DateTime)
    batch = Column(DateTime)
    timestamp = Column(BIGINT)

    buy_ask = Column(Float)
    buy_bid = Column(Float)
    buy_price = Column(Float)

    sell_ask = Column(Float)
    sell_bid = Column(Float)
    sell_price = Column(Float)

    fees = Column(Float)
    no_fees = Column(Float)
    spread_w_fees = Column(Float)

    liquidity = Column(Float)

    quote_order_size = Column(Integer)
    speedup = Column(Float)

    @classmethod
    def findBy(cls, session, serialize, **kwargs):
        q = session.query(cls).filter_by(**kwargs).all()
        if serialize:
            q = serializeQuery(q)
        return q

    @classmethod
    def findUniqueBatches(cls, session):
        query = session.query(cls.batch.distinct().label("batch"))
        uniques = [row.batch for row in query.all()]
        return uniques