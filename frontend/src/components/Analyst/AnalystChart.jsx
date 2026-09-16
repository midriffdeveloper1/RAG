import { useMemo, useState } from "react";
import {
  detectColumnType,
  formatValue,
  humanizeColumn,
  isNumeric,
} from "../../utils/analystFormat.js";

/**
 * Charts are drawn as hand-rolled SVG rather than with a charting library.
 * The project has no chart dependency, and the three shapes the agent can
 * choose (bar / line / pie) are simple enough that adding one would cost more
 * than it saves — and would ship a large bundle for an admin-only page.
 */

const MAX_SLICES = 12;

// Derived from the admin theme's sage/clay palette rather than a generic
// chart palette, so charts sit inside the existing design language.
const PALETTE = [
  "#2f4538",
  "#c17b6b",
  "#6b8f71",
  "#d9a273",
  "#4a6b57",
  "#a8624f",
  "#8fae94",
  "#e0bc93",
  "#3a5744",
  "#b98d7a",
  "#7d9e84",
  "#6b6459",
];

const LINE_COLOR = "#2f4538";

function useChartData(chart, columns, rows) {
  return useMemo(() => {
    if (!chart || !columns?.length || !rows?.length) return null;

    const labelIndex = columns.indexOf(chart.label_column);
    const valueIndex = columns.indexOf(chart.value_column);

    if (labelIndex === -1 || valueIndex === -1) return null;

    const valueType = detectColumnType(columns[valueIndex], rows, valueIndex);

    const points = rows
      .filter((row) => isNumeric(row[valueIndex]))
      .map((row) => ({
        rawLabel: row[labelIndex],
        label: formatValue(row[labelIndex], detectColumnType(columns[labelIndex], rows, labelIndex)),
        value: row[valueIndex],
      }));

    if (points.length < 2) return null;

    return {
      points: points.slice(0, MAX_SLICES),
      overflow: Math.max(0, points.length - MAX_SLICES),
      valueType,
      labelName: humanizeColumn(columns[labelIndex]),
      valueName: humanizeColumn(columns[valueIndex]),
    };
  }, [chart, columns, rows]);
}

function truncateLabel(label, max = 16) {
  const str = String(label ?? "");
  return str.length > max ? `${str.slice(0, max - 1)}…` : str;
}

export default function AnalystChart({ chart, columns, rows }) {
  const data = useChartData(chart, columns, rows);
  const [hovered, setHovered] = useState(null);

  if (!data) return null;

  const { points, valueType, valueName, labelName, overflow } = data;

  return (
    <figure className="analyst-chart">
      <figcaption className="analyst-chart__caption">
        {valueName} by {labelName}
        {overflow > 0 && (
          <span className="analyst-chart__note"> · top {points.length} shown</span>
        )}
      </figcaption>

      {chart.type === "bar" && (
        <BarChart points={points} valueType={valueType} onHover={setHovered} hovered={hovered} />
      )}
      {chart.type === "line" && (
        <LineChart points={points} valueType={valueType} onHover={setHovered} hovered={hovered} />
      )}
      {chart.type === "pie" && (
        <PieChart points={points} valueType={valueType} onHover={setHovered} hovered={hovered} />
      )}
    </figure>
  );
}

/* ---------------------------------------------------------------- bar ---- */

