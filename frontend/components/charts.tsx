"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const GRID = "#1b2029";
const AXIS = "#6b7383";
const PALETTE = [
  "#3ddc97",
  "#5aa9f5",
  "#e2b93b",
  "#f0655a",
  "#b58af5",
  "#48c5d8",
  "#ef8f4e",
  "#7f8ca4",
  "#d85fa8",
  "#8fd85f",
  "#f5d05a",
  "#5f8cf5",
];

const tooltipStyle = {
  backgroundColor: "#12161f",
  border: "1px solid #1b2029",
  borderRadius: "6px",
  fontSize: "12px",
  color: "#e8ecf3",
};

export function OpportunitiesOverTimeChart({
  data,
  height = 240,
}: {
  data: { date: string; count: number; avg_roi: number | null }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <AreaChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <defs>
          <linearGradient id="roiFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3ddc97" stopOpacity={0.25} />
            <stop offset="100%" stopColor="#3ddc97" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="date" tick={{ fill: AXIS, fontSize: 10 }} tickFormatter={(d: string) => d.slice(5)} />
        <YAxis tick={{ fill: AXIS, fontSize: 10 }} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} />
        <Area type="monotone" dataKey="count" name="Opportunities" stroke="#3ddc97" fill="url(#roiFill)" strokeWidth={1.5} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function RoiDistributionChart({
  data,
  height = 240,
}: {
  data: { label: string; count: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="label" tick={{ fill: AXIS, fontSize: 10 }} />
        <YAxis tick={{ fill: AXIS, fontSize: 10 }} allowDecimals={false} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#171c26" }} />
        <Bar dataKey="count" name="Opportunities" fill="#5aa9f5" radius={[2, 2, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function HorizontalBarChart({
  data,
  dataKey,
  nameKey,
  color = "#3ddc97",
  height = 260,
  valueLabel,
}: {
  data: Record<string, unknown>[];
  dataKey: string;
  nameKey: string;
  color?: string;
  height?: number;
  valueLabel?: string;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={data} layout="vertical" margin={{ top: 4, right: 16, bottom: 0, left: 30 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" horizontal={false} />
        <XAxis type="number" tick={{ fill: AXIS, fontSize: 10 }} allowDecimals={false} />
        <YAxis
          type="category"
          dataKey={nameKey}
          tick={{ fill: AXIS, fontSize: 11 }}
          width={100}
        />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "#171c26" }} />
        <Bar dataKey={dataKey} name={valueLabel ?? dataKey} fill={color} radius={[0, 2, 2, 0]} barSize={14} />
      </BarChart>
    </ResponsiveContainer>
  );
}

export function DonutChart({
  data,
  height = 240,
}: {
  data: { name: string; value: number }[];
  height?: number;
}) {
  return (
    <ResponsiveContainer width="100%" height={height}>
      <PieChart>
        <Pie
          data={data}
          dataKey="value"
          nameKey="name"
          innerRadius="55%"
          outerRadius="80%"
          paddingAngle={2}
          stroke="#090b10"
          strokeWidth={2}
        >
          {data.map((_, i) => (
            <Cell key={i} fill={PALETTE[i % PALETTE.length]} />
          ))}
        </Pie>
        <Tooltip contentStyle={tooltipStyle} />
      </PieChart>
    </ResponsiveContainer>
  );
}

export function PortfolioCurveChart({
  data,
  height = 240,
}: {
  data: number[];
  height?: number;
}) {
  const points = data.map((profit, i) => ({ i, profit }));
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={points} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
        <CartesianGrid stroke={GRID} strokeDasharray="3 3" vertical={false} />
        <XAxis dataKey="i" tick={{ fill: AXIS, fontSize: 10 }} />
        <YAxis tick={{ fill: AXIS, fontSize: 10 }} />
        <Tooltip contentStyle={tooltipStyle} labelFormatter={(l: number) => `Trade ${l + 1}`} />
        <Line type="stepAfter" dataKey="profit" name="Cumulative profit (simulated)" stroke="#5aa9f5" strokeWidth={1.5} dot={false} />
      </LineChart>
    </ResponsiveContainer>
  );
}
