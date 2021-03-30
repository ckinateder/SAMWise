
import http from "../http-common";

class DashDataService {
  getSummary() {
    return http.get("/summary");
  }

  getResults() {
    return http.get("/results");
  }
  
  getSpreads() {
    return http.get("/spreads");
  }

  getInfo() {
    return http.get("/info");
  }
  
  getLengths() {
    return http.get("/lengths");
  }
  
  getInterval() {
    return http.get("/interval");
  }

  setInterval(data) {
    return http.put("/interval", data);
  }
  // for config
  setBaseURL(url) {
    http.defaults.baseURL = url+(process.env.REACT_APP_DEFAULT_HOST_ROUTE || "/backend/v1");
  }
  /** 
  get(id) {
    console.log(`trying to get ${id}`);
    return http.get(`/tasks/${id}`);
  }

  update(id, data) {
    return http.put(`/tasks/${id}`, data);
  }

  delete(id) {
    return http.delete(`/tasks/${id}`);
  }

  deleteAll() {
    return http.delete(`/tasks`);
  }

  findByTitle(title) {
    return http.get(`/tasks?title=${title}`);
  }*/
}

export default new DashDataService();