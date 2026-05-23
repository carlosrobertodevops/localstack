import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ResourcePage } from "@/components/resource-page/ResourcePage";
import { azureApi } from "@/lib/api/azure";
import { useCloud } from "@/lib/cloud-context";
import {
  genTerraformAzureRg,
  genTerraformAzureStorageAccount,
} from "@/lib/iac/generators";

export function ResourceGroupsList() {
  const { subscription } = useCloud();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [location, setLocation] = useState("eastus");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["azure", "rgs", subscription],
    queryFn: () => azureApi.listResourceGroups(subscription),
  });
  const create = useMutation({
    mutationFn: () =>
      azureApi.createResourceGroup(subscription, name, location),
    onSuccess: () => {
      toast.success("resource group created");
      setName("");
      qc.invalidateQueries({ queryKey: ["azure", "rgs"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const del = useMutation({
    mutationFn: (n: string) => azureApi.deleteResourceGroup(subscription, n),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["azure", "rgs"] }),
  });

  return (
    <ResourcePage
      title="Azure · Resource Groups"
      description={`subscription ${subscription}`}
      onRefresh={() => refetch()}
      iac={{
        tool: "terraform",
        snippet: genTerraformAzureRg(name || "my-rg", location),
      }}
      actions={
        <div className="flex items-end gap-2">
          <div>
            <Label className="text-xs">Name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-8 w-40"
              placeholder="my-rg"
            />
          </div>
          <div>
            <Label className="text-xs">Location</Label>
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="h-8 w-32"
            />
          </div>
          <Button
            size="sm"
            variant="skin"
            disabled={!name || create.isPending}
            onClick={() => create.mutate()}
          >
            Create
          </Button>
        </div>
      }
    >
      {isLoading ? (
        <div className="p-3 text-sm text-muted-foreground">loading…</div>
      ) : !data || data.length === 0 ? (
        <div className="p-3 text-sm text-muted-foreground">No groups.</div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>State</TableHead>
              <TableHead className="w-20" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((g) => (
              <TableRow key={g.id}>
                <TableCell className="font-mono">{g.name}</TableCell>
                <TableCell>{g.location}</TableCell>
                <TableCell>
                  {g.properties?.provisioningState ?? "—"}
                </TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => del.mutate(g.name)}
                  >
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </ResourcePage>
  );
}

export function StorageAccountsList() {
  const { subscription } = useCloud();
  const qc = useQueryClient();
  const [name, setName] = useState("");
  const [rg, setRg] = useState("default");
  const [location, setLocation] = useState("eastus");

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["azure", "sa", subscription],
    queryFn: () => azureApi.listStorageAccounts(subscription),
  });
  const create = useMutation({
    mutationFn: () =>
      azureApi.createStorageAccount(subscription, rg, name, location),
    onSuccess: () => {
      toast.success("storage account created");
      setName("");
      qc.invalidateQueries({ queryKey: ["azure", "sa"] });
    },
    onError: (e: Error) => toast.error(e.message),
  });
  const del = useMutation({
    mutationFn: (n: string) =>
      azureApi.deleteStorageAccount(subscription, rg, n),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["azure", "sa"] }),
  });

  return (
    <ResourcePage
      title="Azure · Storage Accounts"
      onRefresh={() => refetch()}
      iac={{
        tool: "terraform",
        snippet: genTerraformAzureStorageAccount(
          name || "mystorage",
          rg,
          location,
        ),
      }}
      actions={
        <div className="flex items-end gap-2 flex-wrap">
          <div>
            <Label className="text-xs">Name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="h-8 w-40"
              placeholder="mystorage"
            />
          </div>
          <div>
            <Label className="text-xs">Resource group</Label>
            <Input
              value={rg}
              onChange={(e) => setRg(e.target.value)}
              className="h-8 w-32"
            />
          </div>
          <div>
            <Label className="text-xs">Location</Label>
            <Input
              value={location}
              onChange={(e) => setLocation(e.target.value)}
              className="h-8 w-28"
            />
          </div>
          <Button
            size="sm"
            variant="skin"
            disabled={!name || create.isPending}
            onClick={() => create.mutate()}
          >
            Create
          </Button>
        </div>
      }
    >
      {isLoading ? (
        <div className="p-3 text-sm text-muted-foreground">loading…</div>
      ) : !data || data.length === 0 ? (
        <div className="p-3 text-sm text-muted-foreground">No accounts.</div>
      ) : (
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>Location</TableHead>
              <TableHead>Kind</TableHead>
              <TableHead className="w-20" />
            </TableRow>
          </TableHeader>
          <TableBody>
            {data.map((s) => (
              <TableRow key={s.id}>
                <TableCell className="font-mono">{s.name}</TableCell>
                <TableCell>{s.location}</TableCell>
                <TableCell>{s.kind ?? "—"}</TableCell>
                <TableCell>
                  <Button
                    size="sm"
                    variant="ghost"
                    onClick={() => del.mutate(s.name)}
                  >
                    Delete
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </ResourcePage>
  );
}
