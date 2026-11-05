import React from 'react';
import {
  CheckCircle2,
  AlertTriangle,
  Clock,
  XCircle,
  HelpCircle,
  TrendingDown,
  TrendingUp,
} from 'lucide-react';
import type { ProcessingStatus, RangeStatus } from '../../types';

interface StatusBadgeProps {
  status: ProcessingStatus | RangeStatus | string;
  className?: string;
  size?: 'sm' | 'md';
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({
  status,
  className = '',
  size = 'md',
}) => {
  const norm = status.toLowerCase();

  const sizeClasses = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs';

  if (norm === 'within_range' || norm === 'normal' || norm === 'completed' || norm === 'processed') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#e8f5ee] text-[#168A4A] border border-[#168A4A]/20 ${sizeClasses} ${className}`}
      >
        <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
        <span>{norm === 'completed' ? 'Analysed' : 'Within reported range'}</span>
      </span>
    );
  }

  if (norm === 'below_range' || norm === 'low') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#fdf6e3] text-[#B98512] border border-[#B98512]/30 ${sizeClasses} ${className}`}
      >
        <TrendingDown className="w-3.5 h-3.5 shrink-0" />
        <span>Below stated range</span>
      </span>
    );
  }

  if (norm === 'above_range' || norm === 'high') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#fdf6e3] text-[#B98512] border border-[#B98512]/30 ${sizeClasses} ${className}`}
      >
        <TrendingUp className="w-3.5 h-3.5 shrink-0" />
        <span>Above stated range</span>
      </span>
    );
  }

  if (norm === 'needs_review') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#fdf6e3] text-[#B98512] border border-[#B98512]/30 ${sizeClasses} ${className}`}
      >
        <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
        <span>Needs review</span>
      </span>
    );
  }

  if (norm === 'processing' || norm === 'queued' || norm === 'uploaded') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#F0EEFF] text-[#6257F5] border border-[#6257F5]/20 ${sizeClasses} ${className}`}
      >
        <Clock className="w-3.5 h-3.5 shrink-0 animate-spin" />
        <span>{norm === 'processing' ? 'Processing' : 'Queued'}</span>
      </span>
    );
  }

  if (norm === 'failed' || norm === 'critical') {
    return (
      <span
        className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-[#fdeaea] text-[#C93636] border border-[#C93636]/30 ${sizeClasses} ${className}`}
      >
        <XCircle className="w-3.5 h-3.5 shrink-0" />
        <span>Failed</span>
      </span>
    );
  }

  // Fallback: unknown
  return (
    <span
      className={`inline-flex items-center gap-1.5 font-medium rounded-full bg-slate-100 text-[#77758A] border border-slate-200 ${sizeClasses} ${className}`}
    >
      <HelpCircle className="w-3.5 h-3.5 shrink-0" />
      <span>Range not stated</span>
    </span>
  );
};

export default StatusBadge;

