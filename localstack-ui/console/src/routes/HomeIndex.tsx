import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { useCloud } from "@/lib/cloud-context";
import { cloudsApi } from "@/lib/api/clouds";
import { SERVICES_BY_CLOUD } from "@/routes/registry";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function HomeIndex() {
  const { cloud } = useCloud();
  const { data } = useQuery({
    queryKey: ["cloud-health", cloud],
    queryFn: () => cloudsApi.health(cloud),
  });
  const states = data?.services ?? {};
  const services = SERVICES_BY_CLOUD[cloud] ?? [];

  return (
    <div className="p-4">
      <h1 className="text-xl font-semibold mb-3">{cloud.toUpperCase()} Console</h1>
      <p className="text-sm text-muted-foreground mb-4">
        Pick a service to manage via the UI, Terraform snippet, or Cloud Shell.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {services.map((s) => {
          const state = states[s.id] ?? "unknown";
          return (
            <Link key={s.id} to={s.path}>
              <Card className="hover:bg-accent transition-colors cursor-pointer">
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle>{s.label}</CardTitle>
                    <Badge
                      variant={
                        state === "available" || state === "running"
                          ? "success"
                          : state === "disabled"
                            ? "warn"
                            : "muted"
                      }
                    >
                      {state}
                    </Badge>
                  </div>
                  <CardDescription className="text-xs">{s.id}</CardDescription>
                </CardHeader>
                <CardContent />
              </Card>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
