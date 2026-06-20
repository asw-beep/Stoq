"use client";

import { useRouter } from "next/navigation";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { useLogout, useMe } from "@/lib/queries";

export default function AccountPage() {
  const router = useRouter();
  const { data: me, isLoading } = useMe();
  const logout = useLogout();

  async function onLogout() {
    try {
      await logout.mutateAsync();
      router.replace("/login");
      router.refresh();
    } catch {
      toast.error("Could not log out");
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <h1 className="text-2xl font-semibold tracking-tight">Account</h1>
      <Card>
        <CardHeader>
          <CardTitle>Profile</CardTitle>
          <CardDescription>Your account details.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLoading ? (
            <Skeleton className="h-12 w-full" />
          ) : (
            <dl className="grid grid-cols-3 gap-2 text-sm">
              <dt className="text-muted-foreground">Email</dt>
              <dd className="col-span-2 font-medium">{me?.email ?? "—"}</dd>
              <dt className="text-muted-foreground">Role</dt>
              <dd className="col-span-2 font-medium capitalize">{me?.role ?? "—"}</dd>
            </dl>
          )}
          <Button
            variant="outline"
            onClick={onLogout}
            disabled={logout.isPending}
          >
            {logout.isPending ? "Logging out…" : "Log out"}
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
