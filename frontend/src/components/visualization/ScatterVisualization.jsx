import React from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

/**
 * ScatterVisualization — renders a Recharts ScatterChart from a VisualizationSpec.
 *
 * Uses encoding.x and encoding.y as the XAxis/YAxis dataKeys.
 *
 * @param {object} props
 * @param {object} props.spec - VisualizationSpec with chart_type "scatter"
 * @param {object} props.spec.encoding - { x, y, x_label, y_label }
 * @param {Array} props.spec.data - Array of row objects
 * @param {string} props.spec.title - Chart title
 */
export default function ScatterVisualization({ spec }) {
  const { encoding = {}, data = [] } = spec;
  const xKey = encoding.x;
  const yKey = encoding.y;
  const xLabel = encoding.x_label || xKey;
  const yLabel = encoding.y_label || yKey;

  if (!data.length || !xKey || !yKey) {
    return (
      <div className="ff-viz-chart ff-viz-chart--scatter">
        <p className="ff-viz-chart__empty">No data available</p>
      </div>
    );
  }

  return (
    <div className="ff-viz-chart ff-viz-chart--scatter">
      <ResponsiveContainer width="100%" height={360}>
        <ScatterChart margin={{ top: 20, right: 30, bottom: 20, left: 20 }}>
          <CartesianGrid
            strokeDasharray="3 3"
            stroke="rgba(148, 163, 184, 0.15)"
            className="ff-viz-chart__grid"
          />
          <XAxis
            dataKey={xKey}
            name={xLabel}
            type="number"
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
            dataKey={yKey}
            name={yLabel}
            type="number"
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
            cursor={{ strokeDasharray: "3 3" }}
            formatter={(value, name) => {
              const label = name === xKey ? xLabel : yLabel;
              return [value, label];
            }}
            contentStyle={{
              backgroundColor: "rgba(15, 23, 42, 0.9)",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              borderRadius: "8px",
              color: "#e2e8f0",
            }}
          />
          <Scatter
            data={data}
            fill="#6366f1"
            fillOpacity={0.7}
            className="ff-viz-chart__scatter-dots"
          />
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
