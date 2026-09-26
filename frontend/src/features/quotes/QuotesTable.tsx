import { Badge } from "../../shared/ui/Badge";
import { formatDate } from "../../shared/formatDate";
import type { Quote } from "./quotesApi";
import "./QuotesTable.css";

interface QuotesTableProps {
  quotes: Quote[];
  onAuthorClick: (author: string) => void;
  onTagClick: (tag: string) => void;
}

const MAX_VISIBLE_TAGS = 3;

export function QuotesTable({ quotes, onAuthorClick, onTagClick }: QuotesTableProps) {
  if (quotes.length === 0) {
    return <p className="quotes-table-empty">No quotes match your search.</p>;
  }

  return (
    <div className="quotes-table-wrap">
      <table className="quotes-table">
        <thead>
          <tr>
            <th className="col-quote">Quote</th>
            <th className="col-author">Author</th>
            <th className="col-tags">Tags</th>
            <th className="col-date">Processed</th>
          </tr>
        </thead>
        <tbody>
          {quotes.map((quote) => {
            const visibleTags = quote.tags.slice(0, MAX_VISIBLE_TAGS);
            const remaining = quote.tags.length - visibleTags.length;
            return (
              <tr key={quote.id}>
                <td className="col-quote" title={quote.text}>
                  {quote.text}
                </td>
                <td className="col-author">
                  <button type="button" className="link-button" onClick={() => onAuthorClick(quote.author)}>
                    {quote.author}
                  </button>
                </td>
                <td className="col-tags">
                  <div className="quotes-table-tags">
                    {visibleTags.map((tag) => (
                      <Badge key={tag} onClick={() => onTagClick(tag)}>
                        {tag}
                      </Badge>
                    ))}
                    {remaining > 0 && <Badge tone="accent">{`+${remaining}`}</Badge>}
                  </div>
                </td>
                <td className="col-date">{formatDate(quote.processed_at)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
