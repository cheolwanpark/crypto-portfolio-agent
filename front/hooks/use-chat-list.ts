"use client"

import { useState, useEffect, useCallback } from "react"
import { fetchChats } from "@/lib/api-client"
import { parseUTCDate } from "@/lib/date-utils"
import type { ChatListItem } from "@/lib/types"

export interface UseChatListReturn {
  chats: ChatListItem[]
  isLoading: boolean
  error: Error | null
  refetch: () => Promise<void>
  updateChatInList: (chatId: string, updates: Partial<ChatListItem>) => void
}

/**
 * Hook to fetch the chat list
 * No polling - updates are done via individual chat detail polling
 */
export function useChatList(): UseChatListReturn {
  const [chats, setChats] = useState<ChatListItem[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  const fetchChatList = useCallback(async () => {
    try {
      const data = await fetchChats()
      // Transform UTC timestamps to Date objects
      const transformedChats = data.map((chat) => ({
        ...chat,
        created_at: parseUTCDate(chat.created_at) as any,
        updated_at: parseUTCDate(chat.updated_at) as any,
      }))
      setChats(transformedChats)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err : new Error("Failed to fetch chats"))
    } finally {
      setIsLoading(false)
    }
  }, [])

  const updateChatInList = useCallback(
    (chatId: string, updates: Partial<ChatListItem>) => {
      setChats((prevChats) =>
        prevChats.map((chat) =>
          chat.id === chatId ? { ...chat, ...updates } : chat,
        ),
      )
    },
    [],
  )

  // Initial fetch only
  useEffect(() => {
    fetchChatList()
  }, [fetchChatList])

  return {
    chats,
    isLoading,
    error,
    refetch: fetchChatList,
    updateChatInList,
  }
}
