// API client for communicating with the crypto portfolio agent backend
import type {
  ChatListItem,
  ChatDetail,
  PortfolioResponse,
  CreateChatParams,
  Position,
  GraphType,
  GraphResponse,
} from "./types"

// Get Agent API URL from environment variable, default to localhost:8001
const getApiUrl = () => {
  if (typeof window === "undefined") {
    // Server-side: use environment variable or default
    return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
  }
  // Client-side: use environment variable or default
  return process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001"
}

// Get Data API URL from environment variable, default to localhost:8000
const getDataApiUrl = () => {
  if (typeof window === "undefined") {
    // Server-side: use environment variable or default
    return process.env.NEXT_PUBLIC_DATA_API_URL || "http://localhost:8000"
  }
  // Client-side: use environment variable or default
  return process.env.NEXT_PUBLIC_DATA_API_URL || "http://localhost:8000"
}

// ============================================================================
// Error Handling
// ============================================================================

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
    message: string,
  ) {
    super(message)
    this.name = "ApiError"
  }
}

async function handleResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const errorText = await response.text()
    throw new ApiError(
      response.status,
      response.statusText,
      errorText || `Request failed with status ${response.status}`,
    )
  }

  try {
    return await response.json()
  } catch (error) {
    throw new Error("Failed to parse JSON response")
  }
}

// ============================================================================
// API Functions
// ============================================================================

/**
 * Fetch all chat sessions
 * GET /chat
 */
export async function fetchChats(): Promise<ChatListItem[]> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })

  return handleResponse<ChatListItem[]>(response)
}

/**
 * Fetch detailed information about a specific chat session
 * GET /chat/{id}
 */
export async function fetchChatDetail(id: string): Promise<ChatDetail> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat/${id}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })

  return handleResponse<ChatDetail>(response)
}

/**
 * Fetch portfolio information for a specific chat session
 * GET /chat/{id}/portfolio
 */
export async function fetchChatPortfolio(
  id: string,
): Promise<PortfolioResponse> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat/${id}/portfolio`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })

  return handleResponse<PortfolioResponse>(response)
}

/**
 * Create a new chat session
 * POST /chat
 */
export async function createChat(
  params: CreateChatParams,
): Promise<ChatDetail> {
  const apiUrl = getApiUrl()
  const response = await fetch(`${apiUrl}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      user_prompt: params.initial_message,
      strategy: params.strategy,
      target_apy: params.target_apy,
      max_drawdown: params.max_drawdown,
      title: params.title,
    }),
  })

  return handleResponse<ChatDetail>(response)
}

/**
 * Send a followup message to an existing chat session
 * POST /chat/{id}/followup
 */
export async function sendFollowup(
  chatId: string,
  prompt: string,
  config?: {
    strategy?: "Passive" | "Conservative" | "Aggressive"
    target_apy?: number
    max_drawdown?: number
  },
): Promise<ChatDetail> {
  const apiUrl = getApiUrl()
  const body: Record<string, unknown> = { prompt }

  // Add optional configuration parameters if provided
  if (config?.strategy) body.strategy = config.strategy
  if (config?.target_apy !== undefined) body.target_apy = config.target_apy
  if (config?.max_drawdown !== undefined) body.max_drawdown = config.max_drawdown

  const response = await fetch(`${apiUrl}/chat/${chatId}/followup`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  })

  return handleResponse<ChatDetail>(response)
}

/**
 * @deprecated Use sendFollowup instead
 * Legacy function for backward compatibility
 */
export async function sendMessage(
  chatId: string,
  message: string,
): Promise<ChatDetail> {
  return sendFollowup(chatId, message)
}

/**
 * Fetch graph visualization data for a portfolio
 * POST /api/v1/analysis/graph
 *
 * @param positions - Array of position objects from portfolio
 * @param graphTypes - Types of graphs to generate (default: all Phase 1 graphs)
 * @param lookbackDays - Number of days to look back for historical data (default: 30)
 */
export async function fetchGraph(
  positions: Position[],
  graphTypes: GraphType[] = ["sensitivity", "delta", "risk_contribution", "alerts"],
  lookbackDays: number = 30,
): Promise<GraphResponse> {
  const apiUrl = getDataApiUrl() // Use data API (port 8000) for graph endpoint

  // Convert Position objects to the format expected by backend
  const backendPositions = positions.map((pos) => ({
    asset: pos.asset,
    quantity: pos.quantity,
    position_type: pos.position_type,
    entry_price: pos.entry_price,
    leverage: pos.leverage,
    ...(pos.entry_timestamp && { entry_timestamp: pos.entry_timestamp }),
    ...(pos.entry_index && { entry_index: pos.entry_index }),
    ...(pos.borrow_type && { borrow_type: pos.borrow_type }),
  }))

  const response = await fetch(`${apiUrl}/api/v1/analysis/graph`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      positions: backendPositions,
      lookback_days: lookbackDays,
      graph_types: graphTypes,
    }),
  })

  return handleResponse<GraphResponse>(response)
}
