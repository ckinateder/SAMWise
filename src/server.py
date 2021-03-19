import threading
import webbrowser
import logging

from flask import Flask, request, render_template
from flask_restful import Api, Resource

import manager
import analzye
from helper import strfdelta, nowD
from tables import *
import argparse
from pprint import pprint

app = Flask(__name__)
api = Api(app)

# turn off page gets
flask_log = logging.getLogger("werkzeug")
flask_log.setLevel(logging.ERROR)


class Status(Resource):
    # methods go here
    def get(self):
        return {
            "data": {
                "status": "unknown (probably running)",
                "lengths": dbmanager.lengths,
                "size": dbmanager.db_size,
                "uptime": dbmanager.updateUptime(),
            }
        }, 200  # return data and 200 OK code


class Data(Resource):
    def get(self):
        query_session = Session()  # for querying
        symbol = request.args.get("symbol")
        exchange = request.args.get("exchange")
        if not symbol or not exchange:
            # help
            exchanges = []
            for i in list(dbmanager.beehive.idynamics.keys()):
                exchanges.append(i.name)
            return {
                "supported symbols": list(dbmanager.beehive.dynamic_commons.keys()),
                "supported exchanges": exchanges,
            }, 200

        queried = dbmanager.getRawLatest(query_session, symbol, exchange)
        print(queried)
        if queried:
            return {"data": queried}, 200
        else:
            return {"data": None, "msg": "no records matching those specs"}, 200


class RawFlex(Resource):
    # methods go heredef
    def get(self):
        """
        Calls
        GET 127.0.0.1:5000/api/flex?bottom=2021-02-23 21:00:00&top=2021-02-24 11:34:07.495980&sortby=datetime
        """
        query_session = Session()  # for querying
        bottom = request.args.get("bottom")
        top = request.args.get("top")
        closest_to = request.args.get("closest_to")  # optional

        if closest_to:
            closest_record = dbmanager.getNearestBatchTo(
                query_session, Results, closest_to
            )
            return {"data": closest_record}, 200  # return data with 200 OK
        else:
            rows = dbmanager.getBatchesInRange(query_session, Results, bottom, top)
            return {"data": rows}, 200  # return data with 200 OK


class RawLatest(Resource):
    # methods go here
    def get(self):
        query_session = Session()  # for querying
        row = dbmanager.getRawLatest(query_session)
        return {"data": row}, 200  # return data with 200 OK


class SpreadsFlex(Resource):
    # methods go here
    def get(self):
        return {"data": "OK (spreads)"}, 200  # return data and 200 OK code


class SpreadsLatest(Resource):
    # methods go here
    def get(self):
        query_session = Session()  # for querying
        row = dbmanager.getSpreadsLatest(query_session)
        return {"data": row}, 200  # return data and 200 OK code


# static pages
@app.route("/")
def dynamicStatus():
    supporteds = list(dbmanager.beehive.supported_idynamics.keys())
    for i in range(len(supporteds)):
        supporteds[i] = supporteds[i].name
    mem_usage = getMemUsage()
    # strin = f"'results' length: {resultsrows:,}<br>'spreads' length: {spreadsrows:,}<br>'summary' length: {summaryrows:,}<br>uptime: {strfdelta(nowD() - START_TIME)}<br>current task: {current}"
    num_profit = ""
    if dataThread.is_alive():
        current = dbmanager.current
        summary = dbmanager.latest_summary
    else:
        current = "dead"
        summary = []
    if dbmanager.latest_summary:
        num_profit = f"{len(dbmanager.latest_summary)} profitable symbols!"
    return render_template(
        "status.html",
        resultsrows=format(dbmanager.lengths["results"], ","),
        spreadsrows=format(dbmanager.lengths["spreads"], ","),
        summaryrows=format(dbmanager.lengths["summary"], ","),
        uptime=dbmanager.updateUptime(),
        current=current,
        dbsize=dbmanager.db_size,
        summary=summary,
        num_profit=num_profit,
        footer=getInfo(),
        exchanges=sorted(supporteds),
        bouncers=dbmanager.beehive.bouncers,
    )
    # return strin


@app.route("/exchanges", methods=["POST"])
def editExchanges():
    dbmanager.beehive.sliceFromIdynamics(
        request.form.getlist("check")
    )  # change idynamics, this ONLY messes with scanners rn. we want to change it to only messing with bouncers
    return "Done"


@app.route("/add_bouncer", methods=["POST"])
def addBouncer():
    dbmanager.beehive.addBouncer(
        request.form.getlist("add_bouncer")[0],
        request.form.getlist("add_bouncer")[1],
    )
    return "Done"


api.add_resource(Data, "/api/v1/data")  # '/raw/flex' is our entry point
api.add_resource(RawFlex, "/api/raw/flex")  # '/raw/flex' is our entry point
api.add_resource(RawLatest, "/api/raw/latest")  # '/raw/latest' is our entry point
api.add_resource(SpreadsFlex, "/api/spreads/flex")  # '/spreads/flex' is our entry point
api.add_resource(
    SpreadsLatest, "/api/spreads/latest"
)  # '/spreads/latest' is our entry point


def openBrowser():
    webbrowser.open_new("http://localhost:5000/")


def serveIndefinitely():
    # threading.Timer(1, openBrowser).start()
    app.run(host="0.0.0.0", port=5000, debug=False)


if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(
        description="Handle database connections for SAMWise"
    )
    parser.add_argument("-u", "--user", help="username", default="test")
    parser.add_argument("-p", "--pwd", help="password", default="test")
    parser.add_argument("-H", "--host", help="host", default="localhost")
    parser.add_argument("-P", "--port", help="port", default="3306")
    parser.add_argument("-d", "--database", help="database", default="samwise")
    parser.add_argument("-t", "--timer", help="timer", default=5)
    parser.add_argument(
        "-r", "--reset", help="reset the database", default=False, action="store_true"
    )
    args = parser.parse_args()
    # create engine
    engine = manager.buildEngine(
        connection="mysql",
        username=args.user,
        password=args.pwd,
        host=args.host,
        port=args.port,
        database=args.database,
    )
    # commandline args
    if args.reset:
        confirm = input("Are you sure you want to reset the DB? (Y/n) ").lower()
        if "y" in confirm:
            manager.resetTables(engine)

    # create session maker and session
    Session = manager.createSessionMaker(engine)  # for saving
    dbmanager_sess = Session()
    dbmanager = manager.DatabaseManager(dbmanager_sess)

    # create threads
    apiThread = threading.Thread(target=serveIndefinitely)
    dataThread = threading.Thread(
        target=dbmanager.saveIndefinitely, args=(Session, int(args.timer))
    )
    analyzeThread = threading.Thread(
        target=analzye.analyzeIndefinitely,
        args=(
            engine,
            Session,
        ),
    )

    # start threads
    dataThread.start()
    logs.debug("Started DATA thread ...")
    apiThread.start()
    logs.debug("Started API thread ...")
    # analyzeThread.start()
    # logs.debug("Started ANALYZE thread ...")
