import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "@tanstack/react-router";
import { Toaster } from "sonner";
import "./styles/globals.css";
import { router } from "./router";
import { queryClient } from "./lib/queryClient";
import { CloudProvider } from "./lib/cloud-context";

const root = document.getElementById("root");
if (!root) throw new Error("missing #root");

ReactDOM.createRoot(root).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <CloudProvider>
        <RouterProvider router={router} />
        <Toaster richColors closeButton position="bottom-right" />
      </CloudProvider>
    </QueryClientProvider>
  </React.StrictMode>,
);
