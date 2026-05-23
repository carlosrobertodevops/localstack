import { type ReactNode } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { openIacDrawer, type IacTool } from "@/lib/iac-drawer-store";
import { Code2, RefreshCw } from "lucide-react";

interface ResourcePageProps {
  title: string;
  description?: string;
  children: ReactNode;
  onRefresh?: () => void;
  iac?: { tool: IacTool; snippet: string; title?: string };
  actions?: ReactNode;
}

export function ResourcePage({
  title,
  description,
  children,
  onRefresh,
  iac,
  actions,
}: ResourcePageProps) {
  return (
    <div className="p-4 space-y-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold">{title}</h2>
          {description && (
            <p className="text-sm text-muted-foreground mt-0.5">{description}</p>
          )}
        </div>
        <div className="flex items-center gap-2">
          {actions}
          {iac && (
            <Button
              size="sm"
              variant="outline"
              onClick={() =>
                openIacDrawer({
                  tool: iac.tool,
                  snippet: iac.snippet,
                  title: iac.title ?? `${title} — ${iac.tool}`,
                })
              }
            >
              <Code2 className="h-4 w-4" /> Show as {iac.tool === "terraform" ? "Terraform" : "Serverless"}
            </Button>
          )}
          {onRefresh && (
            <Button size="sm" variant="ghost" onClick={onRefresh}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          )}
        </div>
      </div>
      <Card>
        <CardHeader className="py-3">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            {title}
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-0">{children}</CardContent>
      </Card>
    </div>
  );
}
