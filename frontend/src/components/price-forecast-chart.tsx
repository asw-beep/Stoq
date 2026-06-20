"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

import { fmtCurrency } from "@/lib/format";
import type { Forecast, PriceBar } from "@/lib/types";

function DirectionBadge({ forecast }: { forecast: Forecast }) {
  const isUp = forecast.direction === 1;
  const pct = forecast.probability != null ? Math.round(forecast.probability * 100) : null;
  const horizon = (() => {
    const days = Math.round(
      (new Date(forecast.target_date).getTime() - new Date(forecast.forecast_date).getTime()) /
        86_400_000,
    );
    if (days === 1) return "Tomorrow";
    if (days <= 7) return `${days}d`;
    return `${days}d`;
  })();

  return (
    <div className="flex flex-col items-center gap-1 rounded-xl border bg-card px-5 py-3 text-center shadow-sm">
      <span className="text-xs text-muted-foreground">{horizon}</span>
      <span className={`text-2xl font-bold ${isUp ? "text-green-600" : "text-red-500"}`}>
        {isUp ? "▲" : "▼"}
      </span>
      <span className={`text-sm font-semibold ${isUp ? "text-green-600" : "text-red-500"}`}>
        {isUp ? "UP" : "DOWN"}
      </span>
      {pct != null && (
        <span className="text-xs text-muted-foreground">{pct}% confidence</span>
      )}
    </div>
  );
}

export function PriceForecastChart({
  prices,
  forecasts,
}: {
  prices: PriceBar[];
  forecasts: Forecast[];
}) {
  const data = prices.map((p) => ({ date: p.date, close: p.close }));
  const directionForecasts = forecasts.filter((f) => f.direction != null);

  if (data.length === 0) {
    return (
      <div className="flex h-[320px] items-center justify-center text-sm text-muted-foreground">
        No price history available.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <ResponsiveContainer width="100%" height={280}>
        <LineChart data={data} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
          <XAxis
            dataKey="date"
            tickFormatter={(d: string) => d.slice(5)}
            minTickGap={40}
            tick={{ fontSize: 12 }}
          />
          <YAxis
            domain={["auto", "auto"]}
            tickFormatter={(v: number) => `$${v.toFixed(0)}`}
            width={56}
            tick={{ fontSize: 12 }}
          />
          <Tooltip
            formatter={(value) => [fmtCurrency(Number(value)), "Close"]}
            labelClassName="text-xs"
            contentStyle={{ fontSize: 12, borderRadius: 8 }}
          />
          <Line
            type="monotone"
            dataKey="close"
            stroke="#2a5c32"
            strokeWidth={2}
            dot={false}
            name="close"
          />
        </LineChart>
      </ResponsiveContainer>

      {directionForecasts.length > 0 && (
        <div>
          <p className="mb-2 text-xs text-muted-foreground">
            Directional signal · XGBoost classifier · walk-forward validated
          </p>
          <div className="flex gap-3">
            {directionForecasts.map((f) => (
              <DirectionBadge key={f.target_date} forecast={f} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
