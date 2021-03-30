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
  

  renderSummary() {
    return <table className="table table-bordered table-sm table-hover">
            <thead>
              <th scope="col">
                Symbol
              </th>
              <th scope="col">
                Spread
              </th>
              <th scope="col">
                Speedup
              </th>
              <th scope="col">
                Buy
              </th>
              <th scope="col">
                Sell
              </th>
              <th scope="col">
                Liquidity
              </th>
            </thead>
            <tbody>
              {this.state.latestSummary.map(function(o,i) {
                {console.log(o)}
                return <tr key={i} scope="row">
                        <td>{o.symbol}</td>
                        <td>${o.spread_w_fees}</td>
                        <td>{o.speedup}%</td>
                        <td>{o.buy}</td>
                        <td>{o.sell}</td>
                        <td>{o.liquidity}</td>
                      </tr>
              })}
            </tbody>
          </table>
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
        <div className="summary-table-div table-responsive">          
          {this.renderSummary()}
        </div>
      </div>
    );
  }
}

export default Dash;