import DashDataService from "../services/dash.service"
import { Link } from "react-router-dom";
import React, { Component } from "react";
import JsonToTable from "react-json-to-table";
import {items, commaFormat} from "../helpers/tools.helpers";
class Dash extends Component {
  /*
    declare a member variable to hold the interval ID
    that we can reference later.
  */
  constructor(props) {
    super(props);
    this.intervalID = 0;
    this.state = {
      info: {},
      lengths:{},
      latestSummary:[],
      latestResults:[],
      latestSpreads:[],
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
  updateSummary(){
    DashDataService.getSummary().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({latestSummary: items(cplengths)});
    });
  }
  updateResults(){
    DashDataService.getResults().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({latestResults: items(cplengths)});
    });
  }
  updateSpreads(){
    DashDataService.getSpreads().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({latestSpreads: items(cplengths)});
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
                return <tr key={i} scope="row">
                        <td>{o.symbol}</td>
                        <td>${o.spread_w_fees}</td>
                        <td>{o.speedup}%</td>
                        <td>{o.buy}</td>
                        <td>{o.sell}</td>
                        <td>{commaFormat(o.liquidity)}</td>
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
  }

  render() {
    return (
      <div>
        <div className="rundown">
          <div className="uptime">
            Uptime: {this.state.info.uptime}
          </div>
          <div className="current">
            Current task: {this.state.info.current}
          </div>
          <div className="row-counts">
            Results: {commaFormat(this.state.lengths.results)} <br></br>
            Spreads: {commaFormat(this.state.lengths.spreads)} <br></br>
            Summary: {commaFormat(this.state.lengths.summary)} <br></br>
            Total: {commaFormat(this.state.lengths.results+this.state.lengths.spreads+this.state.lengths.summary)} ({this.state.info.db_size}) <br></br>
          </div>     
          
        </div>
        <div className="summary-table-div table-responsive">          
          {this.renderSummary()}
        </div>
        <footer className="bg-dark text-center text-white text-lg-start foot">
          {this.state.info.footer}
        </footer>
      </div>
    );
  }
}

export default Dash;