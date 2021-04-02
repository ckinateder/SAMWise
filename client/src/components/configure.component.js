import DashDataService from "../services/dash.service"
import { Link } from "react-router-dom";
import React, { Component } from "react";
import {items, commaFormat} from "../helpers/tools.helpers";
import http from "../http-common";

class Configure extends Component {
  /*
    declare a member variable to hold the interval ID
    that we can reference later.
  */
  constructor(props) {
    super(props);
    this.intervalID = 0;
    
    this.state = {
      url: http.defaults.baseURL, // remove end slug
      interval: 0
    }
    
    this.handleChangeURL = this.handleChangeURL.bind(this);
    this.handleSubmit = this.handleSubmit.bind(this);

  }
  handleChangeURL(event) {
    this.setState({url: event.target.value});
  }

  handleSubmit(event) {
    event.preventDefault();
    DashDataService.setBaseURL(this.state.url);
    localStorage.setItem("baseURL", this.state.url);
    console.log(localStorage.getItem("baseURL"));
  }
  
  updateInterval(){
    DashDataService.getInterval().then(res => res.data).then(data => {
      this.setState({interval: data});
    });
  }

  componentDidMount() {
    this.getData();
    this.intervalID = setInterval(this.getData.bind(this), 1000);
  }

  componentWillUnmount() {
    clearInterval(this.intervalID);
  }
  getBaseURL() {
    return this.state.url;
  }

  getData = () => {
    // do something to fetch data from a remote API.
    this.updateInterval();
  }

  render() {
    return (
      <div className="configure-form">
        <div className="form-group">
          <form onSubmit={this.handleSubmit}>
            <label>
              Server URL:
            </label>
            <input type="text" className="form-control" value={this.state.url} onChange={this.handleChangeURL} />
            
          <div>
            <input type="submit" className="btn btn-primary" value="Apply" />
          </div>
        </form>
        </div>
      </div>
    );
  }
}

export default Configure;