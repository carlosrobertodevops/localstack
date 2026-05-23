var _a, _b;
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
var EDGE = (_a = process.env.LOCALSTACK_ENDPOINT) !== null && _a !== void 0 ? _a : "http://localhost:4566";
var BRIDGE = (_b = process.env.CONSOLE_BRIDGE) !== null && _b !== void 0 ? _b : "http://localhost:4578";
export default defineConfig({
    plugins: [react()],
    resolve: {
        alias: { "@": path.resolve(__dirname, "./src") },
    },
    server: {
        port: 5173,
        proxy: {
            "/_localstack": { target: EDGE, changeOrigin: true },
            "/_bridge": { target: BRIDGE, changeOrigin: true, rewrite: function (p) { return p.replace(/^\/_bridge/, ""); } },
        },
    },
    build: {
        outDir: "dist",
        sourcemap: true,
        emptyOutDir: true,
    },
});
