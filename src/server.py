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


class Historical(Resource):
    # methods go heredef
    def get(self):
        """
        Calls
        GET 127.0.0.1:5000/api/historical?bottom=2021-02-23 21:00:00&top=2021-02-24 11:34:07.495980&sortby=datetime

        bottom = request.args.get("bottom")
        top = request.args.get("top")
        sortby = request.args.get("sortby")
        closest_to = request.args.get("closest_to")  # optional

        if closest_to:
            rows = getBatchNearestTo(db_client, "results", closest_to)
            # print(len(rows))
            return {"data": rows}, 200  # return data with 200 OK
        else:
            if not sortby:
                sortby = "batch"
            if not bottom:
                top = nowD()
            if not top:
                return {"data": "No range provided"}, 400  # return data with 400 BAD
            rows = getRowInRange(
                db=db_client, table="results", key=sortby, rang=[bottom, top]
            )
            # print(len(rows))
            return {"data": rows}, 200  # return data with 200 OK"""
        pass


class Latest(Resource):
    # methods go here
    def get(self):
        row = getLatest(session)
        return {"data": row}, 200  # return data with 200 OK


class Spreads(Resource):
    # methods go here
    def get(self):
        return {"data": "OK (spreads)"}, 200  # return data and 200 OK code


api.add_resource(Historical, "/api/historical")  # '/historical' is our entry point
api.add_resource(Latest, "/api/latest")  # '/latest' is our entry point
api.add_resource(Spreads, "/api/spreads")  # '/spreads' is our entry point


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
    Session = createSessionMaker(engine)
    session = Session()

    # create threads
    apiThread = threading.Thread(target=runAPI, name="api")
    dataThread = threading.Thread(target=saveIndefinitely, args=(session,), name="data")
    # start threads
    dataThread.start()
    tqdm.write("Started DATA server ...")
    apiThread.start()
    tqdm.write("Started API server ...")
