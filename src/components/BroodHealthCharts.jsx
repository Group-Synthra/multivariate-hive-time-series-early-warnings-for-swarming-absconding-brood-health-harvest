import React from "react";
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ComposedChart,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

function formatTimestamp(value) {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value ?? "");
  return parsed.toLocaleString();
}

const tooltipStyle = {
  background: "#1e293b",
  border: "1px solid #334155",
  borderRadius: "8px",
};

export function HealthTimelineChart({ data = [] }) {
  return (
    <div className="card chart-card">
      <div className="chart-header">
        <h3>📈 Brood Health Score &amp; BHSI Timeline</h3>
        <p>Current rule-based health index and six-hour stability index.</p>
      </div>

      <div className="chart-container" style={{ height: 320 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={data}
            margin={{ top: 8, right: 24, left: 4, bottom: 8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.05)"
            />
            <XAxis
              dataKey="timestamp"
              minTickGap={28}
              tickFormatter={(value) => {
                const parsed = new Date(value);
                return Number.isNaN(parsed.getTime())
                  ? value
                  : parsed.toLocaleDateString();
              }}
              stroke="var(--text-secondary)"
            />
            <YAxis domain={[0, 100]} stroke="var(--text-secondary)" />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={formatTimestamp}
              formatter={(value, name) => [Number(value).toFixed(2), name]}
            />
            <Legend />

            <ReferenceLine
              y={80}
              stroke="#10b981"
              strokeDasharray="4 4"
              label={{
                value: "Excellent starts: 80",
                fill: "#10b981",
                position: "insideTopRight",
              }}
            />
            <ReferenceLine
              y={60}
              stroke="#34d399"
              strokeDasharray="4 4"
              label={{
                value: "Good starts: 60",
                fill: "#34d399",
                position: "insideTopRight",
              }}
            />
            <ReferenceLine
              y={40}
              stroke="#f59e0b"
              strokeDasharray="4 4"
              label={{
                value: "Poor starts: 40",
                fill: "#f59e0b",
                position: "insideTopRight",
              }}
            />

            <Line
              type="monotone"
              dataKey="brood_health_score"
              stroke="var(--accent-emerald)"
              strokeWidth={2}
              dot={false}
              name="Brood Health Score"
              isAnimationActive={false}
            />
            <Line
              type="monotone"
              dataKey="bhsi"
              stroke="var(--accent-cyan)"
              strokeWidth={2}
              dot={false}
              name="BHSI"
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function RodTrendChart({ data = [] }) {
  return (
    <div className="card chart-card">
      <div className="chart-header">
        <h3>⏱️ Rate of Deterioration (RoD)</h3>
        <p>
          Score change in points per hour; negative values indicate decline.
        </p>
      </div>

      <div className="chart-container" style={{ height: 230 }}>
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart
            data={data}
            margin={{ top: 8, right: 18, left: 0, bottom: 8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.05)"
            />
            <XAxis
              dataKey="timestamp"
              minTickGap={28}
              tickFormatter={(value) => {
                const parsed = new Date(value);
                return Number.isNaN(parsed.getTime())
                  ? value
                  : parsed.toLocaleDateString();
              }}
              stroke="var(--text-secondary)"
            />
            <YAxis stroke="var(--text-secondary)" />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={formatTimestamp}
              formatter={(value) => [
                `${Number(value).toFixed(2)} pts/hr`,
                "RoD",
              ]}
            />
            <ReferenceLine y={0} stroke="#ffffff" strokeDasharray="3 3" />
            <ReferenceLine y={-3} stroke="#ef4444" strokeDasharray="4 4" />
            <Area
              type="monotone"
              dataKey="rod"
              stroke="var(--accent-crimson)"
              fill="var(--accent-crimson)"
              fillOpacity={0.3}
              name="RoD"
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function ApiaryBarChart({ data = [], colors = {} }) {
  const chartHeight = Math.max(350, data.length * 28);

  return (
    <div className="card chart-card">
      <div className="chart-header">
        <h3>🏠 Apiary Overview</h3>
        <p>
          Latest Brood Health Score for every hive, sorted from highest to
          lowest.
        </p>
      </div>

      <div
        className="chart-container"
        style={{ height: chartHeight, maxHeight: 700, overflowY: "auto" }}
      >
        <ResponsiveContainer width="100%" height="100%">
          <BarChart
            data={data}
            layout="vertical"
            margin={{ top: 10, right: 30, left: 60, bottom: 5 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.05)"
            />
            <XAxis
              type="number"
              domain={[0, 100]}
              stroke="var(--text-secondary)"
            />
            <YAxis
              type="category"
              dataKey="hive"
              stroke="var(--text-secondary)"
              tick={{ fontSize: 11 }}
              width={72}
            />
            <Tooltip
              contentStyle={tooltipStyle}
              formatter={(value, _name, properties) => [
                `${Number(value).toFixed(2)} (${properties.payload.health})`,
                "Health Score",
              ]}
            />
            <Bar
              dataKey="score"
              radius={[0, 8, 8, 0]}
              animationDuration={700}
              name="Health Score"
            >
              {data.map((entry) => (
                <Cell
                  key={`${entry.hive}-${entry.health}`}
                  fill={colors[entry.health] || "#64748b"}
                />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}

export function LiveEarlyWarningTimeline({ data = [] }) {
  return (
    <div className="card chart-card">
      <div className="chart-header">
        <div>
          <h3>🛰️ Ten-Minute Early-Warning Timeline</h3>
          <p>
            Current health and BHSI use the left axis; RoD uses the right axis.
          </p>
        </div>
      </div>

      <div className="chart-container" style={{ height: 360 }}>
        <ResponsiveContainer width="100%" height="100%">
          <ComposedChart
            data={data}
            margin={{ top: 10, right: 34, left: 4, bottom: 8 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="rgba(255,255,255,0.05)"
            />
            <XAxis
              dataKey="timestamp"
              minTickGap={34}
              tickFormatter={(value) => {
                const parsed = new Date(value);
                return Number.isNaN(parsed.getTime())
                  ? value
                  : parsed.toLocaleTimeString([], {
                      hour: "2-digit",
                      minute: "2-digit",
                    });
              }}
              stroke="var(--text-secondary)"
            />
            <YAxis
              yAxisId="score"
              domain={[0, 100]}
              stroke="var(--text-secondary)"
            />
            <YAxis
              yAxisId="rod"
              orientation="right"
              stroke="var(--text-secondary)"
            />
            <Tooltip
              contentStyle={tooltipStyle}
              labelFormatter={formatTimestamp}
              formatter={(value, name) => [
                name === "RoD"
                  ? `${Number(value).toFixed(2)} pts/hr`
                  : Number(value).toFixed(2),
                name,
              ]}
            />
            <Legend />
            <ReferenceLine
              yAxisId="score"
              y={40}
              stroke="#ef4444"
              strokeDasharray="4 4"
            />
            <ReferenceLine
              yAxisId="score"
              y={60}
              stroke="#f97316"
              strokeDasharray="4 4"
            />
            <ReferenceLine
              yAxisId="score"
              y={80}
              stroke="#10b981"
              strokeDasharray="4 4"
            />
            <ReferenceLine
              yAxisId="rod"
              y={0}
              stroke="#94a3b8"
              strokeDasharray="3 3"
            />
            <ReferenceLine
              yAxisId="rod"
              y={-3}
              stroke="#ef4444"
              strokeDasharray="3 3"
            />
            <Line
              yAxisId="score"
              type="monotone"
              dataKey="brood_health_score"
              name="Current Health"
              stroke="#10b981"
              strokeWidth={2.3}
              dot={false}
              isAnimationActive={false}
            />
            <Line
              yAxisId="score"
              type="monotone"
              dataKey="bhsi"
              name="BHSI"
              stroke="#22d3ee"
              strokeWidth={2.3}
              dot={false}
              isAnimationActive={false}
            />
            <Area
              yAxisId="rod"
              type="monotone"
              dataKey="rod"
              name="RoD"
              stroke="#f43f5e"
              fill="#f43f5e"
              fillOpacity={0.16}
              isAnimationActive={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
