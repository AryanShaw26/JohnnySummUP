import type { DocumentStatus } from "../../types/medical";

interface Props {
  status: DocumentStatus | string;
}

export function ReportStatusBadge({ status }: Props) {
  switch (status) {
    case "completed":
      return <span className="badge badge--green">Analysed</span>;
    case "processing":
      return <span className="badge badge--purple">Processing...</span>;
    case "queued":
      return <span className="badge badge--purple">Queued</span>;
    case "failed":
      return <span className="badge badge--red">Failed</span>;
    case "analysis_unavailable":
      return <span className="badge badge--gray">Uploaded</span>;
    default:
      return <span className="badge badge--gray">{status}</span>;
  }
}
