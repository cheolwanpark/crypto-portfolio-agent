"use client"

import { useChatDetail } from "@/hooks/use-chat-detail"
import { useGraph } from "@/hooks/use-graph"
import { ScrollArea } from "@/components/ui/scroll-area"
import { ChatConfigStatus } from "@/components/chat-config-status"
import { SensitivityChart } from "@/components/charts/sensitivity-chart"
import { DeltaGauge } from "@/components/charts/delta-gauge"
import { RiskPieChart } from "@/components/charts/risk-pie-chart"
import { AlertCards } from "@/components/charts/alert-cards"
import { Loader2 } from "lucide-react"

interface BoardProps {
  chatId: string
  version?: number
  viewMode?: "chat" | "board"
  onViewModeChange?: (mode: "chat" | "board") => void
  selectedVersion?: string
  onVersionChange?: (version: string) => void
}

export function Board({ chatId, version, viewMode, onViewModeChange, selectedVersion, onVersionChange }: BoardProps) {
  const { chat, isLoading: chatLoading } = useChatDetail(chatId)

  // Get positions for specific version or latest
  const positions =
    version !== undefined
      ? chat?.portfolio_versions.find((v) => v.version === version)?.positions
      : chat?.portfolio

  // Fetch graph data
  const {
    data: graphData,
    isLoading: graphLoading,
    error,
  } = useGraph(positions, {
    graphTypes: ["sensitivity", "delta", "risk_contribution", "alerts"],
    lookbackDays: 30,
  })

  if (chatLoading || graphLoading) {
    return (
      <div className="flex h-full items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center">
        <div className="text-center">
          <p className="text-lg font-semibold text-destructive">
            Error loading graph data
          </p>
          <p className="mt-2 text-sm text-muted-foreground">{error.message}</p>
        </div>
      </div>
    )
  }

  if (!positions || positions.length === 0) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">No portfolio data available</p>
      </div>
    )
  }

  if (!graphData) {
    return (
      <div className="flex h-full items-center justify-center">
        <p className="text-muted-foreground">No graph data available</p>
      </div>
    )
  }

  return (
    <div className="flex h-full flex-col">
      {/* Configuration Status Bar */}
      {chat && (
        <ChatConfigStatus
          strategy={chat.strategy}
          targetApy={chat.target_apy}
          maxDrawdown={chat.max_drawdown}
          viewMode={viewMode}
          onViewModeChange={onViewModeChange}
          portfolioVersions={chat.portfolio_versions}
          selectedVersion={selectedVersion}
          onVersionChange={onVersionChange}
        />
      )}

      {/* Board Content */}
      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="space-y-6 p-6">
            {/* Header Info */}
            <div className="flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-white">
                Portfolio Risk Dashboard
                {version !== undefined && ` - Version ${version}`}
              </h2>
              <div className="text-sm text-muted-foreground">
                {positions.length} position(s) | Updated:{" "}
                {new Date(graphData.metadata.timestamp).toLocaleString()}
              </div>
            </div>

            {/* Grid Layout */}
            <div className="grid gap-6 lg:grid-cols-2">
              {/* Full width sensitivity chart */}
              <div className="lg:col-span-2">
                {graphData.sensitivity && (
                  <SensitivityChart data={graphData.sensitivity} />
                )}
              </div>

              {/* Delta gauge and risk pie side by side */}
              {graphData.delta && <DeltaGauge data={graphData.delta} />}
              {graphData.risk_contribution && (
                <RiskPieChart data={graphData.risk_contribution} />
              )}

              {/* Full width alert cards */}
              <div className="lg:col-span-2">
                {graphData.alerts && <AlertCards data={graphData.alerts} />}
              </div>
            </div>
          </div>
        </ScrollArea>
      </div>
    </div>
  )
}