function BarChart({ points, valueType, onHover, hovered }) {
  const width = 640;
  const height = 260;
  const padding = { top: 16, right: 16, bottom: 52, left: 64 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const maxValue = Math.max(...points.map((p) => p.value), 0);
  const minValue = Math.min(...points.map((p) => p.value), 0);
  const span = maxValue - minValue || 1;

  const bandWidth = plotWidth / points.length;
  const barWidth = Math.min(48, bandWidth * 0.62);

  const zeroY = padding.top + plotHeight - ((0 - minValue) / span) * plotHeight;

  return (
    <svg
      className="analyst-chart__svg"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      preserveAspectRatio="xMidYMid meet"
    >
      <GridLines
        padding={padding}
        plotWidth={plotWidth}
        plotHeight={plotHeight}
        minValue={minValue}
        maxValue={maxValue}
        valueType={valueType}
      />

      {points.map((point, index) => {
        const barHeight = (Math.abs(point.value - 0) / span) * plotHeight;
        const x = padding.left + index * bandWidth + (bandWidth - barWidth) / 2;
        const y = point.value >= 0 ? zeroY - barHeight : zeroY;
        const isHovered = hovered === index;

        return (
          <g key={index}>
            <rect
              x={x}
              y={y}
              width={barWidth}
              height={Math.max(1, barHeight)}
              rx={4}
              fill={PALETTE[index % PALETTE.length]}
              opacity={hovered === null || isHovered ? 1 : 0.45}
              onMouseEnter={() => onHover(index)}
              onMouseLeave={() => onHover(null)}
            />

            {isHovered && (
              <text
                x={x + barWidth / 2}
                y={y - 6}
                textAnchor="middle"
                className="analyst-chart__value-label"
              >
                {formatValue(point.value, valueType)}
              </text>
            )}

            <text
              x={x + barWidth / 2}
              y={height - padding.bottom + 16}
              textAnchor="end"
              transform={`rotate(-35 ${x + barWidth / 2} ${height - padding.bottom + 16})`}
              className="analyst-chart__tick"
            >
              {truncateLabel(point.label)}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

/* --------------------------------------------------------------- line ---- */

function LineChart({ points, valueType, onHover, hovered }) {
  const width = 640;
  const height = 260;
  const padding = { top: 16, right: 16, bottom: 52, left: 64 };

  const plotWidth = width - padding.left - padding.right;
  const plotHeight = height - padding.top - padding.bottom;

  const maxValue = Math.max(...points.map((p) => p.value));
  const minValue = Math.min(...points.map((p) => p.value), 0);
  const span = maxValue - minValue || 1;

  const stepX = points.length > 1 ? plotWidth / (points.length - 1) : 0;

  const coords = points.map((point, index) => ({
    x: padding.left + index * stepX,
    y: padding.top + plotHeight - ((point.value - minValue) / span) * plotHeight,
    point,
  }));

  const path = coords.map((c, i) => `${i === 0 ? "M" : "L"} ${c.x} ${c.y}`).join(" ");
  const areaPath = `${path} L ${coords[coords.length - 1].x} ${padding.top + plotHeight} L ${
    coords[0].x
  } ${padding.top + plotHeight} Z`;

  return (
    <svg
      className="analyst-chart__svg"
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      preserveAspectRatio="xMidYMid meet"
    >
      <GridLines
        padding={padding}
        plotWidth={plotWidth}
        plotHeight={plotHeight}
        minValue={minValue}
        maxValue={maxValue}
        valueType={valueType}
      />

      <path d={areaPath} fill={LINE_COLOR} opacity={0.12} />
      <path d={path} fill="none" stroke={LINE_COLOR} strokeWidth={2.5} strokeLinejoin="round" />

      {coords.map((coord, index) => (
        <g key={index}>
          <circle
            cx={coord.x}
            cy={coord.y}
            r={hovered === index ? 6 : 4}
            fill="#fff"
            stroke={LINE_COLOR}
            strokeWidth={2.5}
            onMouseEnter={() => onHover(index)}
            onMouseLeave={() => onHover(null)}
          />

          {hovered === index && (
            <text
              x={coord.x}
              y={coord.y - 12}
              textAnchor="middle"
              className="analyst-chart__value-label"
            >
              {formatValue(coord.point.value, valueType)}
            </text>
          )}

          <text
            x={coord.x}
            y={height - padding.bottom + 16}
            textAnchor="end"
            transform={`rotate(-35 ${coord.x} ${height - padding.bottom + 16})`}
            className="analyst-chart__tick"
          >
            {truncateLabel(coord.point.label)}
          </text>
        </g>
      ))}
    </svg>
  );
}

/* ---------------------------------------------------------------- pie ---- */

function PieChart({ points, valueType, onHover, hovered }) {
  const size = 240;
  const radius = 96;
  const center = size / 2;

  const total = points.reduce((sum, p) => sum + Math.max(0, p.value), 0);

  if (total <= 0) return null;

  let cursor = -Math.PI / 2;

  const slices = points.map((point, index) => {
    const fraction = Math.max(0, point.value) / total;
    const angle = fraction * Math.PI * 2;
    const start = cursor;
    const end = cursor + angle;
    cursor = end;

    const x1 = center + radius * Math.cos(start);
    const y1 = center + radius * Math.sin(start);
    const x2 = center + radius * Math.cos(end);
    const y2 = center + radius * Math.sin(end);
    const largeArc = angle > Math.PI ? 1 : 0;

    return {
      index,
      point,
      fraction,
      // A full-circle single slice can't be drawn with an arc path, so draw
      // it as a plain circle instead of a degenerate wedge.
      path:
        fraction >= 0.999
          ? null
          : `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`,
    };
  });

  return (
    <div className="analyst-chart__pie-wrap">
      <svg
        className="analyst-chart__pie"
        viewBox={`0 0 ${size} ${size}`}
        role="img"
        preserveAspectRatio="xMidYMid meet"
      >
        {slices.map((slice) =>
          slice.path === null ? (
            <circle
              key={slice.index}
              cx={center}
              cy={center}
              r={radius}
              fill={PALETTE[slice.index % PALETTE.length]}
            />
          ) : (
            <path
              key={slice.index}
              d={slice.path}
              fill={PALETTE[slice.index % PALETTE.length]}
              opacity={hovered === null || hovered === slice.index ? 1 : 0.45}
              onMouseEnter={() => onHover(slice.index)}
              onMouseLeave={() => onHover(null)}
            />
          ),
        )}
      </svg>

      <ul className="analyst-chart__legend">
        {slices.map((slice) => (
          <li
            key={slice.index}
            className={`analyst-chart__legend-item ${
              hovered === slice.index ? "analyst-chart__legend-item--active" : ""
            }`}
            onMouseEnter={() => onHover(slice.index)}
            onMouseLeave={() => onHover(null)}
          >
            <span
              className="analyst-chart__swatch"
              style={{ background: PALETTE[slice.index % PALETTE.length] }}
            />
            <span className="analyst-chart__legend-label">
              {truncateLabel(slice.point.label, 22)}
            </span>
            <span className="analyst-chart__legend-value">
              {formatValue(slice.point.value, valueType)}
              <span className="analyst-chart__legend-pct">
                {" "}
                ({(slice.fraction * 100).toFixed(0)}%)
              </span>
            </span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* -------------------------------------------------------------- shared --- */

function GridLines({ padding, plotWidth, plotHeight, minValue, maxValue, valueType }) {
  const ticks = 4;
  const lines = [];

  for (let i = 0; i <= ticks; i += 1) {
    const ratio = i / ticks;
    const y = padding.top + plotHeight - ratio * plotHeight;
    const value = minValue + ratio * (maxValue - minValue);

    lines.push(
      <g key={i}>
        <line
          x1={padding.left}
          y1={y}
          x2={padding.left + plotWidth}
          y2={y}
          className="analyst-chart__grid"
        />
        <text x={padding.left - 10} y={y + 4} textAnchor="end" className="analyst-chart__tick">
          {formatValue(value, valueType === "currency" ? "number" : valueType)}
        </text>
      </g>,
    );
  }

  return <g>{lines}</g>;
}
