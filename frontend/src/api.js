const API_BASE = "http://localhost:8000";

let currentToken = localStorage.getItem("hospital_jwt") || "";

export const setAuthToken = (token) => {
  currentToken = token;
  if (token) {
    localStorage.setItem("hospital_jwt", token);
  } else {
    localStorage.removeItem("hospital_jwt");
  }
};

export const getAuthToken = () => currentToken;

export const apiFetch = async (endpoint, options = {}) => {
  const headers = {
    "Content-Type": "application/json",
    ...(options.headers || {})
  };
  
  if (currentToken) {
    headers["Authorization"] = `Bearer ${currentToken}`;
  }
  
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers
  });
  
  const data = await response.json().catch(() => null);
  
  if (!response.ok) {
    const errorMsg = data?.detail || `Request failed with status ${response.status}`;
    const err = new Error(errorMsg);
    err.status = response.status;
    err.detail = errorMsg;
    throw err;
  }
  
  return data;
};
