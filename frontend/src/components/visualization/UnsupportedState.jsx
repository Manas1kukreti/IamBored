import React from "react";

/**
 * Displays an error or unsupported state message for visualizations.
 * Used when a VisualizationSpec has status "unsupported" or "failed",
 * or when the chart_type is not recognized.
 *
 * @param {object} props
 * @param {string} props.message - The error/info message to display
 * @param {"info"|"error"} [props.variant="info"] - Visual variant
 * @param {string} [props.className] - Additional CSS class names
 */
export default function UnsupportedState({
  message,
  variant = "info",
  className = "",
}) {
  const baseClass = "ff-viz-state";
  const variantClass =
    variant === "error" ? `${baseClass}--error` : `${baseClass}--info`;

  return (
    <div className={`${baseClass} ${variantClass} ${className}`.trim()}>
      <div className={`${baseClass}__icon`}>
        {variant === "error" ? (
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <line x1="12" y1="8" x2="12" y2="13" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="16" r="1" fill="currentColor" />
          </svg>
        ) : (
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            aria-hidden="true"
          >
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" />
            <line x1="12" y1="11" x2="12" y2="16" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="8" r="1" fill="currentColor" />
          </svg>
        )}
      </div>
      <p className={`${baseClass}__message`}>{message}</p>
    </div>
  );
}
