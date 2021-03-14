from sqlalchemy import Column, String, Integer, Date, Table, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql.elements import and_
from sqlalchemy.sql.sqltypes import BIGINT, VARCHAR, DateTime, Float

import decimal
from datetime import *

from helper import *

Base = declarative_base()

# define relationships
"""
batch_association = Table(
    'results_spread_summary', Base.metadata,
    Column('movie_id', Integer, ForeignKey('movies.id')),
    Column('actor_id', Integer, ForeignKey('actors.id'))
)
"""


class Results(Base):
    __tablename__ = "results"

    id = Column(Integer, autoincrement=True, primary_key=True)
    batch = Column(DateTime)

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

    @classmethod
    def findBetweenDatetimes(cls, session, serialize, start, end):
        q = session.query(cls).filter(and_(cls.batch >= start, cls.batch <= end)).all()
        if serialize:
            q = serializeQuery(q)
        return q

    def __repr__(self):
        tostr = f"<RESULTS @ id={self.id}, symbol={self.symbol}, exchange={self.exchange}, ask={float(self.ask)}, bid={float(self.bid)}>"
        return tostr


class Spread(Base):
    __tablename__ = "spreads"

    id = Column(Integer, autoincrement=True, primary_key=True)
    batch = Column(DateTime)

    symbol = Column(VARCHAR(20))

    buy = Column(VARCHAR(40))
    sell = Column(VARCHAR(40))

    time = Column(DateTime)
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
    def findBetweenDatetimes(cls, session, serialize, start, end):
        q = session.query(cls).filter(and_(cls.batch >= start, cls.batch <= end)).all()
        if serialize:
            q = serializeQuery(q)
        return q

    @classmethod
    def findUniqueBatches(cls, session):
        query = session.query(cls.batch.distinct().label("batch"))
        uniques = [row.batch for row in query.all()]
        return uniques

    def __repr__(self):
        tostr = f"<SPREAD @ id={self.id}, symbol={self.symbol}, buy={self.buy}, sell={self.sell}, net spread={float(self.spread_w_fees)}>"
        return tostr


class Summary(Base):
    __tablename__ = "summary"
    id = Column(Integer, autoincrement=True, primary_key=True)
    batch = Column(DateTime)

    symbol = Column(VARCHAR(20))
    spread_w_fees = Column(Float)  # only the top spread
    speedup = Column(Float)  # only top spread speedup

    buy = Column(VARCHAR(40))  # only top
    sell = Column(VARCHAR(40))  # only top

    liquidity = Column(Float)  # only top spread
    profitable_pairs = Column(Integer)  # number of profitable pairs

    @classmethod
    def findBy(cls, session, serialize, **kwargs):
        q = session.query(cls).filter_by(**kwargs).all()
        if serialize:
            q = serializeQuery(q)
        return q

    @classmethod
    def findBetweenDatetimes(cls, session, serialize, start, end):
        q = session.query(cls).filter(and_(cls.batch >= start, cls.batch <= end)).all()
        if serialize:
            q = serializeQuery(q)
        return q

    @classmethod
    def findUniqueBatches(cls, session):
        query = session.query(cls.batch.distinct().label("batch"))
        uniques = [row.batch for row in query.all()]
        return uniques

    def __repr__(self):
        tostr = f"<SUMMARY @ batch={self.batch}, symbol={self.symbol}, net spread={float(self.spread_w_fees)}>"
        return tostr
