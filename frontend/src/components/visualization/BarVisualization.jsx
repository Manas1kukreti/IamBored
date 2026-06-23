import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

/**
 * BarVisualization — renders a Recharts BarChart bound to a VisualizationSpec.
 *
 * Uses encoding.x as XAxis dataKey and encoding.y as Bar dataKey.
 * Labels fall back to the field ID when x_label / y_label are not provided.
 *
 * @param {object} props
 * @param {object} props.spec - VisualizationSpec with chart_type "bar"
 */
export default function BarVisualization({ spec }) {
  const { encoding = {}, data = [], options = {} } = spec;

  const xField = encoding.x;
  const yField = encoding.y;
  const xLabel = encoding.x_label || xField;
  const yLabel = encoding.y_label || yField;

  // Theme colors aligned with FinFlow dark/glassmorphism
  const axisColor = "var(--ff-muted, #93a6c7)";
  const gridColor = "var(--ff-border, rgba(122, 162, 255, 0.18))";
  const barColor = "var(--ff-accent, #3b82f6)";
  const tooltipBg = "var(--ff-panel-strong, #0f1f36)";
  const tooltipBorder = "var(--ff-border, rgba(122, 162, 255, 0.18))";
  const textColor = "var(--ff-text, #e7eefc)";

  return (
    <div className="ff-viz-chart ff-viz-chart--bar" role="img" aria-label={spec.title || "Bar chart"}>
      <ResponsiveContainer width="100%" height={options.height || 320}>
        <BarChart
          data={data}
          margin={{ top: 16, right: 24, bottom: 32, left: 24 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke={gridColor} />
          <XAxis
            dataKey={xField}
            tick={{ fill: axisColor, fontSize: 12 }}
            axisLine={{ stroke: gridColor }}
            tickLine={{ stroke: gridColor }}
            label={{
              value: xLabel,
              position: "insideBottom",
              offset: -20,
              fill: axisColor,
              fontSize: 12,
            }}
          />
          <YAxis
            tick={{ fill: axisColor, fontSize: 12 }}
            axisLine={{ stroke: gridColor }}
            tickLine={{ stroke: gridColor }}
            label={{
              value: yLabel,
              angle: -90,
              position: "insideLeft",
              offset: -10,
              fill: axisColor,
              fontSize: 12,
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: tooltipBg,
              border: `1px solid ${tooltipBorder}`,
              borderRadius: 8,
              color: textColor,
            }}
            labelStyle={{ color: textColor, fontWeight: 600 }}
            itemStyle={{ color: textColor }}
            labelFormatter={(value) => `${xLabel}: ${value}`}
          />
          <Legend
            wrapperStyle={{ color: textColor, fontSize: 12 }}
          />
          <Bar
            dataKey={yField}
            name={yLabel}
            fill={barColor}
            radius={[4, 4, 0, 0]}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
