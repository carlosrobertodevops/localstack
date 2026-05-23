var __assign = (this && this.__assign) || function () {
    __assign = Object.assign || function(t) {
        for (var s, i = 1, n = arguments.length; i < n; i++) {
            s = arguments[i];
            for (var p in s) if (Object.prototype.hasOwnProperty.call(s, p))
                t[p] = s[p];
        }
        return t;
    };
    return __assign.apply(this, arguments);
};
var _a;
import { defineConfig, devices } from "@playwright/test";
export default defineConfig({
    testDir: "tests/e2e",
    retries: 1,
    timeout: 30000,
    fullyParallel: true,
    use: {
        baseURL: (_a = process.env.CONSOLE_URL) !== null && _a !== void 0 ? _a : "http://localhost:4577",
        trace: "on-first-retry",
    },
    projects: [
        { name: "chromium", use: __assign({}, devices["Desktop Chrome"]) },
    ],
});
