import { useCallback, useEffect, useRef, useState } from "react";
import { Terminal } from "xterm";
import { FitAddon } from "xterm-addon-fit";
import "xterm/css/xterm.css";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { execCli, isAllowedCli, type Cli } from "@/lib/cli-bridge";
import { TerminalSquare } from "lucide-react";
import { toast } from "sonner";

const HISTORY_KEY = "localstack-console:shell-history";
const MAX_HISTORY = 100;

function loadHistory(): string[] {
  try {
    return JSON.parse(localStorage.getItem(HISTORY_KEY) ?? "[]") as string[];
  } catch {
    return [];
  }
}

function saveHistory(items: string[]) {
  try {
    localStorage.setItem(HISTORY_KEY, JSON.stringify(items.slice(-MAX_HISTORY)));
  } catch {
    /* ignore */
  }
}

export function CloudShellButton() {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const terminalRef = useRef<Terminal | null>(null);
  const fitRef = useRef<FitAddon | null>(null);
  const [cmd, setCmd] = useState("");
  const [history, setHistory] = useState<string[]>(() => loadHistory());
  const [historyIdx, setHistoryIdx] = useState<number | null>(null);

  useEffect(() => {
    if (!open || !containerRef.current) return;
    const term = new Terminal({
      convertEol: true,
      fontSize: 12,
      fontFamily: "ui-monospace, SFMono-Regular, Menlo, monospace",
      theme: { background: "#0b0d10" },
    });
    const fit = new FitAddon();
    term.loadAddon(fit);
    term.open(containerRef.current);
    fit.fit();
    term.writeln(
      "\x1b[36m# LocalStack Cloud Shell — aws | az | gcloud only\x1b[0m",
    );
    terminalRef.current = term;
    fitRef.current = fit;
    const onResize = () => fit.fit();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      term.dispose();
      terminalRef.current = null;
      fitRef.current = null;
    };
  }, [open]);

  const submit = useCallback(async () => {
    const line = cmd.trim();
    if (!line) return;
    const tokens = line.split(/\s+/);
    const cli = tokens[0];
    if (!isAllowedCli(cli)) {
      toast.error(`cli not allowed: ${cli}`);
      return;
    }
    setCmd("");
    const next = [...history, line];
    setHistory(next);
    saveHistory(next);
    setHistoryIdx(null);

    const term = terminalRef.current;
    term?.writeln(`\x1b[33m$ ${line}\x1b[0m`);
    try {
      const r = await execCli(cli as Cli, tokens.slice(1));
      if (r.stdout) term?.write(r.stdout);
      if (r.stderr) term?.write(`\x1b[31m${r.stderr}\x1b[0m`);
      term?.writeln(
        `\x1b[2m[via ${r.via}] exit=${r.exit_code} ${r.duration_ms}ms\x1b[0m`,
      );
    } catch (e) {
      term?.writeln(`\x1b[31m${(e as Error).message}\x1b[0m`);
    }
  }, [cmd, history]);

  function navigateHistory(direction: -1 | 1) {
    if (history.length === 0) return;
    const idx =
      historyIdx === null
        ? direction === -1
          ? history.length - 1
          : -1
        : Math.max(0, Math.min(history.length - 1, historyIdx + direction));
    setHistoryIdx(idx);
    setCmd(history[idx] ?? "");
  }

  return (
    <>
      <Button
        size="sm"
        variant="ghost"
        className="fixed bottom-3 right-3 z-40 bg-skin-accent text-black hover:bg-skin-accent/90 shadow"
        onClick={() => setOpen(true)}
      >
        <TerminalSquare className="h-4 w-4" /> Cloud Shell
      </Button>
      <Sheet open={open} onOpenChange={setOpen}>
        <SheetContent side="bottom" className="flex flex-col gap-3">
          <SheetHeader>
            <SheetTitle>Cloud Shell — bridge :4578 or in-container fallback</SheetTitle>
          </SheetHeader>
          <div
            ref={containerRef}
            className="flex-1 min-h-0 bg-[#0b0d10] rounded-md p-2"
          />
          <form
            onSubmit={(e) => {
              e.preventDefault();
              void submit();
            }}
            className="flex gap-2"
          >
            <Input
              value={cmd}
              onChange={(e) => setCmd(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "ArrowUp") {
                  e.preventDefault();
                  navigateHistory(-1);
                } else if (e.key === "ArrowDown") {
                  e.preventDefault();
                  navigateHistory(1);
                }
              }}
              placeholder="aws s3 ls   |   az storage account list   |   gcloud projects list"
              className="font-mono"
              autoFocus
            />
            <Button type="submit" variant="skin">
              Run
            </Button>
          </form>
        </SheetContent>
      </Sheet>
    </>
  );
}
