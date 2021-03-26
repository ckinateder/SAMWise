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
        supporteds = list(dbmanager.beehive.supported_idynamics.keys())
        for i in range(len(supporteds)):
            supporteds[i] = supporteds[i].name

        if dataThread.is_alive():
            current = dbmanager.current
            summary = dbmanager.latest_summary
        else:
            current = "dead"
            summary = []
        return {
            "data": {
                "uptime": dbmanager.updateUptime(),
                "lengths": dbmanager.lengths,
                "current": current,
                "dbsize": dbmanager.db_size,
                "summary": [  # serialize
                    {
                        "symbol": s.symbol,
                        "net spread": s.spread_w_fees,
                        "batch": s.batch,
                    }
                    for s in summary
                ],
                "num_profit": len(summary),
                "sysInfo": getInfo(),
                "exchanges": sorted(supporteds),
            }
        }, 200  # return data and 200 OK code


class Data(Resource):
    def get(self):
        """
        Get by symbol and exchange
        """
        query_session = Session()  # for querying

        if request.args.get("help"):
            # stringitize dynamic_commons
            helps = {}
            for key, item in dbmanager.beehive.dynamic_commons.items():
                helps[str(key)] = [str(i) for i in item]

            return {"you need to provide an symbol": "", "supported pairs": helps}, 200

        converted_args = convertMultiDict(request.args)  # do this to pass kwargs

        if not converted_args:
            return {"data": dbmanager.getRawLatest(query_session)}, 200  # return all

        queried = dbmanager.getRawLatest(query_session, **converted_args)
        if queried:
            return {"data": queried}, 200
        else:
            return {"data": None, "msg": "no records matching those specs"}, 200


class BackendSummary(Resource):
    def get(self):
        """
        Get latest summary
        """
        data = [
            row.serialize() for row in dbmanager.latest_summary
        ]  # serialize each row

        return {"data": data}, 200


class BackendResults(Resource):
    def get(self):
        """
        Get latest results
        """
        data = [row.serialize() for row in dbmanager.latest_raw]  # serialize each row

        return {"data": data}, 200


class BackendSpreads(Resource):
    def get(self):
        """
        Get latest results
        """
        data = [
            row.serialize() for row in dbmanager.latest_spreads
        ]  # serialize each row

        return {"data": data}, 200


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


# serving api for clients
api.add_resource(Status, "/api/v1/status")
api.add_resource(Data, "/api/v1/data")

# backend api for react
api.add_resource(BackendSummary, "/backend/summary")
api.add_resource(BackendResults, "/backend/results")
api.add_resource(BackendSpreads, "/backend/spreads")


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
    # intro
    # clear()
    intro()
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
