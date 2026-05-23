import { Outlet } from "@tanstack/react-router";
import { TopBar } from "@/components/shell/TopBar";
import { Sidebar } from "@/components/shell/Sidebar";
import { Breadcrumbs } from "@/components/shell/Breadcrumbs";
import { IacInlineDrawer } from "@/components/iac/IacInlineDrawer";
import { CloudShellButton } from "@/components/cloud-shell/CloudShellDrawer";

export function App() {
  return (
    <div className="flex flex-col h-screen">
      <TopBar />
      <div className="flex flex-1 min-h-0">
        <Sidebar />
        <main className="flex-1 min-w-0 overflow-y-auto bg-background">
          <Breadcrumbs />
          <Outlet />
        </main>
      </div>
      <IacInlineDrawer />
      <CloudShellButton />
    </div>
  );
}
