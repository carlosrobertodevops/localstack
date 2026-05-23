import { useCloud } from "@/lib/cloud-context";
import type { CloudName } from "@/lib/skins";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Cloud } from "lucide-react";

const CLOUDS: { id: CloudName; label: string }[] = [
  { id: "aws", label: "AWS" },
  { id: "azure", label: "Azure" },
  { id: "gcp", label: "GCP" },
];

export function TopBar() {
  const { cloud, setCloud, region, endpoint } = useCloud();
  return (
    <header
      className="flex h-12 items-center justify-between px-4 text-white"
      style={{ background: "var(--bg-top)" }}
    >
      <div className="flex items-center gap-3">
        <Cloud className="h-5 w-5" style={{ color: "var(--accent)" }} />
        <span className="font-semibold tracking-tight">LocalStack Console</span>
      </div>
      <nav className="flex items-center gap-1">
        {CLOUDS.map((c) => (
          <Button
            key={c.id}
            size="sm"
            variant="ghost"
            onClick={() => setCloud(c.id)}
            className={cn(
              "text-white hover:bg-white/10",
              cloud === c.id && "ring-1 ring-white/40 bg-white/10",
            )}
          >
            {c.label}
          </Button>
        ))}
      </nav>
      <div className="flex items-center gap-3 text-xs opacity-80">
        <span>{region}</span>
        <span className="hidden md:inline">{endpoint}</span>
      </div>
    </header>
  );
}
