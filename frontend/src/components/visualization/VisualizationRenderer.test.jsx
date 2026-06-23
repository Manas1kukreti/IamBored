import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import VisualizationRenderer from "./VisualizationRenderer.jsx";

function makeSpec(overrides = {}) {
  return {
    schema_version: "1.0",
    visualization_id: "test-uuid",
    operation_id: "op_1",
    source_result_id: "result_1",
    status: "ready",
    chart_type: "bar",
    title: "Revenue by Month",
    encoding: { x: "month", y: "revenue" },
    data: [{ month: "Jan", revenue: 1000 }],
    options: {},
    warnings: [],
    error: null,
    ...overrides,
  };
}

describe("VisualizationRenderer", () => {
  it("renders null when no spec is provided", () => {
    const { container } = render(<VisualizationRenderer spec={null} />);
    expect(container.firstChild).toBeNull();
  });

  it("dispatches to LineVisualization for chart_type 'line'", () => {
    const { container } = render(
      <VisualizationRenderer spec={makeSpec({ chart_type: "line" })} />
    );
    expect(container.querySelector(".ff-viz-chart--line")).toBeInTheDocument();
  });

  it("dispatches to BarVisualization for chart_type 'bar'", () => {
    const { container } = render(
      <VisualizationRenderer spec={makeSpec({ chart_type: "bar" })} />
    );
    expect(container.querySelector(".ff-viz-chart--bar")).toBeInTheDocument();
  });

  it("dispatches to PieVisualization for chart_type 'pie'", () => {
    const spec = makeSpec({
      chart_type: "pie",
      encoding: { category: "dept", value: "amount", category_label: "Department", value_label: "Amount" },
      data: [{ dept: "Sales", amount: 500 }, { dept: "Eng", amount: 300 }],
    });
    const { container } = render(<VisualizationRenderer spec={spec} />);
    expect(container.querySelector(".ff-viz-chart--pie")).toBeInTheDocument();
  });

  it("dispatches to ScatterVisualization for chart_type 'scatter'", () => {
    const spec = makeSpec({
      chart_type: "scatter",
      encoding: { x: "height", y: "weight", x_label: "Height", y_label: "Weight" },
      data: [{ height: 170, weight: 65 }, { height: 180, weight: 75 }],
    });
    const { container } = render(<VisualizationRenderer spec={spec} />);
    expect(container.querySelector(".ff-viz-chart--scatter")).toBeInTheDocument();
  });

  it("dispatches to HistogramVisualization for chart_type 'histogram'", () => {
    const spec = makeSpec({
      chart_type: "histogram",
      encoding: { x: "bin", y: "freq", x_label: "Bin", y_label: "Frequency" },
      data: [{ bin: "0-10", freq: 5 }, { bin: "10-20", freq: 12 }],
    });
    const { container } = render(<VisualizationRenderer spec={spec} />);
    expect(container.querySelector(".ff-viz-chart--histogram")).toBeInTheDocument();
  });

  it("displays info-state for unsupported status", () => {
    const spec = makeSpec({
      status: "unsupported",
      error: "Data shape incompatible with line chart",
      data: [],
      encoding: {},
    });
    render(<VisualizationRenderer spec={spec} />);
    expect(
      screen.getByText("Data shape incompatible with line chart")
    ).toBeInTheDocument();
    // Should use info variant (ff-viz-state--info class)
    const stateEl = document.querySelector(".ff-viz-state--info");
    expect(stateEl).toBeInTheDocument();
  });

  it("displays error-state for failed status", () => {
    const spec = makeSpec({
      status: "failed",
      error: "Source data missing",
      data: [],
      encoding: {},
    });
    render(<VisualizationRenderer spec={spec} />);
    expect(screen.getByText("Source data missing")).toBeInTheDocument();
    // Should use error variant (ff-viz-state--error class)
    const stateEl = document.querySelector(".ff-viz-state--error");
    expect(stateEl).toBeInTheDocument();
  });

  it("displays unsupported message for unknown chart_type", () => {
    render(
      <VisualizationRenderer spec={makeSpec({ chart_type: "treemap" })} />
    );
    expect(
      screen.getByText('Chart type "treemap" is not supported')
    ).toBeInTheDocument();
  });

  it("renders the chart title when status is ready", () => {
    render(
      <VisualizationRenderer spec={makeSpec({ title: "My Test Chart" })} />
    );
    expect(screen.getByText("My Test Chart")).toBeInTheDocument();
  });

  it("applies ff-viz-renderer class", () => {
    const { container } = render(
      <VisualizationRenderer spec={makeSpec()} />
    );
    expect(container.querySelector(".ff-viz-renderer")).toBeInTheDocument();
  });

  it("passes additional className prop", () => {
    const { container } = render(
      <VisualizationRenderer spec={makeSpec()} className="custom-class" />
    );
    expect(container.querySelector(".ff-viz-renderer.custom-class")).toBeInTheDocument();
  });
});
