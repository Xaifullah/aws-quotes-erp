import { useState } from "react";
import { formatDate } from "../../shared/formatDate";
import { triggerScrape } from "./pipelineApi";
import { usePipelineStatus } from "./usePipelineStatus";
import "./PipelineStatusPanel.css";

interface PipelineStatusPanelProps {
  token: string;
  onScrapeProcessed?: () => void;
}

// The consumer Lambda drains SQS asynchronously; give it a few seconds before
// re-reading status and quotes so the new run shows up.
const POST_SCRAPE_REFRESH_MS = 8000;

export function PipelineStatusPanel({ token, onScrapeProcessed }: PipelineStatusPanelProps) {
  const { status, error, reload } = usePipelineStatus(token);
  const [scraping, setScraping] = useState(false);
  const [scrapeMessage, setScrapeMessage] = useState<{ text: string; tone: "ok" | "warn" } | null>(null);

  const handleScrape = async () => {
    setScraping(true);
    setScrapeMessage(null);
    try {
      const run = await triggerScrape(token);
      setScrapeMessage({
        text: `Queued ${run.published} quotes in ${run.messages} message${run.messages === 1 ? "" : "s"} — processing…`,
        tone: "ok",
      });
      window.setTimeout(() => {
        reload();
        onScrapeProcessed?.();
        setScraping(false);
      }, POST_SCRAPE_REFRESH_MS);
    } catch (err) {
      setScrapeMessage({ text: err instanceof Error ? err.message : "Scrape failed", tone: "warn" });
      setScraping(false);
    }
  };

  if (error) {
    return <p className="pipeline-error">{error}</p>;
  }

  if (!status) {
    return null;
  }

  const health: { label: string; tone: "ok" | "warn" } =
    status.raw_count === 0
      ? { label: "No scrape runs yet", tone: "warn" }
      : { label: "Pipeline healthy", tone: "ok" };

  return (
    <div className="pipeline-panel">
      <div className="pipeline-panel-header">
        <span className="pipeline-panel-title">Scrape pipeline</span>
        <div className="pipeline-panel-actions">
          <span className={`pipeline-health pipeline-health-${health.tone}`}>{health.label}</span>
          <button type="button" className="pipeline-scrape" onClick={handleScrape} disabled={scraping}>
            {scraping ? "Scraping…" : "Run scrape now"}
          </button>
        </div>
      </div>
      {scrapeMessage && (
        <p className={`pipeline-scrape-message pipeline-health-${scrapeMessage.tone}`}>{scrapeMessage.text}</p>
      )}
      <div className="pipeline-metrics">
        <div className="pipeline-metric">
          <span className="pipeline-metric-label">Scrape runs</span>
          <span className="pipeline-metric-value">{status.raw_count}</span>
        </div>
        <div className="pipeline-metric">
          <span className="pipeline-metric-label">Quotes in DB</span>
          <span className="pipeline-metric-value">{status.processed_count}</span>
        </div>
        <div className="pipeline-metric">
          <span className="pipeline-metric-label">Last scraped</span>
          <span className="pipeline-metric-value pipeline-metric-value-sm">
            {formatDate(status.last_scraped_at)}
          </span>
        </div>
        <div className="pipeline-metric">
          <span className="pipeline-metric-label">Last processed</span>
          <span className="pipeline-metric-value pipeline-metric-value-sm">
            {formatDate(status.last_processed_at)}
          </span>
        </div>
      </div>
    </div>
  );
}
