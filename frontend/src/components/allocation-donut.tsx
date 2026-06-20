"use client";

import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";

import { fmtCurrency } from "@/lib/format";
import type { Holding } from "@/lib/types";

const COLORS = [
  "#2a5c32",
  "#ebdb88",
  "#6b9e5e",
  "#c9a227",
  "#122515",
  "#a9b89a",
  "#3e7c44",
  "#d9c76a",
];

export function AllocationDonut({ holdings }: { holdings: Holding[] }) {
  const data = holdings
    .map((h) => ({ name: h.symbol, value: h.market_value ?? h.cost_basis }))
    .filter((d) => d.value > 0);

  if (data.length === 0) {
    return (
      <div className="flex h-[240px] items-center justify-center text-sm text-muted-foreground">
        No holdings to allocate.
      </div>
    );
  }

  return (
    <ResponsiveContainer width="100%" height={240}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius={60}
          outerRadius={90}
          paddingAngle={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value) => fmtCurrency(Number(value))}
          contentStyle={{ fontSize: 12, borderRadius: 8 }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
