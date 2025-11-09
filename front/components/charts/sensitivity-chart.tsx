"use client"

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts"
import type { SensitivityGraphData } from "@/lib/types"

export function SensitivityChart({ data }: { data: SensitivityGraphData }) {
  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4 text-white">
        Portfolio Value Sensitivity
      </h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={data.data_points}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="x"
            label={{
              value: "Price Change (%)",
              position: "insideBottom",
              offset: -5,
            }}
          />
          <YAxis
            label={{
              value: "Portfolio Value ($)",
              angle: -90,
              position: "insideLeft",
            }}
            tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
          />
          <Tooltip
            formatter={(value: number) => [
              `$${value.toLocaleString()}`,
              "Portfolio Value",
            ]}
            labelFormatter={(label) => `${label}% price change`}
          />
          <ReferenceLine
            x={0}
            stroke="#10b981"
            strokeDasharray="3 3"
            label="Current"
          />
          <Line
            type="monotone"
            dataKey="y"
            stroke="#8884d8"
            strokeWidth={2}
            dot={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <div className="mt-4 flex justify-between text-sm text-muted-foreground">
        <span>Min: ${data.value_range.min.toLocaleString()}</span>
        <span>Current: ${data.value_range.current.toLocaleString()}</span>
        <span>Max: ${data.value_range.max.toLocaleString()}</span>
      </div>
    </div>
  )
}
