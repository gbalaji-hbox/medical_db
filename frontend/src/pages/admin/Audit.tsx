import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "@/api/client";
import { AlertCircle, RefreshCw } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { PageLoader } from "@/components/ui/loader";
import type { AuditEntry } from "@/api/types";

interface AuditFilter {
  identity?: string;
  method?: string;
  page: number;
  limit: number;
}

async function fetchAudit(filter: AuditFilter): Promise<AuditEntry[]> {
  const res = await apiClient.get<AuditEntry[]>("/api/audit", { params: filter });
  return res.data;
}

function statusColor(code: number): string {
  if (code < 300) return "text-emerald-600";
  if (code < 400) return "text-amber-600";
  return "text-red-600";
}

const METHODS = ["all", "GET", "POST", "PUT", "PATCH", "DELETE"];

export function AuditPage() {
  const [page] = useState(1);
  const [identity, setIdentity] = useState("");
  const [method, setMethod] = useState("all");

  const filter: AuditFilter = {
    page,
    limit: 50,
    ...(identity ? { identity } : {}),
    ...(method !== "all" ? { method } : {}),
  };

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["audit", filter],
    queryFn: () => fetchAudit(filter),
    retry: false,
  });

  const endpointMissing =
    (error as { response?: { status?: number } })?.response?.status === 404 ||
    (error as { response?: { status?: number } })?.response?.status === 405;

  if (isLoading) return <PageLoader text="Loading audit log…" />;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Audit Log</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Compliance visibility into who called what and when.
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-2" onClick={() => refetch()}>
          <RefreshCw size={14} />
          Refresh
        </Button>
      </div>

      {endpointMissing && (
        <div className="flex items-start gap-2 rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <p>
            The audit endpoint (<code>/api/audit</code>) has not been added to the backend yet.
            This page will become functional once it is implemented.
          </p>
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <Input
          placeholder="Filter by identity…"
          value={identity}
          onChange={(e) => setIdentity(e.target.value)}
          className="w-48"
        />
        <Select value={method} onValueChange={setMethod}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {METHODS.map((m) => (
              <SelectItem key={m} value={m}>
                {m === "all" ? "All methods" : m}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Timestamp</TableHead>
                <TableHead>Identity</TableHead>
                <TableHead>Auth type</TableHead>
                <TableHead>Method</TableHead>
                <TableHead>Path</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>Duration</TableHead>
                <TableHead>IP</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data ?? []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={8} className="text-center text-muted-foreground py-12">
                    {endpointMissing ? "Backend endpoint not available yet." : "No audit entries found."}
                  </TableCell>
                </TableRow>
              ) : (
                (data ?? []).map((entry) => (
                  <TableRow key={entry.id}>
                    <TableCell className="text-xs text-muted-foreground whitespace-nowrap">
                      {new Date(entry.timestamp).toLocaleString()}
                    </TableCell>
                    <TableCell className="text-sm font-medium">{entry.identity}</TableCell>
                    <TableCell>
                      <Badge variant="outline" className="text-xs">
                        {entry.auth_type}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      <span className="font-mono text-xs font-semibold">{entry.method}</span>
                    </TableCell>
                    <TableCell className="text-xs font-mono text-muted-foreground max-w-[200px] truncate">
                      {entry.path}
                    </TableCell>
                    <TableCell className={`text-sm font-semibold ${statusColor(entry.status_code)}`}>
                      {entry.status_code}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {entry.duration_ms}ms
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {entry.client_ip}
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
