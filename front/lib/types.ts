// Type definitions for the crypto portfolio agent API
// Based on agent/API.md

// ============================================================================
// Chat List Types
// ============================================================================

export type ChatStatus = "queued" | "processing" | "completed" | "failed" | "timeout"
export type InvestmentStrategy = "Passive" | "Conservative" | "Aggressive"

export interface ChatListItem {
  id: string
  status: ChatStatus
  strategy: InvestmentStrategy
  target_apy: number
  max_drawdown: number
  title?: string
  has_portfolio: boolean
  message_count: number
  created_at: string
  updated_at: string
}

// ============================================================================
// Message Types
// ============================================================================

export interface Reasoning {
  summary: string
  detail: string
  timestamp: string
}

export interface ToolCall {
  tool_name: string
  message: string
  timestamp: string
  inputs: Record<string, any>
  outputs: Record<string, any>
  status: "success" | "error"
}

export type MessageType = "user" | "agent" | "system"

export interface BaseMessage {
  type: MessageType
  message: string
  timestamp: string
  reasonings: Reasoning[]
  toolcalls: ToolCall[]
}

// ============================================================================
// Portfolio Types
// ============================================================================

export type PositionType = "spot" | "futures" | "lending_supply" | "lending_borrow"
export type BorrowType = "variable" | "stable" | null

export interface Position {
  asset: string
  quantity: number
  position_type: PositionType
  entry_price: number
  leverage: number
  entry_timestamp: string | null
  entry_index: number | null
  borrow_type: BorrowType
}

export interface PortfolioVersion {
  version: number
  positions: Position[]
  explanation: string
  timestamp: string
}

// ============================================================================
// Chat Detail Types
// ============================================================================

export interface ChatDetail {
  id: string
  status: ChatStatus
  strategy: InvestmentStrategy
  target_apy: number
  max_drawdown: number
  title?: string
  messages: BaseMessage[]
  portfolio: Position[] | null
  portfolio_versions: PortfolioVersion[]
  error_message: string | null
  created_at: string
  updated_at: string
}

// ============================================================================
// Portfolio Response Type
// ============================================================================

export interface PortfolioResponse {
  chat_id: string
  portfolio_versions: PortfolioVersion[]
  latest_portfolio: Position[]
  has_portfolio: boolean
}

// ============================================================================
// Create Chat Types
// ============================================================================

export interface CreateChatParams {
  strategy: InvestmentStrategy
  target_apy: number
  max_drawdown: number
  initial_message: string
  title: string
}

// ============================================================================
// UI State Types
// ============================================================================

export interface ChatState {
  selectedChatId: string | null
  isNewChatModalOpen: boolean
}

export interface LoadingState {
  isLoading: boolean
  error: Error | null
}

// ============================================================================
// Validation Helpers
// ============================================================================

/**
 * Clamp APY value to valid range (0-200%)
 */
export function clampAPY(value: number): number {
  return Math.max(0, Math.min(200, value))
}

/**
 * Clamp max drawdown value to valid range (0-100%)
 */
export function clampDrawdown(value: number): number {
  return Math.max(0, Math.min(100, value))
}

// ============================================================================
// Graph Visualization Types
// ============================================================================

export interface SensitivityDataPoint {
  x: number
  y: number
  return_pct: number
  pnl: number
}

export interface SensitivityGraphData {
  data_points: SensitivityDataPoint[]
  current_position: number
  value_range: {
    min: number
    max: number
    current: number
  }
}

export interface DeltaGaugeData {
  delta_raw: number
  delta_normalized: number
  status: "neutral" | "slight_long" | "slight_short" | "high_long" | "high_short"
  portfolio_value: number
  directional_exposure_pct: number
}

export interface RiskContribution {
  asset: string
  risk_pct: number
  value_pct: number
  risk_value: number
  position_value: number
}

export interface RiskContributionData {
  contributions: RiskContribution[]
  total_risk: number
  diversification_benefit: number
}

export interface HealthComponent {
  score: number
  status: "excellent" | "good" | "fair" | "warning" | "poor"
}

export interface LiquidationRisk {
  asset: string
  position_type: string
  liquidation_price: number
  current_price: number
  price_distance_pct: number
  risk_level: "safe" | "moderate" | "high"
}

export interface AlertDashboardData {
  health_score: number
  health_components: {
    delta_neutral: HealthComponent
    volatility: HealthComponent
    sharpe_ratio: HealthComponent
    leverage: HealthComponent
  }
  liquidation_risk: {
    overall_risk: "low" | "moderate" | "high"
    positions: LiquidationRisk[]
  }
  rebalancing_signal: {
    needed: boolean
    urgency: "none" | "medium" | "high"
    current_delta: number
    delta_normalized: number
  }
}

export interface GraphResponse {
  sensitivity: SensitivityGraphData | null
  delta: DeltaGaugeData | null
  risk_contribution: RiskContributionData | null
  alerts: AlertDashboardData | null
  funding_waterfall: Record<string, any> | null
  rolling_metrics: Record<string, any> | null
  monte_carlo: Record<string, any> | null
  metadata: {
    lookback_days_used: number
    graph_types_generated: string[]
    timestamp: string
  }
}

export type GraphType =
  | "sensitivity"
  | "delta"
  | "risk_contribution"
  | "alerts"
  | "funding_waterfall"
  | "rolling_metrics"
  | "monte_carlo"
