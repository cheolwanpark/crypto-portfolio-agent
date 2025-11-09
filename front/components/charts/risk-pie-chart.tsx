"use client"

import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts"
import type { RiskContributionData } from "@/lib/types"

const COLORS = ["#0088FE", "#00C49F", "#FFBB28", "#FF8042", "#8884d8", "#82ca9d"]

export function RiskPieChart({ data }: { data: RiskContributionData }) {
  const chartData = data.contributions.map((c) => ({
    name: c.asset,
    value: Math.abs(c.risk_pct),
    valuePct: c.value_pct,
  }))

  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4">Risk Contribution</h3>
      <ResponsiveContainer width="100%" height={250}>
        <PieChart>
          <Pie
            data={chartData}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            outerRadius={80}
            label={(entry: any) =>
              `${entry.name} ${(entry.percent * 100).toFixed(0)}%`
            }
          >
            {chartData.map((entry, index) => (
              <Cell
                key={`cell-${index}`}
                fill={COLORS[index % COLORS.length]}
              />
            ))}
          </Pie>
          <Tooltip
            formatter={(value: number, name: string, props: any) => [
              `${value.toFixed(2)}% risk (${props.payload.valuePct.toFixed(2)}% value)`,
              name,
            ]}
          />
          <Legend />
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-4 space-y-1 text-sm text-muted-foreground">
        <p>
          Diversification Benefit: {data.diversification_benefit.toFixed(2)}%
        </p>
        <p>Total Risk: {data.total_risk.toFixed(4)}</p>
      </div>
    </div>
  )
}
