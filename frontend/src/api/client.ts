import axios from "axios";

// Base URL comes from the environment (VITE_API_BASE_URL), defaulting to the
// local backend. Exported separately because the streaming endpoint uses fetch
// (axios doesn't expose a readable stream in the browser) and needs the URL.
export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});
