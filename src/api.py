import json, ccxt
from datetime import datetime
from pprint import pprint

import hive
import propagator
import db
from flask import Flask
from flask_restful import Resource, Api, reqparse
import pandas as pd
import ast

app = Flask(__name__)
api = Api(app)


class Historical(Resource):
    # methods go here
    def get(self):
        return {"data": "OK (historical)"}, 200  # return data and 200 OK code


class Latest(Resource):
    # methods go here
    def get(self):
        return {"data": "OK (latest)"}, 200  # return data and 200 OK code


class Spreads(Resource):
    # methods go here
    def get(self):
        return {"data": "OK (spreads)"}, 200  # return data and 200 OK code


api.add_resource(Historical, "/historical")  # '/historical' is our entry point
api.add_resource(Latest, "/latest")  # '/latest' is our entry point
api.add_resource(Spreads, "/spreads")  # '/spreads' is our entry point


if __name__ == "__main__":
    app.run()