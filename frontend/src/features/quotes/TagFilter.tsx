import { useMemo } from "react";
import type { Quote } from "./quotesApi";
import "./TagFilter.css";

interface TagFilterProps {
  quotes: Quote[];
  activeTag: string | null;
  onSelectTag: (tag: string) => void;
}

const MAX_TAGS_SHOWN = 14;

export function TagFilter({ quotes, activeTag, onSelectTag }: TagFilterProps) {
  const tagCounts = useMemo(() => {
    const counts = new Map<string, number>();
    for (const quote of quotes) {
      for (const tag of quote.tags) {
        counts.set(tag, (counts.get(tag) ?? 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .sort((a, b) => b[1] - a[1])
      .slice(0, MAX_TAGS_SHOWN);
  }, [quotes]);

  if (tagCounts.length === 0) return null;

  return (
    <div className="tag-filter">
      <span className="tag-filter-label">Top tags</span>
      <div className="tag-filter-list">
        {tagCounts.map(([tag, count]) => (
          <button
            key={tag}
            type="button"
            className={`tag-filter-chip${tag === activeTag ? " is-active" : ""}`}
            onClick={() => onSelectTag(tag)}
          >
            {tag} <span className="tag-filter-count">{count}</span>
          </button>
        ))}
      </div>
    </div>
  );
}
