import { useState } from "react";
import type { TrendPoint } from "../../types/medical";

interface Props {
  points: TrendPoint[];
  parameterName: string;
  unit: string;
  referenceRange?: string | null;
}

export function TrendChart({ points, parameterName, unit }: Props) {
  const [hoveredPoint, setHoveredPoint] = useState<TrendPoint | null>(null);

  if (!points || points.length === 0) {
    return (
      <div style={{ height: 260, display: "grid", placeItems: "center", color: "var(--muted)", fontSize: 13 }}>
        No trend data recorded for {parameterName}.
      </div>
    );
  }

  const width = 640;
  const height = 240;
  const padding = { top: 25, right: 30, bottom: 40, left: 50 };

  const values = points.map((p) => p.value);
  const minVal = Math.min(...values);
  const maxVal = Math.max(...values);
  const spread = maxVal - minVal || 1;
  const yMin = Math.max(0, Math.floor(minVal - spread * 0.25));
  const yMax = Math.ceil(maxVal + spread * 0.25);

  const chartWidth = width - padding.left - padding.right;
  const chartHeight = height - padding.top - padding.bottom;

  const getX = (index: number) => {
    if (points.length === 1) return padding.left + chartWidth / 2;
    return padding.left + (index / (points.length - 1)) * chartWidth;
  };

  const getY = (val: number) => {
    const ratio = (val - yMin) / (yMax - yMin || 1);
    return padding.top + chartHeight - ratio * chartHeight;
  };

  const linePath = points
    .map((p, idx) => `${idx === 0 ? "M" : "L"} ${getX(idx)} ${getY(p.value)}`)
    .join(" ");

  return (
    <div style={{ position: "relative", width: "100%" }}>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        style={{ width: "100%", height: "auto", overflow: "visible" }}
      >
        {/* Horizontal grid lines */}
        {[0, 0.33, 0.66, 1].map((pct, idx) => {
          const val = yMin + pct * (yMax - yMin);
          const y = getY(val);
          return (
            <g key={idx}>
              <line
                x1={padding.left}
                y1={y}
                x2={width - padding.right}
                y2={y}
                stroke="#eeeaf4"
                strokeDasharray="4 4"
              />
              <text
                x={padding.left - 8}
                y={y + 4}
                textAnchor="end"
                fontSize={10}
                fill="#918a9e"
              >
                {val.toFixed(1)}
              </text>
            </g>
          );
        })}

        {/* Trend line */}
        <path
          d={linePath}
          fill="none"
          stroke="var(--purple)"
          strokeWidth={3}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Data points */}
        {points.map((p, idx) => {
          const cx = getX(idx);
          const cy = getY(p.value);
          const isHovered = hoveredPoint?.date === p.date && hoveredPoint?.value === p.value;
          return (
            <g key={idx}>
              <circle
                cx={cx}
                cy={cy}
                r={isHovered ? 7 : 5}
                fill={p.is_abnormal ? "#ef4444" : "#ffffff"}
                stroke="var(--purple)"
                strokeWidth={isHovered ? 3 : 2}
                style={{ cursor: "pointer", transition: "r 0.15s ease" }}
                onMouseEnter={() => setHoveredPoint(p)}
                onMouseLeave={() => setHoveredPoint(null)}
              />
              {/* Date label on X-axis */}
              <text
                x={cx}
                y={height - 12}
                textAnchor="middle"
                fontSize={11}
                fill="#777085"
                fontWeight={500}
              >
                {new Date(p.date).toLocaleDateString(undefined, {
                  month: "short",
                  year: "numeric",
                })}
              </text>
            </g>
          );
        })}
      </svg>

      {/* Tooltip */}
      {hoveredPoint && (
        <div
          style={{
            position: "absolute",
            top: 10,
            right: 15,
            padding: "8px 14px",
            background: "#241c38",
            color: "#ffffff",
            borderRadius: 8,
            fontSize: 12,
            boxShadow: "0 6px 18px rgba(0,0,0,0.15)",
            zIndex: 10,
          }}
        >
          <div>
            <strong>{hoveredPoint.value} {unit}</strong>
          </div>
          <div style={{ color: "#c1bad0", fontSize: 11, marginTop: 2 }}>
            {hoveredPoint.document_name} ({hoveredPoint.date})
          </div>
          {hoveredPoint.is_abnormal && (
            <div style={{ color: "#fca5a5", fontSize: 10, marginTop: 2, fontWeight: 700 }}>
              Outside reference range
            </div>
          )}
        </div>
      )}
    </div>
  );
}
