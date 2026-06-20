import { Badge } from "@/components/ui/badge";
import { fmtDate } from "@/lib/format";
import type { NewsArticle } from "@/lib/types";

function sentimentClass(label?: string) {
  switch (label?.toLowerCase()) {
    case "positive":
      return "text-emerald-600";
    case "negative":
      return "text-red-600";
    default:
      return "text-muted-foreground";
  }
}

export function NewsList({ articles }: { articles: NewsArticle[] }) {
  if (articles.length === 0) {
    return (
      <p className="py-6 text-center text-sm text-muted-foreground">
        No news yet. Use “Ingest news” to fetch and score recent articles.
      </p>
    );
  }

  return (
    <ul className="divide-y">
      {articles.map((a) => (
        <li key={a.id} className="flex items-start justify-between gap-3 py-3">
          <div className="min-w-0">
            {a.url ? (
              <a
                href={a.url}
                target="_blank"
                rel="noopener noreferrer"
                className="line-clamp-2 text-sm font-medium hover:underline"
              >
                {a.title}
              </a>
            ) : (
              <span className="line-clamp-2 text-sm font-medium">{a.title}</span>
            )}
            <div className="mt-1 text-xs text-muted-foreground">
              {a.source ?? "Unknown"} · {fmtDate(a.published_at)}
            </div>
          </div>
          {a.sentiment && (
            <Badge
              variant="outline"
              className={`shrink-0 ${sentimentClass(a.sentiment.sentiment)}`}
            >
              {a.sentiment.sentiment}
            </Badge>
          )}
        </li>
      ))}
    </ul>
  );
}
