"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { ApiError } from "@/lib/api";
import { fmtDate } from "@/lib/format";
import { useAdminUsers } from "@/lib/queries";

export default function AdminUsersPage() {
  const { data, isLoading, isError, error } = useAdminUsers();
  const users = data?.items ?? [];
  const forbidden = error instanceof ApiError && error.status === 403;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Users</h1>
        <p className="text-sm text-muted-foreground">
          All registered accounts. Visible to admins only.
        </p>
      </div>

      {isLoading ? (
        <Skeleton className="h-48 w-full" />
      ) : forbidden ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            You don’t have permission to view this page.
          </CardContent>
        </Card>
      ) : isError ? (
        <p className="py-8 text-center text-sm text-red-600">Failed to load users.</p>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-16">ID</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Registered</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {users.map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="text-muted-foreground">{u.id}</TableCell>
                    <TableCell className="font-medium">{u.email}</TableCell>
                    <TableCell>
                      <Badge variant={u.role === "admin" ? "default" : "secondary"}>
                        {u.role}
                      </Badge>
                    </TableCell>
                    <TableCell className="text-muted-foreground">
                      {fmtDate(u.created_at)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
            {data ? (
              <p className="border-t px-4 py-2 text-xs text-muted-foreground">
                {data.total} user{data.total === 1 ? "" : "s"} registered.
              </p>
            ) : null}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
