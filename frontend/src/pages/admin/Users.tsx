import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus, UserX, KeyRound, Loader2, AlertCircle } from "lucide-react";
import { listUsers, createUser, updateUser, resetPassword } from "@/api/auth";
import { useToast } from "@/components/ui/use-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
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
import { Paginator } from "@/components/ui/paginator";

function fmtTs(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString();
}

function generatePassword(): string {
  const chars = "ABCDEFGHJKMNPQRSTUVWXYZabcdefghjkmnpqrstuvwxyz23456789!@#$";
  return Array.from({ length: 12 }, () => chars[Math.floor(Math.random() * chars.length)]).join("");
}

export function UsersPage() {
  const { toast } = useToast();
  const qc = useQueryClient();

  const [createOpen, setCreateOpen] = useState(false);
  const [newUsername, setNewUsername] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [autoGen, setAutoGen] = useState(true);
  const [newRole, setNewRole] = useState<"admin" | "user">("user");
  const [resetResult, setResetResult] = useState<{ username: string; password: string } | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);

  const { data: users, isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: listUsers,
    retry: false,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createUser({
        username: newUsername,
        password: autoGen ? generatePassword() : newPassword,
        role: newRole,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      setCreateOpen(false);
      setNewUsername("");
      setNewPassword("");
      toast({ title: "User created" });
    },
    onError: () => {
      toast({ variant: "destructive", title: "Failed to create user" });
    },
  });

  const deactivateMutation = useMutation({
    mutationFn: (username: string) => updateUser(username, { is_active: false }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["users"] });
      toast({ title: "User deactivated" });
    },
    onError: () => {
      toast({ variant: "destructive", title: "Failed to deactivate user" });
    },
  });

  const resetMutation = useMutation({
    mutationFn: (username: string) => resetPassword(username),
    onSuccess: (data, username) => {
      setResetResult({ username, password: data.temporary_password });
    },
    onError: () => {
      toast({ variant: "destructive", title: "Failed to reset password" });
    },
  });

  if (isLoading) return <PageLoader text="Loading users…" />;

  const endpointMissing = (error as { response?: { status?: number } })?.response?.status === 404 ||
    (error as { response?: { status?: number } })?.response?.status === 405;
  const start = (page - 1) * pageSize;
  const visibleUsers = (users ?? []).slice(start, start + pageSize);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">User Management</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Create and manage user accounts.
          </p>
        </div>
        <Button className="gap-2" onClick={() => setCreateOpen(true)} disabled={endpointMissing}>
          <Plus size={16} />
          Create User
        </Button>
      </div>

      {endpointMissing && (
        <div className="flex items-start gap-2 rounded-md bg-amber-50 border border-amber-200 px-4 py-3 text-sm text-amber-800">
          <AlertCircle size={16} className="mt-0.5 shrink-0" />
          <p>
            The user management endpoints (<code>/api/auth/users</code>) have not been added to the
            backend yet. This page will become functional once they are implemented.
          </p>
        </div>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Username</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
                <TableHead>API Keys</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(users ?? []).length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center text-muted-foreground py-12">
                    {endpointMissing ? "Backend endpoint not available yet." : "No users found."}
                  </TableCell>
                </TableRow>
              ) : (
                visibleUsers.map((u) => (
                  <TableRow key={u.username}>
                    <TableCell className="font-medium">{u.username}</TableCell>
                    <TableCell>
                      <Badge variant={u.role === "admin" ? "default" : "outline"}>
                        {u.role}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {fmtTs(u.created_at)}
                    </TableCell>
                    <TableCell>
                      <Badge variant={u.is_active ? "success" : "secondary"}>
                        {u.is_active ? "Active" : "Inactive"}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-sm">{u.api_key_count}</TableCell>
                    <TableCell className="text-right">
                      <div className="flex items-center justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          className="h-7 text-xs gap-1"
                          onClick={() => resetMutation.mutate(u.username)}
                          disabled={!u.is_active}
                        >
                          <KeyRound size={13} />
                          Reset PW
                        </Button>
                        {u.is_active && (
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 text-xs gap-1 text-destructive hover:text-destructive"
                            onClick={() => deactivateMutation.mutate(u.username)}
                          >
                            <UserX size={13} />
                            Deactivate
                          </Button>
                        )}
                      </div>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      <Paginator
        total={(users ?? []).length}
        page={page}
        pageSize={pageSize}
        onPageChange={setPage}
        onPageSizeChange={(size) => {
          setPageSize(size);
          setPage(1);
        }}
        pageSizeOptions={[5, 10, 25, 50]}
      />

      {/* Create user dialog */}
      <Dialog open={createOpen} onOpenChange={setCreateOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Create User</DialogTitle>
            <DialogDescription>
              Create a new account. Share credentials securely with the user.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="space-y-1.5">
              <Label htmlFor="new-username">Username</Label>
              <Input
                id="new-username"
                value={newUsername}
                onChange={(e) => setNewUsername(e.target.value)}
                placeholder="Enter username"
              />
            </div>
            <div className="space-y-1.5">
              <div className="flex items-center justify-between">
                <Label>Password</Label>
                <button
                  type="button"
                  className="text-xs text-primary underline"
                  onClick={() => setAutoGen((a) => !a)}
                >
                  {autoGen ? "Set manually" : "Auto-generate"}
                </button>
              </div>
              {autoGen ? (
                <p className="text-sm text-muted-foreground italic">
                  A secure password will be generated automatically.
                </p>
              ) : (
                <Input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  placeholder="Enter password"
                />
              )}
            </div>
            <div className="space-y-1.5">
              <Label>Role</Label>
              <Select value={newRole} onValueChange={(v) => setNewRole(v as "admin" | "user")}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="user">User</SelectItem>
                  <SelectItem value="admin">Admin</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setCreateOpen(false)}>Cancel</Button>
            <Button
              disabled={!newUsername.trim() || (!autoGen && !newPassword) || createMutation.isPending}
              onClick={() => createMutation.mutate()}
            >
              {createMutation.isPending && <Loader2 size={14} className="mr-2 animate-spin" />}
              Create User
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset password result */}
      <Dialog open={!!resetResult} onOpenChange={() => setResetResult(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Temporary Password</DialogTitle>
            <DialogDescription>
              Share this with <strong>{resetResult?.username}</strong> securely. They should change it on first login.
            </DialogDescription>
          </DialogHeader>
          <div className="rounded-md bg-muted p-3 font-mono text-sm">
            {resetResult?.password}
          </div>
          <DialogFooter>
            <Button onClick={() => setResetResult(null)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
