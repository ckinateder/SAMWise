import axios from "axios";
require('dotenv').config();

export default axios.create({
  baseURL: (process.env.BACKEND_URL || "http://localhost:5000")+"/backend/v1",
  headers: {
    "Content-type": "application/json"
  }
});