import logo from './logo.svg';
import React, { Component } from "react";
import Dash from "./components/dash.component";
import Results from "./components/results.component";
import Spreads from "./components/spreads.component";
import "bootstrap/dist/css/bootstrap.min.css";
import { Switch, Route, Link } from "react-router-dom";

import http from "./http-common";

import DashDataService from "./services/dash.service"
import './App.css';
import Configure from './components/configure.component';

class App extends Component {
  render() {
    return (
      <div>
        <nav className="navbar navbar-expand navbar-dark bg-purple">
          <a href="/" className="navbar-brand">
            SAMWise
          </a>
          <div className="navbar-nav mr-auto">
          <li className="nav-item">
              <Link to={"/dashboard"} className="nav-link">
                Dashboard
              </Link>
            </li>
            <li className="nav-item">
              <Link to={"/results"} className="nav-link">
                Results
              </Link>
            </li>
            <li className="nav-item">
              <Link to={"/spreads"} className="nav-link">
                Spreads
              </Link>
            </li>
            <li className="nav-item">
              <Link to={"/configure"} className="nav-link">
                Configure
              </Link>
            </li>
          </div>
          <div className="text-white">
          Routing requests to {http.defaults.baseURL} | Built by
            <a className="text-white" href="https://ckinateder.github.io/"> Calvin Kinateder</a>
          </div>
        </nav>
        <div>
          <Switch>
            <Route exact path={["/", "/dashboard"]} component={Dash} />
            <Route exact path="/results" component={Results} />
            <Route path="/spreads" component={Spreads} />
            <Route path="/configure" component={Configure} />
          </Switch>
        </div>
      </div>
      
    );
  }
}

export default App;