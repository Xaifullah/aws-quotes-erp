import "./Badge.css";

interface BadgeProps {
  children: string;
  tone?: "neutral" | "accent";
  onClick?: () => void;
}

export function Badge({ children, tone = "neutral", onClick }: BadgeProps) {
  const className = `badge badge-${tone}${onClick ? " badge-clickable" : ""}`;

  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick}>
        {children}
      </button>
    );
  }

  return <span className={className}>{children}</span>;
}
