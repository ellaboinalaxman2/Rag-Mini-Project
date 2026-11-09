import axios from "axios";

const baseURL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const api = axios.create({
  baseURL,
  timeout: 60000,
  headers: { "Content-Type": "application/json" },
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const detail =
      error?.response?.data?.detail || error?.message || "Request failed";
    return Promise.reject(
      Object.assign(new Error(detail), {
        status: error?.response?.status,
      }),
    );
  },
);
