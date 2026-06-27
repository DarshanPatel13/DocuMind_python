import axios from "axios";

import { clearToken, getToken } from "../auth/token";

// Base URL is the GATEWAY now — the frontend never talks to the services
// directly. Defaults to the local gateway; baked from VITE_API_BASE_URL at build.
// Exported separately because the streaming endpoint uses fetch (axios doesn't
// expose a readable stream in the browser) and needs the URL + token itself.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8080";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Attach the JWT to every request if we have one.
apiClient.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// If the gateway rejects the token, drop it so the app falls back to login.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error?.response?.status === 401) {
      clearToken();
    }
    return Promise.reject(error);
  },
);
