import ast
import json
import threading
from datetime import datetime
from pprint import pprint

import ccxt
import pandas as pd
from flask import Flask, request
from flask_restful import Api, Resource

import hive
import propagator
from db import *

app = Flask(__name__)
api = Api(app)


class Status(Resource):
    # methods go here
    def get(self):
        query_session = Session()
        rrows = getTableLength(query_session, "results")
        srows = getTableLength(query_session, "spreads")

        strin = f"'results' length: {rrows:,}\n'spreads' length: {srows:,}"
        return {"data": strin}, 200  # return data and 200 OK code


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
            closest_record = getNearestBatchTo(query_session, Results, closest_to)
            return {"data": closest_record}, 200  # return data with 200 OK
        else:
            rows = getBatchesInRange(query_session, Results, bottom, top)
            return {"data": rows}, 200  # return data with 200 OK


class RawLatest(Resource):
    # methods go here
    def get(self):
        query_session = Session()  # for querying
        row = getRawLatest(query_session)
        return {"data": row}, 200  # return data with 200 OK


class SpreadsFlex(Resource):
    # methods go here
    def get(self):
        return {"data": "OK (spreads)"}, 200  # return data and 200 OK code


class SpreadsLatest(Resource):
    # methods go here
    def get(self):
        query_session = Session()  # for querying
        row = getSpreadsLatest(query_session)
        return {"data": row}, 200  # return data and 200 OK code


"""
# add static status
@app.route("/")
def status():
    query_session = Session()
    rrows = query_session.query(Results).count()
    srows = query_session.query(Spread).count()

    strin = f"'results' length: {rrows:,}\n'spreads' length: {srows:,}"
    return strin
"""

api.add_resource(Status, "/api/status")  # '/api/status' is our entry point
api.add_resource(RawFlex, "/api/raw/flex")  # '/raw/flex' is our entry point
api.add_resource(RawLatest, "/api/raw/latest")  # '/raw/latest' is our entry point
api.add_resource(SpreadsFlex, "/api/spreads/flex")  # '/spreads/flex' is our entry point
api.add_resource(
    SpreadsLatest, "/api/spreads/latest"
)  # '/spreads/latest' is our entry point


def runAPI():
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
    # commandline args
    if args.reset:
        confirm = input("Are you sure you want to reset the DB? (Y/n) ").lower()
        if "y" in confirm:
            resetTables("symbols")

    # create session maker and session
    Session = createSessionMaker(engine)  # for saving

    # create threads
    apiThread = threading.Thread(target=runAPI, name="api")
    dataThread = threading.Thread(target=saveIndefinitely, args=(Session,), name="data")
    # start threads
    dataThread.start()
    tqdm.write("Started DATA server ...")
    apiThread.start()
    tqdm.write("Started API server ...")
