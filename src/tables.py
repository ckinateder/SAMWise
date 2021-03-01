from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String
from sqlalchemy.sql.sqltypes import BIGINT, DECIMAL, DateTime, VARCHAR
from beautifultable import BeautifulTable

Base = declarative_base()


class TickerInfo(Base):
    __tablename__ = "results"

    id = Column(Integer, primary_key=True, autoincrement=True)

    symbol = Column(VARCHAR(40))
    exchange = Column(VARCHAR(40))
    timestamp = Column(BIGINT)

    ask = Column(DECIMAL(20, 8))
    askVolume = Column(DECIMAL(20, 8))
    average = Column(DECIMAL(20, 8))
    baseVolume = Column(DECIMAL(20, 8))
    bid = Column(DECIMAL(20, 8))
    close = Column(DECIMAL(20, 8))

    datetime = Column(DateTime)
    batch = Column(DateTime)

    dx = Column(DECIMAL(20, 8))
    high = Column(DECIMAL(20, 8))
    last = Column(DECIMAL(20, 8))
    low = Column(DECIMAL(20, 8))
    open = Column(DECIMAL(20, 8))
    percentage = Column(DECIMAL(20, 8))
    previousClose = Column(DECIMAL(20, 8))
    quoteVolume = Column(DECIMAL(20, 8))
    vwap = Column(DECIMAL(20, 8))

    def __init__(
        self,
        symbol,
        exchange,
        timestamp,
        ask,
        askVolume,
        average,
        baseVolume,
        bid,
        close,
        datetime,
        batch,
        dx,
        high,
        last,
        low,
        open,
        percentage,
        previousClose,
        quoteVolume,
        vwap,
    ):
        self.symbol = symbol
        self.exchange = exchange
        self.timestamp = timestamp

        self.ask = ask
        self.askVolume = askVolume
        self.average = average
        self.baseVolume = baseVolume
        self.bid = bid
        self.close = close

        self.datetime = datetime
        self.batch = batch

        self.dx = dx
        self.high = high
        self.last = last
        self.low = low
        self.open = open
        self.percentage = percentage
        self.previousClose = previousClose
        self.quoteVolume = quoteVolume
        self.vwap = vwap

    def __repr__(self):
        tostr = BeautifulTable()
        tostr.rows.append(["ID", self.id])
        tostr.rows.append(["symbol", self.symbol])
        tostr.rows.append(["exchange", self.exchange])
        tostr.rows.append(["ask", self.ask])
        tostr.rows.append(["bid", self.bid])
        tostr.columns.header = ["key", "value"]
        return str(tostr)
