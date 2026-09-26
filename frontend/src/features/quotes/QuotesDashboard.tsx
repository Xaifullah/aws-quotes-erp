import { useEffect, useMemo, useState } from "react";
import { AppShell } from "../../shared/ui/AppShell";
import { TopBar } from "../../shared/ui/TopBar";
import { StatCard } from "../../shared/ui/StatCard";
import { Pagination } from "../../shared/ui/Pagination";
import { decodeJwtPayload } from "../../shared/jwt";
import { downloadAsCsv, downloadAsJson } from "../../shared/exportData";
import { PipelineStatusPanel } from "../pipeline/PipelineStatusPanel";
import { QuotesTable } from "./QuotesTable";
import { AuthorsList } from "./AuthorsList";
import { TagFilter } from "./TagFilter";
import { useQuotes } from "./useQuotes";
import "./QuotesDashboard.css";

interface QuotesDashboardProps {
  token: string;
  onLogout: () => void;
}

type ActiveView = "quotes" | "authors";
type ActiveFilter = { type: "author" | "tag"; value: string } | null;

const DEFAULT_PAGE_SIZE = 10;

export function QuotesDashboard({ token, onLogout }: QuotesDashboardProps) {
  const { quotes, loading, error, reload } = useQuotes(token);
  const [search, setSearch] = useState("");
  const [activeView, setActiveView] = useState<ActiveView>("quotes");
  const [activeFilter, setActiveFilter] = useState<ActiveFilter>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(DEFAULT_PAGE_SIZE);

  const username = decodeJwtPayload<{ sub?: string }>(token)?.sub ?? "user";

  const filteredQuotes = useMemo(() => {
    const term = search.trim().toLowerCase();
    return quotes.filter((quote) => {
      if (activeFilter?.type === "author" && quote.author !== activeFilter.value) return false;
      if (activeFilter?.type === "tag" && !quote.tags.includes(activeFilter.value)) return false;
      if (!term) return true;
      return (
        quote.text.toLowerCase().includes(term) ||
        quote.author.toLowerCase().includes(term) ||
        quote.tags.some((tag) => tag.toLowerCase().includes(term))
      );
    });
  }, [quotes, search, activeFilter]);

  const uniqueAuthors = useMemo(() => new Set(quotes.map((q) => q.author)).size, [quotes]);
  const uniqueTags = useMemo(() => new Set(quotes.flatMap((q) => q.tags)).size, [quotes]);

  useEffect(() => {
    setPage(1);
  }, [search, activeFilter, pageSize]);

  const totalPages = Math.max(1, Math.ceil(filteredQuotes.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const pagedQuotes = useMemo(
    () => filteredQuotes.slice((safePage - 1) * pageSize, safePage * pageSize),
    [filteredQuotes, safePage, pageSize],
  );

  const goToAuthor = (author: string) => {
    setActiveFilter({ type: "author", value: author });
    setActiveView("quotes");
  };

  const toggleTag = (tag: string) => {
    setActiveFilter((current) => (current?.type === "tag" && current.value === tag ? null : { type: "tag", value: tag }));
  };

  const exportRows = filteredQuotes.map((q) => ({
    id: q.id,
    text: q.text,
    author: q.author,
    tags: q.tags,
    processed_at: q.processed_at,
  }));

  return (
    <AppShell
      username={username}
      onLogout={onLogout}
      navItems={[
        { id: "quotes", label: "Quotes", active: activeView === "quotes", onClick: () => setActiveView("quotes") },
        { id: "authors", label: "Authors", active: activeView === "authors", onClick: () => setActiveView("authors") },
      ]}
    >
      <TopBar
        title={activeView === "quotes" ? "Quotes" : "Authors"}
        subtitle="Scraped from quotes.toscrape.com, cleaned by the processing Lambda"
        actions={
          activeView === "quotes" ? (
            <>
              <input
                className="quotes-search"
                type="search"
                placeholder="Search quotes, authors, tags…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
              <button type="button" className="quotes-export" onClick={() => downloadAsJson("quotes.json", exportRows)}>
                Export JSON
              </button>
              <button type="button" className="quotes-export" onClick={() => downloadAsCsv("quotes.csv", exportRows)}>
                Export CSV
              </button>
              <button type="button" className="quotes-refresh" onClick={reload} disabled={loading}>
                {loading ? "Refreshing…" : "Refresh"}
              </button>
            </>
          ) : undefined
        }
      />
      <div className="app-shell-content">
        <PipelineStatusPanel token={token} />

        <div className="quotes-stats">
          <StatCard label="Total quotes" value={quotes.length} />
          <StatCard label="Authors" value={uniqueAuthors} />
          <StatCard label="Tags" value={uniqueTags} />
        </div>

        {error && <p className="quotes-error">{error}</p>}

        {activeView === "authors" ? (
          <AuthorsList quotes={quotes} onSelectAuthor={goToAuthor} />
        ) : (
          <>
            <TagFilter quotes={quotes} activeTag={activeFilter?.type === "tag" ? activeFilter.value : null} onSelectTag={toggleTag} />

            {activeFilter && (
              <div className="active-filter-chip">
                Filtering by {activeFilter.type}: <strong>{activeFilter.value}</strong>
                <button type="button" onClick={() => setActiveFilter(null)}>
                  Clear
                </button>
              </div>
            )}

            {loading && quotes.length === 0 ? (
              <p className="quotes-loading">Loading quotes…</p>
            ) : (
              <>
                <QuotesTable quotes={pagedQuotes} onAuthorClick={goToAuthor} onTagClick={toggleTag} />
                <Pagination
                  page={safePage}
                  totalPages={totalPages}
                  pageSize={pageSize}
                  totalItems={filteredQuotes.length}
                  onPageChange={setPage}
                  onPageSizeChange={setPageSize}
                />
              </>
            )}
          </>
        )}
      </div>
    </AppShell>
  );
}
