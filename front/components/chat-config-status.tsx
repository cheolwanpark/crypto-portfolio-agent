"use client"

import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import type { InvestmentStrategy } from "@/lib/types"

interface ChatConfigStatusProps {
  strategy: InvestmentStrategy
  targetApy: number
  maxDrawdown: number
  viewMode?: "chat" | "board"
  onViewModeChange?: (mode: "chat" | "board") => void
  // Board-specific props
  portfolioVersions?: Array<{ version: number }>
  selectedVersion?: string
  onVersionChange?: (version: string) => void
}

function getStrategyColor(strategy: InvestmentStrategy): string {
  switch (strategy) {
    case "Passive":
      return "bg-blue-500/10 text-blue-700 dark:text-blue-300 border-blue-500/20"
    case "Conservative":
      return "bg-green-500/10 text-green-700 dark:text-green-300 border-green-500/20"
    case "Aggressive":
      return "bg-red-500/10 text-red-700 dark:text-red-300 border-red-500/20"
    default:
      return "bg-gray-500/10 text-gray-700 dark:text-gray-300 border-gray-500/20"
  }
}

export function ChatConfigStatus({
  strategy,
  targetApy,
  maxDrawdown,
  viewMode,
  onViewModeChange,
  portfolioVersions,
  selectedVersion,
  onVersionChange,
}: ChatConfigStatusProps) {
  return (
    <div className="border-b border-border bg-card px-6 py-2.5">
      <div className="flex items-center justify-between gap-4 text-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Strategy:</span>
            <Badge variant="outline" className={getStrategyColor(strategy)}>
              {strategy}
            </Badge>
          </div>
          <Separator orientation="vertical" className="h-4" />
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Target APY:</span>
            <span className="font-medium text-foreground">{targetApy}%</span>
          </div>
          <Separator orientation="vertical" className="h-4" />
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Max Drawdown:</span>
            <span className="font-medium text-foreground">{maxDrawdown}%</span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Version Dropdown - only show in board mode */}
          {viewMode === "board" && portfolioVersions && selectedVersion && onVersionChange && (
            <>
              <Select value={selectedVersion} onValueChange={onVersionChange}>
                <SelectTrigger className="h-7 w-[140px] text-xs text-white">
                  <SelectValue placeholder="Latest version" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="latest">Latest</SelectItem>
                  {portfolioVersions.map((v) => (
                    <SelectItem key={v.version} value={String(v.version)}>
                      Version {v.version}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <Separator orientation="vertical" className="h-4" />
            </>
          )}

          {/* View Mode Toggle - only show if props are provided */}
          {viewMode && onViewModeChange && (
            <div className="flex gap-1 rounded-lg bg-muted p-0.5">
              <Button
                variant={viewMode === "chat" ? "default" : "ghost"}
                size="sm"
                onClick={() => onViewModeChange("chat")}
                className="h-7 rounded-md px-3 text-xs"
              >
                Chat
              </Button>
              <Button
                variant={viewMode === "board" ? "default" : "ghost"}
                size="sm"
                onClick={() => onViewModeChange("board")}
                className="h-7 rounded-md px-3 text-xs"
              >
                Board
              </Button>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
