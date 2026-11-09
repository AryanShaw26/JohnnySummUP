import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";
import { Link } from "react-router-dom";

interface Props {
  icon: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  actionLink?: string;
  onAction?: () => void;
  children?: ReactNode;
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionText,
  actionLink,
  onAction,
  children,
}: Props) {
  return (
    <div className="domain-placeholder" style={{ minHeight: "280px", padding: "40px 20px" }}>
      <div className="domain-placeholder__icon" style={{ width: 48, height: 48, marginBottom: 14 }}>
        <Icon size={22} aria-hidden="true" />
      </div>
      <h3 style={{ fontSize: 18, marginBottom: 6, color: "var(--ink)" }}>{title}</h3>
      <p className="domain-placeholder__copy" style={{ fontSize: 13, marginBottom: 18, maxWidth: 400 }}>
        {description}
      </p>
      {actionText && actionLink && (
        <Link to={actionLink} className="button button--primary button--compact">
          {actionText}
        </Link>
      )}
      {actionText && onAction && !actionLink && (
        <button type="button" onClick={onAction} className="button button--primary button--compact">
          {actionText}
        </button>
      )}
      {children}
    </div>
  );
}
