import { useState } from "react";
import Editor from "@monaco-editor/react";
import { toast } from "sonner";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  useIacDrawer,
  closeIacDrawer,
  setIacSnippet,
} from "@/lib/iac-drawer-store";

interface IacResponse {
  session_id: string;
  exit_code: number;
  stdout: string;
  stderr: string;
  log_path?: string;
  duration_ms: number;
}

async function postIac(
  path: string,
  body: Record<string, unknown>,
): Promise<IacResponse> {
  const res = await fetch(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`HTTP ${res.status}: ${text}`);
  }
  return (await res.json()) as IacResponse;
}

export function IacInlineDrawer() {
  const { open, tool, snippet, title } = useIacDrawer();
  const [running, setRunning] = useState(false);
  const [stdout, setStdout] = useState("");
  const [stderr, setStderr] = useState("");

  async function copy() {
    await navigator.clipboard.writeText(snippet);
    toast.success("Copied to clipboard");
  }

  async function preview() {
    try {
      const r = await fetch("/_localstack/console/iac/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tool, snippet }),
      });
      const body = (await r.json()) as { files: Record<string, string> };
      setStdout(
        Object.entries(body.files)
          .map(([n, c]) => `# ${n}\n${c}`)
          .join("\n\n"),
      );
    } catch (e) {
      toast.error((e as Error).message);
    }
  }

  async function run(action: "plan" | "apply" | "destroy") {
    setRunning(true);
    setStdout("");
    setStderr("");
    try {
      const r = await postIac("/_localstack/console/iac", {
        tool,
        snippet,
        action,
      });
      setStdout(r.stdout);
      setStderr(r.stderr);
      if (r.exit_code === 0) {
        toast.success(`${action} ok (${r.duration_ms} ms)`);
      } else {
        toast.error(`${action} failed (exit ${r.exit_code})`);
      }
    } catch (e) {
      toast.error((e as Error).message);
    } finally {
      setRunning(false);
    }
  }

  return (
    <Sheet open={open} onOpenChange={(o) => !o && closeIacDrawer()}>
      <SheetContent side="right" className="flex flex-col gap-3 max-w-2xl">
        <SheetHeader>
          <SheetTitle>{title ?? "Infrastructure as Code"}</SheetTitle>
          <SheetDescription>
            Tool: <span className="font-mono">{tool}</span> · Provider configured
            to LocalStack
          </SheetDescription>
        </SheetHeader>

        <div className="border rounded-md overflow-hidden">
          <Editor
            height="32vh"
            defaultLanguage={tool === "terraform" ? "hcl" : "yaml"}
            value={snippet}
            onChange={(v) => setIacSnippet(v ?? "")}
            options={{
              minimap: { enabled: false },
              fontSize: 12,
              scrollBeyondLastLine: false,
            }}
          />
        </div>

        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={copy}>
            Copy
          </Button>
          <Button variant="outline" size="sm" onClick={preview}>
            Preview
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => run("plan")}
            disabled={running}
          >
            Plan
          </Button>
          <Button
            size="sm"
            onClick={() => run("apply")}
            disabled={running}
            variant="skin"
          >
            Apply
          </Button>
          <Button
            size="sm"
            variant="destructive"
            onClick={() => run("destroy")}
            disabled={running}
          >
            Destroy
          </Button>
        </div>

        <Tabs defaultValue="stdout" className="flex-1 min-h-0 flex flex-col">
          <TabsList>
            <TabsTrigger value="stdout">stdout</TabsTrigger>
            <TabsTrigger value="stderr">stderr</TabsTrigger>
          </TabsList>
          <TabsContent value="stdout" className="flex-1 min-h-0">
            <pre className="h-full overflow-auto text-xs bg-muted p-3 rounded">
              {stdout || "(empty)"}
            </pre>
          </TabsContent>
          <TabsContent value="stderr" className="flex-1 min-h-0">
            <pre className="h-full overflow-auto text-xs bg-muted p-3 rounded">
              {stderr || "(empty)"}
            </pre>
          </TabsContent>
        </Tabs>
      </SheetContent>
    </Sheet>
  );
}
