import React from "react";
import { render } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";

// Capture props passed to Recharts components for verification
const capturedProps = {};

vi.mock("recharts", () => ({
  ResponsiveContainer: ({ children }) => <div data-testid="responsive-container">{children}</div>,
  BarChart: ({ children, data }) => {
    capturedProps.BarChart = { data };
    return <div className="mock-bar-chart" data-data={JSON.stringify(data)}>{children}</div>;
  },
  Bar: (props) => {
    capturedProps.Bar = props;
    return <div className="mock-bar" data-datakey={props.dataKey} data-name={props.name} />;
  },
  XAxis: (props) => {
    capturedProps.XAxis = props;
    return <div className="mock-xaxis" data-datakey={props.dataKey} data-label={props.label?.value} />;
  },
  YAxis: (props) => {
    capturedProps.YAxis = props;
    return <div className="mock-yaxis" data-label={props.label?.value} />;
  },
  CartesianGrid: () => <div className="mock-grid" />,
  Tooltip: (props) => {
    capturedProps.Tooltip = props;
    return <div className="mock-tooltip" />;
  },
  Legend: (props) => {
    capturedProps.Legend = props;
    return <div className="mock-legend" />;
  },
}));

import BarVisualization from "./BarVisualization.jsx";

function makeSpec(overrides = {}) {
  return {
    chart_type: "bar",
    title: "Revenue by Month",
    encoding: {
      x: "month_field_id",
      y: "revenue_field_id",
      x_label: "Month",
      y_label: "Revenue",
    },
    data: [
      { month_field_id: "Jan", revenue_field_id: 42000 },
      { month_field_id: "Feb", revenue_field_id: 51000 },
      { month_field_id: "Mar", revenue_field_id: 47000 },
    ],
    options: {},
    ...overrides,
  };
}

describe("BarVisualization", () => {
  it("renders with ff-viz-chart--bar class", () => {
    const { container } = render(<BarVisualization spec={makeSpec()} />);
    expect(container.querySelector(".ff-viz-chart--bar")).toBeInTheDocument();
  });

  it("renders an accessible role=img element with the chart title as aria-label", () => {
    const { container } = render(<BarVisualization spec={makeSpec()} />);
    const chart = container.querySelector('[role="img"]');
    expect(chart).toBeInTheDocument();
    expect(chart.getAttribute("aria-label")).toBe("Revenue by Month");
  });

  it("passes encoding.x as XAxis dataKey", () => {
    render(<BarVisualization spec={makeSpec()} />);
    expect(capturedProps.XAxis.dataKey).toBe("month_field_id");
  });

  it("passes encoding.y as Bar dataKey", () => {
    render(<BarVisualization spec={makeSpec()} />);
    expect(capturedProps.Bar.dataKey).toBe("revenue_field_id");
  });

  it("uses x_label for XAxis label value", () => {
    render(<BarVisualization spec={makeSpec()} />);
    expect(capturedProps.XAxis.label.value).toBe("Month");
  });

  it("uses y_label for YAxis label value", () => {
    render(<BarVisualization spec={makeSpec()} />);
    expect(capturedProps.YAxis.label.value).toBe("Revenue");
  });

  it("falls back to field ID when labels are not provided", () => {
    const spec = makeSpec({
      encoding: { x: "month_field_id", y: "revenue_field_id" },
    });
    render(<BarVisualization spec={spec} />);
    expect(capturedProps.XAxis.label.value).toBe("month_field_id");
    expect(capturedProps.YAxis.label.value).toBe("revenue_field_id");
  });

  it("uses y_label as the Bar name (used for legend)", () => {
    render(<BarVisualization spec={makeSpec()} />);
    expect(capturedProps.Bar.name).toBe("Revenue");
  });

  it("passes spec.data to BarChart", () => {
    const spec = makeSpec();
    render(<BarVisualization spec={spec} />);
    expect(capturedProps.BarChart.data).toEqual(spec.data);
  });

  it("renders with empty data without crashing", () => {
    const spec = makeSpec({ data: [] });
    const { container } = render(<BarVisualization spec={spec} />);
    expect(container.querySelector(".ff-viz-chart--bar")).toBeInTheDocument();
  });
});
