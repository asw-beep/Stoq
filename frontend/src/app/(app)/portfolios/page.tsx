"use client";

import { Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { useCreatePortfolio, useDeletePortfolio, usePortfolios } from "@/lib/queries";

export default function PortfoliosPage() {
  const { data, isLoading, isError } = usePortfolios();
  const create = useCreatePortfolio();
  const remove = useDeletePortfolio();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState("");

  const portfolios = data?.items ?? [];

  async function onCreate(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) return;
    try {
      await create.mutateAsync(trimmed);
      toast.success(`Created “${trimmed}”`);
      setName("");
      setOpen(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not create portfolio");
    }
  }

  async function onDelete(id: number) {
    try {
      await remove.mutateAsync(id);
      toast.success("Portfolio deleted");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not delete");
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">Portfolios</h1>
          <p className="text-sm text-muted-foreground">
            Track holdings and live valuation.
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger render={<Button />}>
            <Plus className="size-4" /> New portfolio
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={onCreate}>
              <DialogHeader>
                <DialogTitle>New portfolio</DialogTitle>
                <DialogDescription>Give your portfolio a name.</DialogDescription>
              </DialogHeader>
              <div className="space-y-2 py-4">
                <Label htmlFor="name">Name</Label>
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="e.g. Long-term growth"
                  autoFocus
                />
              </div>
              <DialogFooter>
                <Button type="submit" disabled={create.isPending}>
                  {create.isPending ? "Creating…" : "Create"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-28 w-full" />
          ))}
        </div>
      ) : isError ? (
        <p className="py-8 text-center text-sm text-red-600">
          Failed to load portfolios.
        </p>
      ) : portfolios.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-sm text-muted-foreground">
            No portfolios yet. Create one to start adding holdings.
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {portfolios.map((p) => (
            <Card key={p.id} className="transition-shadow hover:shadow-md">
              <CardHeader className="flex flex-row items-start justify-between space-y-0">
                <CardTitle className="text-base">
                  <Link href={`/portfolios/${p.id}`} className="hover:underline">
                    {p.name}
                  </Link>
                </CardTitle>
                <Button
                  variant="ghost"
                  size="icon"
                  className="size-8 text-muted-foreground hover:text-red-600"
                  onClick={() => onDelete(p.id)}
                  aria-label="Delete portfolio"
                >
                  <Trash2 className="size-4" />
                </Button>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  {p.holding_count} holding{p.holding_count === 1 ? "" : "s"}
                </p>
                <Link
                  href={`/portfolios/${p.id}`}
                  className="mt-2 inline-block text-sm font-medium underline"
                >
                  View details →
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
