import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// In development the Vite server proxies API calls to Flask on :5000, so the
// browser talks to one origin. In production Flask serves the built files.
const API = process.env.POLICYPAL_API || "http://127.0.0.1:5000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/chat": API,
      "/health": API,
      "/api": API,
      "/sources": API,
      "/docs": API,
    },
  },
  build: { outDir: "dist", emptyOutDir: true, sourcemap: false },
  test: { environment: "node" },
});
