import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

/**
 * HistogramVisualization — renders a Recharts BarChart in histogram mode
 * from a VisualizationSpec.
 *
 * Uses encoding.x for bin labels (category axis) and encoding.y for
 * frequencies (numeric axis). Bars are rendered edge-to-edge (no gap)
 * to visually represent a histogram distribution.
 *
 * @param {object} props
 * @param {object} props.spec - VisualizationSpec with chart_type "histogram"
 * @param {object} props.spec.encoding - { x, y, x_label, y_label }
 * @param {Array} props.spec.data - Array of row objects (bin data)
 * @param {string} props.spec.title - Chart title
 */
export default function HistogramVisualization({ spec }) {
  const { encoding = {}, data = [] } = spec;
  const xKey = encoding.x;
  const yKey = encoding.y;
  const xLabel = encoding.x_label || xKey;
  const yLabel = encoding.y_label || yKey;

  if (!data.length || !xKey || !yKey) {
    return (
      <div className="ff-viz-chart ff-viz-chart--histogram">
        <p className="ff-viz-chart__empty">No data available</p>
      </div>
    );
  }

  return (
    <div className="ff-viz-chart ff-viz-chart--histogram">
      <ResponsiveContainer width="100%" height={360}>
        <BarChart
          data={data}
          margin={{ top: 20, right: 30, bottom: 20, left: 20 }}
          barCategoryGap={0}
          barGap={0}
        >
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(148, 163, 184, 0.15)"
            className="ff-viz-chart__grid"
          />
          <XAxis
            dataKey={xKey}
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            axisLine={{ stroke: "rgba(148, 163, 184, 0.3)" }}
            label={{
              value: xLabel,
              position: "bottom",
              offset: 0,
              fill: "#94a3b8",
            }}
          />
          <YAxis
            tick={{ fill: "#94a3b8", fontSize: 12 }}
            axisLine={{ stroke: "rgba(148, 163, 184, 0.3)" }}
            label={{
              value: yLabel,
              angle: -90,
              position: "insideLeft",
              fill: "#94a3b8",
            }}
          />
          <Tooltip
            formatter={(value) => [value, yLabel]}
            labelFormatter={(label) => `${xLabel}: ${label}`}
            contentStyle={{
              backgroundColor: "rgba(15, 23, 42, 0.9)",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              borderRadius: "8px",
              color: "#e2e8f0",
            }}
          />
          <Bar
            dataKey={yKey}
            fill="#6366f1"
            fillOpacity={0.85}
            stroke="#818cf8"
            strokeWidth={1}
            className="ff-viz-chart__bar"
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
