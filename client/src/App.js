import logo from './logo.svg';
import React, { useState, useEffect } from 'react';
import Dash from "./components/dash.component";
import "bootstrap/dist/css/bootstrap.min.css";

import DashDataService from "./services/dash.service"
import './App.css';

function App() {
  const [currentTime, setCurrentTime] = useState(0);
  
  useEffect(() => {
    DashDataService.getInfo().then(res => res.data).then(data => {
    console.log(data);  
    setCurrentTime(data.uptime);
    });
  }, []);

  return (
    
    <Dash />
  );
}

export default App;
