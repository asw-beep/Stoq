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
import { changeColor, fmtCurrency, fmtPercent } from "@/lib/format";
import { useMarketOverview } from "@/lib/queries";
import type { MarketOverviewItem } from "@/lib/types";

export default function MarketOverviewPage() {
  const { data, isLoading, isError } = useMarketOverview();

  const items = data ?? [];
  const withChange = items.filter((i) => i.change_pct != null);
  const topGainer = withChange.reduce<MarketOverviewItem | null>(
    (best, i) => (best == null || i.change_pct! > best.change_pct! ? i : best),
    null,
  );
  const topLoser = withChange.reduce<MarketOverviewItem | null>(
    (worst, i) => (worst == null || i.change_pct! < worst.change_pct! ? i : worst),
    null,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Market Overview</h1>
        <p className="text-sm text-muted-foreground">
          Latest close and day-over-day move for tracked stocks.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Tracked stocks" value={isLoading ? "—" : items.length} />
        <StatCard
          label="Top gainer"
          value={topGainer ? topGainer.symbol : "—"}
          sub={topGainer ? fmtPercent(topGainer.change_pct) : undefined}
          valueClassName={changeColor(topGainer?.change_pct)}
        />
        <StatCard
          label="Top loser"
          value={topLoser ? topLoser.symbol : "—"}
          sub={topLoser ? fmtPercent(topLoser.change_pct) : undefined}
          valueClassName={changeColor(topLoser?.change_pct)}
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Stocks</CardTitle>
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
              Failed to load market data.
            </p>
          ) : items.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No stocks ingested yet. Seed the backend (e.g. run the market-data
              ingest) to populate this view.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Symbol</TableHead>
                  <TableHead>Name</TableHead>
                  <TableHead className="text-right">Last</TableHead>
                  <TableHead className="text-right">Change</TableHead>
                  <TableHead className="text-right">%</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((s) => (
                  <TableRow key={s.symbol} className="cursor-pointer">
                    <TableCell className="font-medium">
                      <Link href={`/stocks/${s.symbol}`} className="hover:underline">
                        {s.symbol}
                      </Link>
                    </TableCell>
                    <TableCell className="max-w-[20ch] truncate text-muted-foreground">
                      {s.name ?? "—"}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">
                      {fmtCurrency(s.latest_close)}
                    </TableCell>
                    <TableCell
                      className={`text-right tabular-nums ${changeColor(s.change)}`}
                    >
                      {s.change == null ? "—" : fmtCurrency(s.change)}
                    </TableCell>
                    <TableCell className="text-right">
                      {s.change_pct == null ? (
                        "—"
                      ) : (
                        <Badge
                          variant="outline"
                          className={changeColor(s.change_pct)}
                        >
                          {fmtPercent(s.change_pct)}
                        </Badge>
                      )}
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
