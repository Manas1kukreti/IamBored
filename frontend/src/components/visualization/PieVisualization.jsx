import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

/**
 * Default color palette for pie slices — FinFlow dark theme compatible.
 */
const COLORS = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#06b6d4", // cyan
  "#10b981", // emerald
  "#f59e0b", // amber
  "#ef4444", // red
  "#ec4899", // pink
  "#14b8a6", // teal
  "#f97316", // orange
  "#84cc16", // lime
  "#a855f7", // purple
  "#22d3ee", // light cyan
];

/**
 * PieVisualization — renders a Recharts PieChart from a VisualizationSpec.
 *
 * Uses encoding.category as the name key and encoding.value as the
 * numeric value key for each pie slice.
 *
 * @param {object} props
 * @param {object} props.spec - VisualizationSpec with chart_type "pie"
 * @param {object} props.spec.encoding - { category, value, category_label, value_label }
 * @param {Array} props.spec.data - Array of row objects
 * @param {string} props.spec.title - Chart title
 */
export default function PieVisualization({ spec }) {
  const { encoding = {}, data = [] } = spec;
  const categoryKey = encoding.category;
  const valueKey = encoding.value;
  const categoryLabel = encoding.category_label || categoryKey;
  const valueLabel = encoding.value_label || valueKey;

  if (!data.length || !categoryKey || !valueKey) {
    return (
      <div className="ff-viz-chart ff-viz-chart--pie">
        <p className="ff-viz-chart__empty">No data available</p>
      </div>
    );
  }

  return (
    <div className="ff-viz-chart ff-viz-chart--pie">
      <ResponsiveContainer width="100%" height={360}>
        <PieChart>
          <Pie
            data={data}
            dataKey={valueKey}
            nameKey={categoryKey}
            cx="50%"
            cy="50%"
            outerRadius={120}
            label={({ name, percent }) =>
              `${name} (${(percent * 100).toFixed(1)}%)`
            }
            labelLine
          >
            {data.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[index % COLORS.length]}
                className="ff-viz-chart__cell"
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [value, valueLabel]}
            labelFormatter={(label) => `${categoryLabel}: ${label}`}
            contentStyle={{
              backgroundColor: "rgba(15, 23, 42, 0.9)",
              border: "1px solid rgba(99, 102, 241, 0.3)",
              borderRadius: "8px",
              color: "#e2e8f0",
            }}
          />
          <Legend
            wrapperStyle={{ color: "#e2e8f0" }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  );
}
