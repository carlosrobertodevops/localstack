import { useQuery } from "@tanstack/react-query";
import { Link } from "@tanstack/react-router";
import { cloudsApi, type CloudHealth } from "@/lib/api/clouds";
import { useCloud } from "@/lib/cloud-context";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { SERVICES_BY_CLOUD } from "@/routes/registry";

export function Sidebar() {
  const { cloud } = useCloud();
  const { data, isLoading, error } = useQuery<CloudHealth>({
    queryKey: ["cloud-health", cloud],
    queryFn: () => cloudsApi.health(cloud),
    refetchInterval: 15_000,
  });

  const states = data?.services ?? {};
  const services = SERVICES_BY_CLOUD[cloud] ?? [];

  return (
    <aside
      className="w-64 shrink-0 overflow-y-auto p-3 text-sm"
      style={{ background: "var(--sidebar)", color: "var(--text-on-bg)" }}
    >
      <div className="px-2 pb-2 text-xs uppercase tracking-wider opacity-60">
        {cloud.toUpperCase()} services
      </div>
      {isLoading && <div className="px-2 text-xs opacity-60">loading…</div>}
      {error && (
        <div className="px-2 text-xs text-red-300">
          {(error as Error).message}
        </div>
      )}
      <ul className="space-y-0.5">
        {services.map((s) => {
          const state = states[s.id] ?? "unknown";
          return (
            <li key={s.id}>
              <Link
                to={s.path}
                params={{}}
                className={cn(
                  "flex items-center justify-between rounded-md px-2 py-1.5 hover:bg-white/10",
                )}
                activeProps={{ className: "bg-white/15" }}
              >
                <span>{s.label}</span>
                <Badge
                  variant={
                    state === "available" || state === "running"
                      ? "success"
                      : state === "disabled"
                        ? "warn"
                        : "muted"
                  }
                  className="text-[10px] py-0"
                >
                  {state}
                </Badge>
              </Link>
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
