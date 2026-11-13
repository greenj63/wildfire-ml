import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// In development the React app calls /api/..., and Vite forwards it to the FastAPI
// backend (python -m uvicorn backend.app.main:app --reload, on port 8000).
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": "http://127.0.0.1:8000",
    },
  },
});
