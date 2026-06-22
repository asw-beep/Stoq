"use client";

import Link from "next/link";

import { StatCard } from "@/components/stat-card";
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
import { useMarketSentiment } from "@/lib/queries";
import type { MarketSentiment } from "@/lib/types";

function SentimentBar({ item }: { item: MarketSentiment }) {
  if (item.total === 0) {
    return <span className="text-xs text-muted-foreground">No data</span>;
  }
  const posPct = Math.round((item.positive / item.total) * 100);
  const negPct = Math.round((item.negative / item.total) * 100);
  const neuPct = 100 - posPct - negPct;
  return (
    <div className="flex h-2 w-full min-w-[80px] overflow-hidden rounded-full">
      {posPct > 0 && (
        <div className="bg-emerald-500" style={{ width: `${posPct}%` }} />
      )}
      {neuPct > 0 && (
        <div className="bg-slate-300" style={{ width: `${neuPct}%` }} />
      )}
      {negPct > 0 && (
        <div className="bg-red-500" style={{ width: `${negPct}%` }} />
      )}
    </div>
  );
}

export default function SentimentDashboardPage() {
  const { data, isLoading, isError } = useMarketSentiment();

  const items = data ?? [];
  const withData = items.filter((i) => i.total > 0);
  const mostBullish = withData.reduce<MarketSentiment | null>(
    (best, i) =>
      best == null || i.positive / i.total > best.positive / best.total
        ? i
        : best,
    null,
  );
  const mostBearish = withData.reduce<MarketSentiment | null>(
    (worst, i) =>
      worst == null || i.negative / i.total > worst.negative / worst.total
        ? i
        : worst,
    null,
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Sentiment Dashboard
        </h1>
        <p className="text-sm text-muted-foreground">
          FinBERT sentiment scores aggregated across all ingested news.
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard
          label="Stocks with news"
          value={isLoading ? "—" : withData.length}
        />
        <StatCard
          label="Most bullish"
          value={mostBullish?.symbol ?? "—"}
          sub={
            mostBullish
              ? `${Math.round((mostBullish.positive / mostBullish.total) * 100)}% positive`
              : undefined
          }
          valueClassName="text-emerald-600"
        />
        <StatCard
          label="Most bearish"
          value={mostBearish?.symbol ?? "—"}
          sub={
            mostBearish
              ? `${Math.round((mostBearish.negative / mostBearish.total) * 100)}% negative`
              : undefined
          }
          valueClassName="text-red-600"
        />
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Sentiment by stock</CardTitle>
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
              Failed to load sentiment data.
            </p>
          ) : items.length === 0 ? (
            <p className="py-8 text-center text-sm text-muted-foreground">
              No stocks tracked yet.
            </p>
          ) : (
            <>
              <div className="mb-3 flex items-center gap-3 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-3 rounded-sm bg-emerald-500" />
                  Positive
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-3 rounded-sm bg-slate-300" />
                  Neutral
                </span>
                <span className="flex items-center gap-1">
                  <span className="inline-block h-2 w-3 rounded-sm bg-red-500" />
                  Negative
                </span>
              </div>
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Symbol</TableHead>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-40">Sentiment</TableHead>
                    <TableHead className="text-right">Positive</TableHead>
                    <TableHead className="text-right">Neutral</TableHead>
                    <TableHead className="text-right">Negative</TableHead>
                    <TableHead className="text-right">Articles</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {items.map((item) => (
                    <TableRow key={item.symbol}>
                      <TableCell className="font-medium">
                        <Link
                          href={`/stocks/${item.symbol}`}
                          className="hover:underline"
                        >
                          {item.symbol}
                        </Link>
                      </TableCell>
                      <TableCell className="max-w-[20ch] truncate text-muted-foreground">
                        {item.name ?? "—"}
                      </TableCell>
                      <TableCell>
                        <SentimentBar item={item} />
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-emerald-600">
                        {item.total > 0
                          ? `${Math.round((item.positive / item.total) * 100)}%`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {item.total > 0
                          ? `${Math.round((item.neutral / item.total) * 100)}%`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-red-600">
                        {item.total > 0
                          ? `${Math.round((item.negative / item.total) * 100)}%`
                          : "—"}
                      </TableCell>
                      <TableCell className="text-right tabular-nums text-muted-foreground">
                        {item.total > 0 ? item.total : "—"}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
