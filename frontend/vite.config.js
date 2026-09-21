import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8000",
      "/auth": "http://localhost:8000",
      "/economy": "http://localhost:8000",
      "/leaderboard": "http://localhost:8000",
      "/bounties": "http://localhost:8000",
      "/tutor": "http://localhost:8000"
    }
  }
});
