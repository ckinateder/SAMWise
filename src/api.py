import ast
import json
from datetime import datetime
from pprint import pprint

import ccxt
import pandas as pd
from flask import Flask, request
from flask_restful import Api, Resource
from mysql.connector import Error, connect

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
        """
        bottom = request.args.get("bottom")
        top = request.args.get("top")
        sortby = request.args.get("sortby")
        print(bottom, top)

        if not bottom:
            top = nowD()

        if not bottom and not top:
            return {"data": "No range provided"}, 400  # return data with 400 BAD
        elif not sortby:
            sortby = "datetime"
        row = getRowInRange(
            db=database, table="results", key=sortby, rang=[bottom, top]
        )
        return {"data": row}, 200  # return data with 200 OK


class Latest(Resource):
    # methods go here
    def get(self):
        row = getRowInRange(
            db=database, table="latest", key="datetime", rang=None, special="all"
        )

        return {"data": row}, 200  # return data with 200 OK


class Spreads(Resource):
    # methods go here
    def get(self):
        return {"data": "OK (spreads)"}, 200  # return data and 200 OK code


api.add_resource(Historical, "/api/historical")  # '/historical' is our entry point
api.add_resource(Latest, "/api/latest")  # '/latest' is our entry point
api.add_resource(Spreads, "/api/spreads")  # '/spreads' is our entry point


if __name__ == "__main__":
    # start database
    database = initializeDB("symbols")
    app.run()
