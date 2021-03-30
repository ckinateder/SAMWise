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
      latestResults:[],
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
  updateResults(){
    DashDataService.getResults().then(res => res.data).then(data => {
      let cplengths = { ...data};
      this.setState({latestResults: items(cplengths)});
    });
  }  

  renderResults() {
    return <table className="table table-bordered table-sm table-hover">
            <thead>
              <th scope="col">
                Symbol
              </th>
              <th scope="col">
                Exchange
              </th>
              <th scope="col">
                Ask
              </th>
              <th scope="col">
                Bid
              </th>
              <th scope="col">
                Base Volume
              </th>
              <th scope="col">
                Quote Volume
              </th>
            </thead>
            <tbody>
              {this.state.latestResults.map(function(o,i) {
                return <tr key={i} scope="row">
                        <td>{o.symbol}</td>
                        <td>{o.exchange}</td>
                        <td>${o.ask}</td>
                        <td>${o.bid}</td>
                        <td>{(o.baseVolume)? o.baseVolume: "--"}</td>
                        <td>{(o.quoteVolume)? o.quoteVolume: "--"}</td>
                      </tr>
              })}
            </tbody>
          </table>
  }

  getData = () => {
    // do something to fetch data from a remote API.
    this.updateInfo();
    this.updateResults();
  }

  render() {
    return (
      <div>
        <div className="results-table-div table-responsive">       
          {this.renderResults()}   
        </div>
        <footer className="bg-dark text-center text-white text-lg-start foot">
          {this.state.info.footer}
        </footer>
      </div>
    );
  }
}

export default Dash;