import { useMemo } from "react";
import type { Quote } from "./quotesApi";
import "./AuthorsList.css";

interface AuthorsListProps {
  quotes: Quote[];
  onSelectAuthor: (author: string) => void;
}

interface AuthorSummary {
  name: string;
  quoteCount: number;
  topTags: string[];
}

export function AuthorsList({ quotes, onSelectAuthor }: AuthorsListProps) {
  const authors = useMemo<AuthorSummary[]>(() => {
    const byAuthor = new Map<string, Quote[]>();
    for (const quote of quotes) {
      const existing = byAuthor.get(quote.author);
      if (existing) {
        existing.push(quote);
      } else {
        byAuthor.set(quote.author, [quote]);
      }
    }

    return Array.from(byAuthor.entries())
      .map(([name, authorQuotes]) => ({
        name,
        quoteCount: authorQuotes.length,
        topTags: Array.from(new Set(authorQuotes.flatMap((q) => q.tags))).slice(0, 3),
      }))
      .sort((a, b) => b.quoteCount - a.quoteCount || a.name.localeCompare(b.name));
  }, [quotes]);

  if (authors.length === 0) {
    return <p className="quotes-table-empty">No authors yet.</p>;
  }

  return (
    <div className="authors-grid">
      {authors.map((author) => (
        <button key={author.name} type="button" className="author-card" onClick={() => onSelectAuthor(author.name)}>
          <span className="author-card-name">{author.name}</span>
          <span className="author-card-count">
            {author.quoteCount} {author.quoteCount === 1 ? "quote" : "quotes"}
          </span>
          {author.topTags.length > 0 && (
            <span className="author-card-tags">{author.topTags.join(" · ")}</span>
          )}
        </button>
      ))}
    </div>
  );
}
