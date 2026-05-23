import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";

const EDGE = process.env.LOCALSTACK_ENDPOINT ?? "http://localhost:4566";
const BRIDGE = process.env.CONSOLE_BRIDGE ?? "http://localhost:4578";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { "@": path.resolve(__dirname, "./src") },
  },
  server: {
    port: 5173,
    proxy: {
      "/_localstack": { target: EDGE, changeOrigin: true },
      "/_bridge": { target: BRIDGE, changeOrigin: true, rewrite: (p) => p.replace(/^\/_bridge/, "") },
    },
  },
  build: {
    outDir: "dist",
    sourcemap: true,
    emptyOutDir: true,
  },
});
