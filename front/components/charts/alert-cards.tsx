"use client"

import type { AlertDashboardData } from "@/lib/types"
import { AlertTriangle, TrendingUp, Shield, RefreshCw } from "lucide-react"

export function AlertCards({ data }: { data: AlertDashboardData }) {
  const getHealthColor = (score: number) => {
    if (score >= 80) return "bg-green-100 text-green-800 border-green-200"
    if (score >= 60) return "bg-yellow-100 text-yellow-800 border-yellow-200"
    return "bg-red-100 text-red-800 border-red-200"
  }

  const getLiquidationColor = (risk: string) => {
    if (risk === "low") return "text-green-600"
    if (risk === "moderate") return "text-yellow-600"
    return "text-red-600"
  }

  const getRebalancingColor = (urgency: string) => {
    if (urgency === "none") return "text-green-600"
    if (urgency === "medium") return "text-yellow-600"
    return "text-red-600"
  }

  const formatComponentName = (name: string) => {
    return name
      .split("_")
      .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
      .join(" ")
  }

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {/* Health Score Card */}
      <div
        className={`rounded-xl border p-6 ${getHealthColor(data.health_score)}`}
      >
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold">Health Score</h4>
          <Shield className="h-5 w-5" />
        </div>
        <div className="mt-2 text-3xl font-bold">
          {data.health_score}/100
        </div>
        <div className="mt-4 space-y-1 text-xs">
          {Object.entries(data.health_components).map(([key, val]) => (
            <div key={key} className="flex justify-between">
              <span>{formatComponentName(key)}</span>
              <span className="font-semibold">
                {val.score}/25 ({val.status})
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Liquidation Risk Card */}
      <div className="rounded-xl border bg-card p-6">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-white">Liquidation Risk</h4>
          <AlertTriangle className="h-5 w-5" />
        </div>
        <div
          className={`mt-2 text-2xl font-bold ${getLiquidationColor(data.liquidation_risk.overall_risk)}`}
        >
          {data.liquidation_risk.overall_risk.toUpperCase()}
        </div>
        <div className="mt-4 space-y-2 text-xs text-muted-foreground">
          <p>
            {data.liquidation_risk.positions.length} position(s) monitored
          </p>
          {data.liquidation_risk.positions.slice(0, 2).map((pos, idx) => (
            <div key={idx} className="border-t pt-1">
              <p className="font-semibold">
                {pos.asset} {pos.position_type}
              </p>
              <p>Distance: {pos.price_distance_pct.toFixed(1)}%</p>
            </div>
          ))}
        </div>
      </div>

      {/* Rebalancing Card */}
      <div className="rounded-xl border bg-card p-6">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-white">Rebalancing</h4>
          <RefreshCw className="h-5 w-5" />
        </div>
        <div
          className={`mt-2 text-2xl font-bold ${getRebalancingColor(data.rebalancing_signal.urgency)}`}
        >
          {data.rebalancing_signal.needed ? "NEEDED" : "OK"}
        </div>
        <div className="mt-4 space-y-1 text-xs text-muted-foreground">
          <p>Urgency: {data.rebalancing_signal.urgency.toUpperCase()}</p>
          <p>
            Delta: {data.rebalancing_signal.current_delta.toFixed(2)}
          </p>
          <p>
            Normalized: {data.rebalancing_signal.delta_normalized.toFixed(3)}
          </p>
        </div>
      </div>

      {/* Performance Metrics Placeholder */}
      <div className="rounded-xl border bg-card p-6">
        <div className="flex items-center justify-between">
          <h4 className="text-sm font-semibold text-white">Performance</h4>
          <TrendingUp className="h-5 w-5" />
        </div>
        <div className="mt-2 text-2xl font-bold text-muted-foreground">
          --
        </div>
        <div className="mt-4 text-xs text-muted-foreground">
          <p>Additional metrics</p>
          <p className="mt-2">Coming soon</p>
        </div>
      </div>
    </div>
  )
}
