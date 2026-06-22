"use client";

import Link from "next/link";

import { StatCard } from "@/components/stat-card";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { fmtDate } from "@/lib/format";
import { useMarketSignals } from "@/lib/queries";
import type { MarketSignal } from "@/lib/types";

function SignalBadge({ signal }: { signal: MarketSignal }) {
  if (signal.direction === 1) {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 hover:bg-emerald-100">
        ▲ UP
      </Badge>
    );
  }
  if (signal.direction === 0) {
    return (
      <Badge className="bg-red-100 text-red-700 hover:bg-red-100">▼ DOWN</Badge>
    );
  }
  return <Badge variant="outline">—</Badge>;
}

export default function ForecastDashboardPage() {
  const { data, isLoading, isError } = useMarketSignals();

  const signals = data ?? [];
  const upCount = signals.filter((s) => s.direction === 1).length;
  const downCount = signals.filter((s) => s.direction === 0).length;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Forecast Dashboard
        </h1>
        <p className="text-sm text-muted-foreground">
          Latest XGBoost directional signal for every tracked stock.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Stocks with signals" value={isLoading ? "—" : signals.length} />
        <StatCard
          label="Bullish signals"
          value={isLoading ? "—" : upCount}
          valueClassName="text-emerald-600"
        />
        <StatCard
          label="Bearish signals"
          value={isLoading ? "—" : downCount}
          valueClassName="text-red-600"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Signals</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="space-y-2">
              {Array.from({ length: 5 }).map((_, i) => (
                <Skeleton key={i} className="h-10 w-full" />
              ))}
            </div>
          ) : isError ? (
            <p className="py-8 text-center text-sm text-red-600">
              Failed to load forecast signals.
            </p>
          ) : signals.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No forecasts yet. Open a stock and click &quot;Generate
              forecast&quot; to populate signals.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead>Signal</TableHead>
                  <TableHead className="text-right">Confidence</TableHead>
                  <TableHead className="text-right">Forecast date</TableHead>
                  <TableHead className="text-right">Target date</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {signals.map((s) => (
                  <TableRow key={s.symbol}>
                    <TableCell className="font-medium">
                      <Link
                        href={`/stocks/${s.symbol}`}
                        className="hover:underline"
                      >
                        {s.symbol}
                      </Link>
                    </TableCell>
                    <TableCell className="max-w-[20ch] truncate text-muted-foreground">
                      {s.name ?? "—"}
                    </TableCell>
                    <TableCell>
                      <SignalBadge signal={s} />
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {s.probability != null
                        ? `${Math.round(s.probability * 100)}%`
                        : "—"}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {fmtDate(s.forecast_date)}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {fmtDate(s.target_date)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
