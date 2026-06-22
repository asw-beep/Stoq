"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { Plus, Trash2 } from "lucide-react";
import { useParams } from "next/navigation";
import { useState } from "react";
import { Controller, useForm } from "react-hook-form";
import { toast } from "sonner";
import { z } from "zod";

import { AllocationDonut } from "@/components/allocation-donut";
import { StatCard } from "@/components/stat-card";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
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
import { changeColor, fmtCurrency } from "@/lib/format";
import {
  useAddHolding,
  usePortfolio,
  usePortfolioAnalytics,
  useRemoveHolding,
  useStocks,
} from "@/lib/queries";

const holdingSchema = z.object({
  symbol: z.string().min(1, "Required").transform((s) => s.toUpperCase()),
  shares: z.coerce.number().positive("Must be > 0"),
  purchase_price: z.coerce.number().positive("Must be > 0"),
});
type HoldingForm = z.input<typeof holdingSchema>;

export default function PortfolioDetailPage() {
  const params = useParams<{ id: string }>();
  const id = Number(params.id);

  const { data, isLoading, isError, error } = usePortfolio(id);
  const { data: analytics } = usePortfolioAnalytics(id);
  const { data: stocksPage } = useStocks(200);
  const addHolding = useAddHolding(id);
  const removeHolding = useRemoveHolding(id);
  const [open, setOpen] = useState(false);

  const stocks = stocksPage?.items ?? [];

  const {
    register,
    control,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<HoldingForm>({
    resolver: zodResolver(holdingSchema),
    defaultValues: { symbol: "" },
  });

  const onAdd = handleSubmit(async (values) => {
    try {
      await addHolding.mutateAsync(holdingSchema.parse(values));
      toast.success("Holding added");
      reset();
      setOpen(false);
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not add holding");
    }
  });

  async function onRemove(holdingId: number) {
    try {
      await removeHolding.mutateAsync(holdingId);
      toast.success("Holding removed");
    } catch (err) {
      toast.error(err instanceof ApiError ? err.message : "Could not remove holding");
    }
  }

  if (isError && error instanceof ApiError && error.status === 404) {
    return (
      <p className="py-16 text-center text-sm text-muted-foreground">
        Portfolio not found.
      </p>
    );
  }

  if (isLoading || !data) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <div className="grid gap-4 sm:grid-cols-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full" />
          ))}
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{data.name}</h1>
          <p className="text-sm text-muted-foreground">
            {data.holdings.length} holding{data.holdings.length === 1 ? "" : "s"}
          </p>
        </div>
        <Dialog open={open} onOpenChange={setOpen}>
          <DialogTrigger render={<Button />}>
            <Plus className="size-4" /> Add holding
          </DialogTrigger>
          <DialogContent>
            <form onSubmit={onAdd}>
              <DialogHeader>
                <DialogTitle>Add holding</DialogTitle>
                <DialogDescription>
                  Pick a stock from the list and enter your position.
                </DialogDescription>
              </DialogHeader>
              <div className="space-y-4 py-4">
                <div className="space-y-2">
                  <Label htmlFor="symbol">Symbol</Label>
                  <Controller
                    control={control}
                    name="symbol"
                    render={({ field }) => (
                      <Select
                        value={field.value || ""}
                        onValueChange={(v) => field.onChange(v ?? "")}
                      >
                        <SelectTrigger id="symbol" className="w-full">
                          <SelectValue placeholder="Select a stock…" />
                        </SelectTrigger>
                        <SelectContent className="max-h-64">
                          {stocks.map((s) => (
                            <SelectItem key={s.symbol} value={s.symbol}>
                              {s.symbol}
                              {s.name ? ` — ${s.name}` : ""}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    )}
                  />
                  {errors.symbol && (
                    <p className="text-sm text-red-600">{errors.symbol.message}</p>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div className="space-y-2">
                    <Label htmlFor="shares">Shares</Label>
                    <Input
                      id="shares"
                      type="number"
                      step="any"
                      {...register("shares")}
                    />
                    {errors.shares && (
                      <p className="text-sm text-red-600">{errors.shares.message}</p>
                    )}
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="purchase_price">Buy price</Label>
                    <Input
                      id="purchase_price"
                      type="number"
                      step="any"
                      {...register("purchase_price")}
                    />
                    {errors.purchase_price && (
                      <p className="text-sm text-red-600">
                        {errors.purchase_price.message}
                      </p>
                    )}
                  </div>
                </div>
              </div>
              <DialogFooter>
                <Button type="submit" disabled={addHolding.isPending}>
                  {addHolding.isPending ? "Adding…" : "Add holding"}
                </Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Total cost" value={fmtCurrency(data.total_cost)} />
        <StatCard label="Market value" value={fmtCurrency(data.total_value)} />
        <StatCard
          label="Total gain / loss"
          value={fmtCurrency(data.total_gain_loss)}
          sub={
            analytics?.return_pct != null
              ? `${analytics.return_pct >= 0 ? "+" : ""}${analytics.return_pct.toFixed(2)}%`
              : undefined
          }
          valueClassName={changeColor(data.total_gain_loss)}
        />
      </div>

      {analytics && (
        <div className="grid gap-4 sm:grid-cols-4">
          <StatCard
            label="Ann. return"
            value={
              analytics.annualized_return != null
                ? `${analytics.annualized_return >= 0 ? "+" : ""}${analytics.annualized_return.toFixed(2)}%`
                : "—"
            }
            valueClassName={changeColor(analytics.annualized_return)}
          />
          <StatCard
            label="Ann. volatility"
            value={
              analytics.annualized_volatility != null
                ? `${analytics.annualized_volatility.toFixed(2)}%`
                : "—"
            }
          />
          <StatCard
            label="Sharpe ratio"
            value={
              analytics.sharpe_ratio != null
                ? analytics.sharpe_ratio.toFixed(2)
                : "—"
            }
            sub="Risk-free = 0%"
          />
          <StatCard
            label="Max drawdown"
            value={
              analytics.max_drawdown != null
                ? `${analytics.max_drawdown.toFixed(2)}%`
                : "—"
            }
            valueClassName={
              analytics.max_drawdown != null && analytics.max_drawdown > 0
                ? "text-red-600"
                : undefined
            }
          />
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Holdings</CardTitle>
          </CardHeader>
          <CardContent>
            {data.holdings.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No holdings yet. Add one to see valuation and allocation.
              </p>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead className="text-right">Shares</TableHead>
                    <TableHead className="text-right">Cost</TableHead>
                    <TableHead className="text-right">Value</TableHead>
                    <TableHead className="text-right">P/L</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.holdings.map((h) => (
                    <TableRow key={h.id}>
                      <TableCell className="font-medium">{h.symbol}</TableCell>
                      <TableCell className="text-right tabular-nums">
                        {h.shares}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {fmtCurrency(h.cost_basis)}
                      </TableCell>
                      <TableCell className="text-right tabular-nums">
                        {fmtCurrency(h.market_value)}
                      </TableCell>
                      <TableCell
                        className={`text-right tabular-nums ${changeColor(h.gain_loss)}`}
                      >
                        {fmtCurrency(h.gain_loss)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="size-8 text-muted-foreground hover:text-red-600"
                          onClick={() => onRemove(h.id)}
                          aria-label={`Remove ${h.symbol}`}
                        >
                          <Trash2 className="size-4" />
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Allocation</CardTitle>
          </CardHeader>
          <CardContent>
            <AllocationDonut holdings={data.holdings} />
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
