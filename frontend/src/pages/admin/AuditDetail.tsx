import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { AlertCircle, ArrowLeft, RefreshCw } from "lucide-react";
import { getAuditLog } from "@/api/audit";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { PageLoader } from "@/components/ui/loader";

function statusColor(code: number | null): string {
  if (code === null) return "text-muted-foreground";
  if (code < 300) return "text-emerald-600";
  if (code < 400) return "text-amber-600";
  return "text-red-600";
}

export function AuditDetailPage() {
  const { logId } = useParams();
  const parsedId = Number(logId);

  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ["audit-log", parsedId],
    queryFn: () => getAuditLog(parsedId),
    enabled: Number.isFinite(parsedId),
    retry: false,
  });

  if (!Number.isFinite(parsedId)) {
    return (
      <div className="space-y-4">
        <Link to="/admin/audit">
          <Button variant="outline" size="sm" className="gap-2">
            <ArrowLeft size={14} /> Back to Audit Log
          </Button>
        </Link>
        <div className="flex items-start gap-2 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <p>Invalid audit log id.</p>
        </div>
      </div>
    );
  }

  if (isLoading) return <PageLoader text="Loading audit log detail…" />;

  if (isError || !data) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Link to="/admin/audit">
            <Button variant="outline" size="sm" className="gap-2">
              <ArrowLeft size={14} /> Back to Audit Log
            </Button>
          </Link>
          <Button variant="outline" size="sm" className="gap-2" onClick={() => refetch()}>
            <RefreshCw size={14} /> Refresh
          </Button>
        </div>
        <div className="flex items-start gap-2 rounded-md bg-red-50 border border-red-200 px-4 py-3 text-sm text-red-800">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <p>Could not load this audit log entry.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link to="/admin/audit">
            <Button variant="outline" size="sm" className="gap-2">
              <ArrowLeft size={14} /> Back to Audit Log
            </Button>
          </Link>
          <h1 className="text-2xl font-bold tracking-tight mt-3">Audit Log #{data.id}</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Full details for one request audit record.
          </p>
        </div>
        <Button variant="outline" size="sm" className="gap-2" onClick={() => refetch()}>
          <RefreshCw size={14} /> Refresh
        </Button>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Request Summary</CardTitle>
        </CardHeader>
        <CardContent className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
          <div>
            <p className="text-muted-foreground">Timestamp</p>
            <p className="font-medium">{new Date(data.ts * 1000).toLocaleString()}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Identity</p>
            <p className="font-medium">{data.identity ?? "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Auth Type</p>
            <Badge variant="outline">{data.auth_type ?? "—"}</Badge>
          </div>
          <div>
            <p className="text-muted-foreground">Client IP</p>
            <p className="font-medium">{data.client_ip ?? "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">HTTP Method</p>
            <p className="font-mono font-semibold">{data.method}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Status Code</p>
            <p className={`font-semibold ${statusColor(data.status_code)}`}>{data.status_code ?? "—"}</p>
          </div>
          <div>
            <p className="text-muted-foreground">Duration</p>
            <p className="font-medium">{data.duration_ms !== null ? `${data.duration_ms}ms` : "—"}</p>
          </div>
          <div className="md:col-span-2">
            <p className="text-muted-foreground">Path</p>
            <p className="font-mono text-xs break-all">{data.path}</p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
