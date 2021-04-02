import DashDataService from "../services/dash.service"
import { Link } from "react-router-dom";
import React, { Component } from "react";

import {items, commaFormat} from "../helpers/tools.helpers";

class Spreads extends Component {
  /*
    declare a member variable to hold the interval ID
    that we can reference later.
  */
  constructor(props) {
    super(props);
    this.intervalID = 0;
    
    this.state = {
      info: {},
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
  
  updateSpreads(){
    DashDataService.getSpreads().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({latestSpreads: items(cplengths)});
    });
  }
  renderSpreads() {
    try {   
    return <table className="table table-bordered table-sm table-hover">
            <thead>
              <th scope="col">
                Symbol
              </th>
              <th scope="col">
                Buy Exchange
              </th>
              <th scope="col">
                Sell Exchange
              </th>
              <th scope="col">
                Buy At
              </th>
              <th scope="col">
                Sell At
              </th>
              <th scope="col">
                Spread
              </th>
              <th scope="col">
                Speedup
              </th>
              <th scope="col">
                Liquidity
              </th>
              <th scope="col">
                Batch
              </th>
            </thead>
            <tbody>
              {this.state.latestSpreads.map(function(o,i) {
                return <tr key={i} scope="row">
                        <td>{o.symbol}</td>
                        <td>{o.buy}</td>
                        <td>{o.sell}</td>
                        <td>${o.sell_price}</td>
                        <td>${o.buy_price}</td>
                        <td>${o.spread_w_fees}</td>
                        <td>{o.speedup}%</td>
                        <td>{commaFormat(o.liquidity)}</td>
                        <td>{o.batch}</td>
                      </tr>
              })}
            </tbody>
          </table>
    }
    catch{
      return "Loading spreads ..."
    }
  }

  getData = () => {
    // do something to fetch data from a remote API.
    this.updateInfo();
    this.updateSpreads();
  }

  render() {
    return (
      <div>
        <div className="results-table-div table-responsive">          
          {this.renderSpreads()}
        </div>
        <footer className="bg-dark text-center text-white text-lg-start foot">
          {this.state.info.footer}
        </footer>
      </div>
    );
  }
}

export default Spreads;