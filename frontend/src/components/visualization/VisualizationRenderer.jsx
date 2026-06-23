import React from "react";
import LineVisualization from "./LineVisualization.jsx";
import BarVisualization from "./BarVisualization.jsx";
import PieVisualization from "./PieVisualization.jsx";
import ScatterVisualization from "./ScatterVisualization.jsx";
import HistogramVisualization from "./HistogramVisualization.jsx";
import UnsupportedState from "./UnsupportedState.jsx";

/**
 * Chart type to component mapping.
 * Dispatches rendering to the appropriate subcomponent based on chart_type.
 */
const CHART_COMPONENTS = {
  line: LineVisualization,
  bar: BarVisualization,
  pie: PieVisualization,
  scatter: ScatterVisualization,
  histogram: HistogramVisualization,
};

/**
 * VisualizationRenderer — dispatches a VisualizationSpec to the correct
 * chart subcomponent, or renders an error/unsupported state.
 *
 * @param {object} props
 * @param {object} props.spec - VisualizationSpec object
 * @param {string} props.spec.status - "ready" | "unsupported" | "failed"
 * @param {string} props.spec.chart_type - "line" | "bar" | "pie" | "scatter" | "histogram"
 * @param {object} props.spec.encoding - Axis role to field ID mapping
 * @param {Array} props.spec.data - Array of row objects
 * @param {string} props.spec.title - Chart title
 * @param {string|null} props.spec.error - Error message (when status !== "ready")
 * @param {string[]} props.spec.warnings - Warning messages
 * @param {string} [props.className] - Additional CSS class names
 */
export default function VisualizationRenderer({ spec, className = "" }) {
  if (!spec) {
    return null;
  }

  // Handle unsupported status — display in info-state container
  if (spec.status === "unsupported") {
    return (
      <div className={`ff-viz-renderer ${className}`.trim()}>
        <UnsupportedState message={spec.error} variant="info" />
      </div>
    );
  }

  // Handle failed status — display in error-state container
  if (spec.status === "failed") {
    return (
      <div className={`ff-viz-renderer ${className}`.trim()}>
        <UnsupportedState message={spec.error} variant="error" />
      </div>
    );
  }

  // Dispatch to the correct chart subcomponent based on chart_type
  const ChartComponent = CHART_COMPONENTS[spec.chart_type];

  // Handle unknown chart_type — display "chart type not supported" message
  if (!ChartComponent) {
    return (
      <div className={`ff-viz-renderer ${className}`.trim()}>
        <UnsupportedState
          message={`Chart type "${spec.chart_type}" is not supported`}
          variant="info"
        />
      </div>
    );
  }

  return (
    <div className={`ff-viz-renderer ${className}`.trim()}>
      {spec.title && (
        <h3 className="ff-viz-renderer__title">{spec.title}</h3>
      )}
      <ChartComponent spec={spec} />
    </div>
  );
}
