import DashDataService from "../services/dash.service"
import { Link } from "react-router-dom";
import React, { Component } from "react";
import JsonToTable from "react-json-to-table";

class Dash extends Component {
  /*
    declare a member variable to hold the interval ID
    that we can reference later.
  */
  intervalID;
  state = {
    info: {},
    lengths:{},
    latestSummary:[],
    latestResults:[],
    latestSpreads:[],
  }
  items(obj) {
    var i, arr = [];
    for(i in obj) {
      arr.push(obj[i]);
    }
    return arr;
   }
  componentDidMount() {
    /*
      need to make the initial call to getData() to populate
     data right away
    */
    this.getData();

    /*
      Now we need to make it run at a specified interval,
      bind the getData() call to `this`, and keep a reference
      to the invterval so we can clear it later.
    */
    this.intervalID = setInterval(this.getData.bind(this), 1000);
  }

  componentWillUnmount() {
    /*
      stop getData() from continuing to run even
      after unmounting this component
    */
    clearInterval(this.intervalID);
  }

  updateInfo(){
    DashDataService.getInfo().then(res => res.data).then(data => {
      this.setState({info: data});
    });
  }
  updateSummary(){
    DashDataService.getSummary().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({latestSummary: this.items(cplengths)});
    });
  }
  updateResults(){
    DashDataService.getResults().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({latestResults: this.items(cplengths)});
    });
  }
  updateSpreads(){
    DashDataService.getSpreads().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({latestSpreads: this.items(cplengths)});
    });
  }
  updateLengths(){
    DashDataService.getLengths().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({lengths: cplengths});
    });
  }
  renderRows(tbl) {
    console.log(tbl)
    return tbl.map(function(o,i) {
      {console.log(o)}
      return <tr key={i}>
              <td>{o.batch}</td>
              <td>{o.symbol}</td>
            </tr>
    });
  }

  getData = () => {
    // do something to fetch data from a remote API.
    this.updateInfo();
    this.updateSummary();
    this.updateResults();
    this.updateSpreads();
    this.updateLengths();
    console.log(this.state)
  }

  render() {
    return (
      <div>
        <div className="uptime">
          {this.state.info.uptime}
        </div>
        <div className="current">
          {this.state.info.current}
        </div>
        <div className="db-size">
          {this.state.info.db_size}
        </div>
        <div className="results-rows">
          {this.state.lengths.results}
        </div>
        <div className="sys-info">
          {this.state.info.footer}
        </div>
        <div className="summary">   
        <table>
          <tbody>
            {this.renderRows(this.state.latestSummary)}
          </tbody>
        </table>
        </div>
      </div>
    );
  }
}

export default Dash;