import { Badge } from "@/components/ui/badge";
import type { NewsArticle } from "@/lib/types";

const COLORS: Record<string, string> = {
  positive: "bg-emerald-500",
  negative: "bg-red-500",
  neutral: "bg-slate-400",
};

export function SentimentSummary({ articles }: { articles: NewsArticle[] }) {
  const scored = articles.filter((a) => a.sentiment);
  const counts = { positive: 0, negative: 0, neutral: 0 } as Record<string, number>;
  for (const a of scored) {
    const label = a.sentiment!.sentiment.toLowerCase();
    counts[label] = (counts[label] ?? 0) + 1;
  }
  const total = scored.length;

  if (total === 0) {
    return (
      <p className="text-sm text-muted-foreground">
        No scored articles yet. Ingest news to compute sentiment.
      </p>
    );
  }

  const overall =
    counts.positive >= counts.negative && counts.positive >= counts.neutral
      ? "positive"
      : counts.negative >= counts.neutral
        ? "negative"
        : "neutral";

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2">
        <span className="text-sm text-muted-foreground">Overall</span>
        <Badge
          variant="outline"
          className={
            overall === "positive"
              ? "text-emerald-600"
              : overall === "negative"
                ? "text-red-600"
                : "text-muted-foreground"
          }
        >
          {overall} ({total})
        </Badge>
      </div>
      <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-muted">
        {(["positive", "neutral", "negative"] as const).map((k) =>
          counts[k] > 0 ? (
            <div
              key={k}
              className={COLORS[k]}
              style={{ width: `${(counts[k] / total) * 100}%` }}
              title={`${k}: ${counts[k]}`}
            />
          ) : null,
        )}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>▲ {counts.positive} positive</span>
        <span>● {counts.neutral} neutral</span>
        <span>▼ {counts.negative} negative</span>
      </div>
    </div>
  );
}
