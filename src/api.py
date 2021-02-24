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
        table = request.args.get("table")
        idstart = request.args.get("idstart")
        idend = request.args.get("idend")
        row = getRowByID(db=database, table=table, id=[idstart, idend])

        return {"data": row}, 200  # return data with 200 OK


class Latest(Resource):
    # methods go here
    # def get(self):
    #    return {"data": "OK (latest)"}, 200  # return data and 200 OK code

    def get(self):
        row = getRowByID(db=database, table="latest", special="all")

        return {"data": row}, 200  # return data with 200 OK


class Spreads(Resource):
    # methods go here
    def get(self):
        return {"data": "OK (spreads)"}, 200  # return data and 200 OK code


api.add_resource(Historical, "/historical")  # '/historical' is our entry point
api.add_resource(Latest, "/latest")  # '/latest' is our entry point
api.add_resource(Spreads, "/spreads")  # '/spreads' is our entry point


if __name__ == "__main__":
    # start database
    database = initializeDB("symbols")
    app.run()
