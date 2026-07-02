import axios from "axios";

// Design decision: a single configured axios instance, with the access
// token attached via a request interceptor reading from localStorage-backed
// state rather than passed manually into every call site. A response
// interceptor centralizes "401 -> log out" handling so every page doesn't
// need its own try/catch for expired tokens.
export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "/api/v1",
});

apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

let onUnauthorized = () => {};
export function registerUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      onUnauthorized();
    }
    return Promise.reject(error);
  }
);
