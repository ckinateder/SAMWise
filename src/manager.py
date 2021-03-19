import tqdm, psutil, sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from helper import *
from tables import Base, Results, Spread, Summary
import hive
from pprint import *

# statics

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
    logs.debug(colorBad("Resetting database ..."))
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


def getTableSize(session, dbname, table):
    """
    Get table size in dbname
    """
    x = session.execute(
        f'SELECT table_name AS "Table", (data_length + index_length) AS "Size (B)" FROM information_schema.TABLES WHERE table_schema = "{dbname}" ORDER BY (data_length + index_length) DESC'
    ).fetchall()
    for st in x:
        if table in list(st):
            formatted = humanFormat(st[1]) + "B"

    return formatted


def getTableLength(session, table):
    # get table length
    try:
        number_of_rows = session.execute(
            f"SELECT id FROM {table} ORDER BY id DESC LIMIT 1"
        ).fetchall()[0][0]
    except IndexError:
        number_of_rows = 0
    return number_of_rows


# class
class DatabaseManager:
    def __init__(self, default_session):
        self.current = "starting"  # current process
        self.start_time = nowD()
        self.uptime = 0

        # create propagator
        self.beehive = hive.Hive(minnum=2)
        # lengths
        self.lengths = {
            "results": getTableLength(default_session, "results"),
            "spreads": getTableLength(default_session, "spreads"),
            "summary": getTableLength(default_session, "summary"),
        }
        self.db_size = getDBSize(default_session, "samwise")
        self.latest_summary = []

    def findNearestBatchTo(self, session, cls, batch):
        # batch must be in datetime string format
        batch = datetime.strptime(batch, TIME_FORMAT)
        uniques = cls.findUniqueBatches(session)
        closest = min(uniques, key=lambda d: abs(d - batch))
        return closest

    def getNearestBatchTo(self, session, cls, batch):
        # batch must be in datetime string format
        closest = self.findNearestBatchTo(session, cls, batch)
        closest_record = cls.findBy(session, True, batch=closest.strftime(TIME_FORMAT))
        return closest_record

    def getBatchesInRange(self, session, cls, start, end):
        betweens = cls.findBetweenDatetimes(session, True, start=start, end=end)
        return betweens

    def getRawLatest(self, session, symbol=None, exchange=None):
        """
        Get latest data from the price tickers.
        """
        latest = None
        batch = session.query(Results).order_by(Results.id.desc()).first().batch
        if symbol and not exchange:
            latest = Results.findBy(session, True, batch=batch, symbol=symbol)
        elif exchange and not symbol:
            latest = Results.findBy(session, True, batch=batch, exchange=exchange)
        elif symbol and exchange:
            latest = Results.findBy(
                session, True, batch=batch, symbol=symbol, exchange=exchange
            )
        else:
            latest = Results.findBy(session, True, batch=batch)
        return latest

    def getSpreadsLatest(self, session):
        """
        Get latest data from the
        """
        latest = None
        batch = session.query(Spread).order_by(Spread.id.desc()).first().batch
        latest = Spread.findBy(
            session,
            True,
            batch=batch,
        )
        return latest

    def convertPropsToORM(self, props):
        """
        Converts props to set of Results's
        """
        logs.debug(colorEh("Packaging props ..."))
        rows = []
        total = countNestedDicts(props)
        with tqdm(
            disable=BARSDISABLED,
            total=total,
            leave=False,
            unit="tic",
            dynamic_ncols=True,
            desc="cycle",
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

    def convertSpreadsToORM(self, spreads):
        """
        Converts spreads to set of spread table rows
        """
        logs.debug(colorEh("Packaging spreads ..."))
        rows = []
        total = countNestedDicts(spreads)
        with tqdm(
            disable=BARSDISABLED,
            total=total,
            leave=False,
            unit="tic",
            dynamic_ncols=True,
            desc="cycle",
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

    def spreadsToSummary(self, spreads):
        """
        Takes a spreads nested dict and creates the summary table
        """
        rows = []
        for symbol in spreads:
            if spreads[symbol]:
                numberof = len(spreads[symbol])
                top = spreads[symbol][0]
                if top["symbol"] != "BCH/USD":  # bch is broken rn
                    row = Summary(
                        batch=top["batch"],
                        symbol=top["symbol"],
                        spread_w_fees=top["spread_w_fees"],
                        speedup=top["speedup"],
                        profitable_pairs=numberof,
                        buy=top["buy"],
                        sell=top["sell"],
                        liquidity=top["liquidity"],
                    )
                    rows.append(row)

        return rows

    def saveProps(self, props, session):
        """
        Save props to database
        """
        start = now()
        rows = self.convertPropsToORM(props)
        session.bulk_save_objects(rows)
        session.commit()
        self.lengths["results"] = getTableLength(session, "results")
        logs.debug(
            colorGood(
                f"Wrote {len(rows)} records to 'results' in {now()-start:.2f}s (now {getTableLength(session,'results'):,} records long)."
            )
        )

    def saveSpreads(self, spreads, session):
        """
        Save spreads to database
        """
        start = now()
        rows = self.convertSpreadsToORM(spreads)
        session.bulk_save_objects(rows)
        session.commit()
        self.lengths["spreads"] = getTableLength(session, "spreads")
        logs.debug(
            colorGood(
                f"Wrote {len(rows)} records to 'spreads' in {now()-start:.2f}s (now {getTableLength(session,'spreads'):,} records long)."
            )
        )

    def saveBoth(self, props, spreads, session):
        """
        Save spreads to database
        """
        proptime = now()
        rows = self.convertSpreadsToORM(spreads)
        session.bulk_save_objects(rows)

        rows = self.convertPropsToORM(props)
        session.bulk_save_objects(rows)

        session.commit()

        proptime = now() - proptime
        logs.debug(
            colorGood(
                f"Wrote {len(rows)} records to 'spreads' (now {getTableLength(session,'spreads'):,} records long).\nWrote {countNestedDicts(props)} records to 'results' (now {getTableLength(session,'results'):,} records long).\n* Took {proptime:.2f}s, DB now {getDBSize(session,'samwise')}."
            )
        )

    def saveSummary(self, spreads, session):
        start = now()
        rows = self.spreadsToSummary(spreads)
        session.bulk_save_objects(rows)
        session.commit()
        self.lengths["summary"] = getTableLength(session, "summary")
        logs.debug(
            colorGood(
                f"Wrote {len(rows)} records to 'summary' in {now()-start:.2f}s (now {getTableLength(session,'summary'):,} records long)."
            )
        )
        return rows

    def updateUptime(self):
        self.uptime = strfdelta(nowD() - self.start_time)
        return self.uptime

    def saveIndefinitely(self, Session, interval=5):
        """
        Takes a sessionmaker object, create session, and save every interval seconds
        """
        session = Session()
        while True:
            # create props
            self.current = "propagating"
            props, latest_raw_batch = self.beehive.pgator.propagate(
                self.beehive.idynamics
            )

            self.current = "saving props"
            self.saveProps(props, session)
            # scan one cycle
            self.current = "solving"
            spreads = self.beehive.scanFull(props)

            # bounce
            self.current = "bouncing"
            self.beehive.bounce(spreads)

            self.current = "saving spreads"
            self.saveSpreads(spreads, session)
            # summarize one cycle
            self.current = "saving summary"
            self.latest_summary = self.saveSummary(spreads, session)
            self.latest_summary.sort(
                key=lambda x: x.liquidity, reverse=True
            )  # sort by liquidity

            self.db_size = getDBSize(session, "samwise")
            # print stats
            mem_usage = getMemUsage()
            logs.debug(
                colorHigh(
                    f"* ip: {getIP()} - usage: {mem_usage} - uptime: {self.updateUptime()} - db size: {self.db_size} *\n"
                )
            )

            # update on screen
            for t in trange(
                0,
                interval,
                disable=BARSDISABLED,
                leave=False,
                desc="timer",
                dynamic_ncols=True,
                position=1,
            ):
                self.current = f"waiting {interval-t}s"
                time.sleep(1)
