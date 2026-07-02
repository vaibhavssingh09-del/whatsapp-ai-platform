import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Design decision: the dev server proxies /api to the backend instead of
// hardcoding an absolute backend URL in the frontend fetch client. This
// means the same VITE_API_BASE_URL="/api/v1" works unchanged in both local
// dev (proxied through Vite) and production (served behind the same
// reverse proxy / same Render service, see render.yaml), avoiding CORS
// entirely in production.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.VITE_BACKEND_ORIGIN || "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
