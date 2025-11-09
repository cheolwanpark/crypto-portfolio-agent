"use client"

import { useState, useEffect, useCallback, useRef } from "react"
import { fetchGraph } from "@/lib/api-client"
import type { Position, GraphType, GraphResponse } from "@/lib/types"

export interface UseGraphOptions {
  graphTypes?: GraphType[]
  lookbackDays?: number
  enabled?: boolean // Allow disabling auto-fetch
}

export interface UseGraphReturn {
  data: GraphResponse | null
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<void>
}

/**
 * Hook to fetch graph visualization data for a portfolio
 *
 * Automatically fetches when positions change (unless enabled=false)
 *
 * @param positions - Portfolio positions to analyze
 * @param options - Configuration options
 * @returns Graph data, loading state, error, and refetch function
 *
 * @example
 * ```tsx
 * const { data, isLoading, error } = useGraph(portfolio?.positions, {
 *   graphTypes: ["sensitivity", "delta", "alerts"],
 *   lookbackDays: 30
 * })
 * ```
 */
export function useGraph(
  positions: Position[] | null | undefined,
  options: UseGraphOptions = {},
): UseGraphReturn {
  const {
    graphTypes = ["sensitivity", "delta", "risk_contribution", "alerts"],
    lookbackDays = 30,
    enabled = true,
  } = options

  const [data, setData] = useState<GraphResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  // Use ref to track if we've already fetched for current positions
  const lastFetchedPositionsRef = useRef<string | null>(null)

  // Create a stable string representation of positions for comparison
  const positionsKey = positions
    ? JSON.stringify(
        positions.map((p) => ({
          asset: p.asset,
          quantity: p.quantity,
          type: p.position_type,
        }))
      )
    : null

  const fetch = useCallback(async () => {
    // Don't fetch if no positions or disabled
    if (!positions || positions.length === 0 || !enabled) {
      setData(null)
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const result = await fetchGraph(positions, graphTypes, lookbackDays)
      setData(result)
    } catch (err) {
      const errorObj =
        err instanceof Error ? err : new Error("Failed to fetch graph data")
      setError(errorObj)
      console.error("Graph fetch error:", errorObj)
    } finally {
      setIsLoading(false)
    }
  }, [positions, graphTypes, lookbackDays, enabled])

  // Auto-fetch only when positions key changes (not on every render)
  useEffect(() => {
    if (positionsKey !== lastFetchedPositionsRef.current) {
      lastFetchedPositionsRef.current = positionsKey
      fetch()
    }
  }, [positionsKey, fetch])

  return {
    data,
    isLoading,
    error,
    refetch: fetch,
  }
}

/**
 * Lazy version of useGraph - only fetches when manually triggered
 * Useful for on-demand graph generation (e.g., when user clicks a button)
 */
export interface UseGraphLazyReturn {
  data: GraphResponse | null
  isLoading: boolean
  error: Error | null
  fetch: (
    positions: Position[],
    graphTypes?: GraphType[],
    lookbackDays?: number,
  ) => Promise<GraphResponse | null>
  reset: () => void
}

export function useGraphLazy(): UseGraphLazyReturn {
  const [data, setData] = useState<GraphResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)

  const fetch = useCallback(
    async (
      positions: Position[],
      graphTypes: GraphType[] = [
        "sensitivity",
        "delta",
        "risk_contribution",
        "alerts",
      ],
      lookbackDays: number = 30,
    ): Promise<GraphResponse | null> => {
      if (!positions || positions.length === 0) {
        setData(null)
        return null
      }

      setIsLoading(true)
      setError(null)

      try {
        const result = await fetchGraph(positions, graphTypes, lookbackDays)
        setData(result)
        return result
      } catch (err) {
        const errorObj =
          err instanceof Error ? err : new Error("Failed to fetch graph data")
        setError(errorObj)
        console.error("Graph fetch error:", errorObj)
        return null
      } finally {
        setIsLoading(false)
      }
    },
    [],
  )

  const reset = useCallback(() => {
    setData(null)
    setError(null)
    setIsLoading(false)
  }, [])

  return {
    data,
    isLoading,
    error,
    fetch,
    reset,
  }
}
