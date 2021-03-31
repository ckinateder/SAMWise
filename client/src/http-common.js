import axios from "axios";

const path = require('path')
require('dotenv').config({ path: path.resolve(__dirname, '../.env') }); // load env

export default axios.create({
  baseURL: (localStorage.getItem("baseURL") || process.env.REACT_APP_DEFAULT_HOST),
  headers: {
    "Content-type": "application/json"
  }
});