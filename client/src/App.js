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
  constructor(props) {
    super(props);
    this.intervalID = 0;
    this.state = {
      info: {},
      baseUrl: localStorage.getItem("baseURL")
    }

  }
  componentDidMount() {
    this.getData();
    this.intervalID = setInterval(this.getData.bind(this), 1000);
  }

  componentWillUnmount() {
    clearInterval(this.intervalID);
  }

  updateInfo(){
    DashDataService.getInfo().then(res => res.data).then(data => {
      this.setState({info: data});
    });
  }

  updateURL(){
      this.setState({baseUrl: localStorage.getItem("baseURL")});
  }

  getData = () => {
    // do something to fetch data from a remote API.
    this.updateInfo();
    this.updateURL();
  }

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
          {this.state.info.current} | Routing requests to <a className="text-white" href={this.state.baseUrl}> {(localStorage.getItem("baseURL"))}</a>
          </div>
        </nav>
        <div className="">
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