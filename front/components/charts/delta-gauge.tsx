"use client"

import { PieChart, Pie, Cell, ResponsiveContainer } from "recharts"
import type { DeltaGaugeData } from "@/lib/types"

export function DeltaGauge({ data }: { data: DeltaGaugeData }) {
  // Convert delta to gauge percentage (normalized -1 to +1 → 0 to 100)
  const gaugeValue = ((data.delta_normalized + 1) / 2) * 100

  const gaugeData = [
    { name: "value", value: gaugeValue },
    { name: "remaining", value: 100 - gaugeValue },
  ]

  const getColorByStatus = (status: string) => {
    if (status === "neutral") return "#10b981" // green
    if (status.includes("slight")) return "#f59e0b" // yellow
    return "#ef4444" // red
  }

  const getStatusLabel = (status: string) => {
    return status.replace(/_/g, " ").toUpperCase()
  }

  return (
    <div className="rounded-xl border bg-card p-6">
      <h3 className="text-lg font-semibold mb-4 text-white">Delta Gauge</h3>
      <ResponsiveContainer width="100%" height={200}>
        <PieChart>
          <Pie
            data={gaugeData}
            cx="50%"
            cy="70%"
            startAngle={180}
            endAngle={0}
            innerRadius={60}
            outerRadius={90}
            dataKey="value"
            stroke="none"
          >
            <Cell fill={getColorByStatus(data.status)} />
            <Cell fill="#e5e7eb" />
          </Pie>
          <text
            x="50%"
            y="65%"
            textAnchor="middle"
            fontSize={24}
            fontWeight="bold"
          >
            {data.delta_normalized.toFixed(3)}
          </text>
          <text x="50%" y="75%" textAnchor="middle" fontSize={14} fill="#666">
            {getStatusLabel(data.status)}
          </text>
        </PieChart>
      </ResponsiveContainer>
      <div className="mt-2 space-y-1 text-sm text-muted-foreground">
        <p>Directional Exposure: {data.directional_exposure_pct.toFixed(2)}%</p>
        <p>Raw Delta: ${data.delta_raw.toLocaleString()}</p>
        <p>Portfolio Value: ${data.portfolio_value.toLocaleString()}</p>
      </div>
    </div>
  )
}
