import "@testing-library/jest-dom";

// Mock ResizeObserver for Recharts ResponsiveContainer in jsdom
globalThis.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};
