import { formatDate } from "../../shared/formatDate";
import { usePipelineStatus } from "./usePipelineStatus";
import "./PipelineStatusPanel.css";

interface PipelineStatusPanelProps {
  token: string;
}

export function PipelineStatusPanel({ token }: PipelineStatusPanelProps) {
  const { status, error } = usePipelineStatus(token);

  if (error) {
    return <p className="pipeline-error">{error}</p>;
  }

  if (!status) {
    return null;
  }

  const pending = status.raw_count - status.processed_count;
  const health: { label: string; tone: "ok" | "warn" } =
    pending > 0
      ? { label: `${pending} file${pending === 1 ? "" : "s"} pending processing`, tone: "warn" }
      : { label: "Pipeline up to date", tone: "ok" };

  return (
    <div className="pipeline-panel">
      <div className="pipeline-panel-header">
        <span className="pipeline-panel-title">Scrape pipeline</span>
        <span className={`pipeline-health pipeline-health-${health.tone}`}>{health.label}</span>
      </div>
      <div className="pipeline-metrics">
        <div className="pipeline-metric">
          <span className="pipeline-metric-label">Raw files (S3)</span>
          <span className="pipeline-metric-value">{status.raw_count}</span>
        </div>
        <div className="pipeline-metric">
          <span className="pipeline-metric-label">Processed files</span>
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
