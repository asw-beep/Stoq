"use client";

import { useParams } from "next/navigation";
import { useState } from "react";
import { toast } from "sonner";

import { NewsList } from "@/components/news-list";
import { PriceForecastChart } from "@/components/price-forecast-chart";
import { SentimentSummary } from "@/components/sentiment-summary";
import { StatCard } from "@/components/stat-card";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { ApiError } from "@/lib/api";
import { changeColor, fmtCurrency, fmtPercent } from "@/lib/format";
import {
  useForecasts,
  useGenerateForecast,
  useIngestNews,
  useNews,
  usePrices,
  useStock,
} from "@/lib/queries";
import type { ForecastModel, PriceRange } from "@/lib/types";

export default function StockDetailPage() {
  const params = useParams<{ symbol: string }>();
  const symbol = (params.symbol ?? "").toUpperCase();

  const [range, setRange] = useState<PriceRange>("1y");
  const [model] = useState<ForecastModel>("xgboost");

  const stock = useStock(symbol);
  const prices = usePrices(symbol, range);
  const forecasts = useForecasts(symbol, model);
  const news = useNews(symbol);
  const genForecast = useGenerateForecast(symbol);
  const ingestNews = useIngestNews(symbol);

  const bars = prices.data ?? [];
  const last = bars.at(-1)?.close ?? null;
  const prev = bars.at(-2)?.close ?? null;
  const change = last != null && prev != null ? last - prev : null;
  const changePct = change != null && prev ? (change / prev) * 100 : null;

  const nextDayForecast = (forecasts.data ?? []).find((f) => f.direction != null);

  const notFound = stock.isError && stock.error instanceof ApiError && stock.error.status === 404;

  async function onGenerate() {
    try {
      await genForecast.mutateAsync(model);
      toast.success(`Generated ${model} forecast for ${symbol}`);
    } catch (err) {
      toast.error(
        err instanceof ApiError ? err.message : "Could not generate forecast",
      );
    }
  }

  async function onIngest() {
    try {
      await ingestNews.mutateAsync();
      toast.success(`Ingested news for ${symbol}`);
    } catch (err) {
      const msg =
        err instanceof ApiError && err.status === 503
          ? "News provider not configured (set FINNHUB_API_KEY on the backend)."
          : err instanceof ApiError
            ? err.message
            : "Could not ingest news";
      toast.error(msg);
    }
  }

  if (notFound) {
    return (
      <div className="py-16 text-center">
        <h1 className="text-2xl font-semibold">{symbol}</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          This symbol hasn’t been ingested into the system yet.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{symbol}</h1>
          <p className="text-sm text-muted-foreground">
            {stock.data?.name ?? ""}
            {stock.data?.sector ? ` · ${stock.data.sector}` : ""}
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={onIngest} disabled={ingestNews.isPending}>
            {ingestNews.isPending ? "Ingesting…" : "Ingest news"}
          </Button>
          <Button onClick={onGenerate} disabled={genForecast.isPending}>
            {genForecast.isPending ? "Forecasting…" : "Generate forecast"}
          </Button>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-3">
        <StatCard label="Last close" value={fmtCurrency(last)} />
        <StatCard
          label="Day change"
          value={change == null ? "—" : fmtCurrency(change)}
          sub={changePct == null ? undefined : fmtPercent(changePct)}
          valueClassName={changeColor(change)}
        />
        <StatCard
          label="Signal (tomorrow)"
          value={
            nextDayForecast?.direction == null
              ? "—"
              : nextDayForecast.direction === 1
                ? "▲ UP"
                : "▼ DOWN"
          }
          sub={
            nextDayForecast?.probability != null
              ? `${Math.round(nextDayForecast.probability * 100)}% confidence`
              : undefined
          }
          valueClassName={
            nextDayForecast?.direction === 1
              ? "text-green-600"
              : nextDayForecast?.direction === 0
                ? "text-red-500"
                : undefined
          }
        />
      </div>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
          <CardTitle>Price &amp; forecast</CardTitle>
          <div className="flex gap-2">
            <Select value={range} onValueChange={(v) => setRange(v as PriceRange)}>
              <SelectTrigger className="w-24" aria-label="Price range">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {(["1m", "3m", "6m", "1y", "max"] as PriceRange[]).map((r) => (
                  <SelectItem key={r} value={r}>
                    {r}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardHeader>
        <CardContent>
          {prices.isLoading ? (
            <Skeleton className="h-[320px] w-full" />
          ) : prices.isError ? (
            <p className="py-12 text-center text-sm text-red-600">
              Failed to load prices.
            </p>
          ) : (
            <PriceForecastChart prices={bars} forecasts={forecasts.data ?? []} />
          )}
          <p className="mt-3 text-xs text-muted-foreground">
            <span className="text-[#2a5c32]">—</span> historical close
          </p>
        </CardContent>
      </Card>

      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle>Sentiment</CardTitle>
          </CardHeader>
          <CardContent>
            {news.isLoading ? (
              <Skeleton className="h-20 w-full" />
            ) : (
              <SentimentSummary articles={news.data ?? []} />
            )}
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent news</CardTitle>
          </CardHeader>
          <CardContent>
            {news.isLoading ? (
              <div className="space-y-2">
                {Array.from({ length: 4 }).map((_, i) => (
                  <Skeleton key={i} className="h-12 w-full" />
                ))}
              </div>
            ) : (
              <NewsList articles={news.data ?? []} />
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
