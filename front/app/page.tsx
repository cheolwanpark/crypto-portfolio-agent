"use client"

import { useState } from "react"
import { Sidebar } from "@/components/sidebar"
import { Chat } from "@/components/chat"
import { Board } from "@/components/board"
import { NewChatModal } from "@/components/new-chat-modal"
import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { useChatList } from "@/hooks/use-chat-list"
import { useChatDetail } from "@/hooks/use-chat-detail"
import { useCreateChat } from "@/hooks/use-create-chat"
import { useToast } from "@/hooks/use-toast"
import { Toaster } from "@/components/ui/toaster"
import type { CreateChatParams } from "@/lib/types"

export default function Home() {
  const [selectedChatId, setSelectedChatId] = useState<string | null>(null)
  const [isNewChatModalOpen, setIsNewChatModalOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [viewMode, setViewMode] = useState<"chat" | "board">("chat")
  const [selectedVersion, setSelectedVersion] = useState<string>("latest")

  const { chats, isLoading: isLoadingChats, updateChatInList, refetch } = useChatList()
  const { chat } = useChatDetail(selectedChatId)
  const { create, isCreating } = useCreateChat()
  const { toast } = useToast()

  const handleCreateChat = async (params: CreateChatParams) => {
    const newChat = await create(params)

    if (newChat) {
      toast({
        title: "Chat created",
        description: "Your new chat has been created successfully",
      })
      setIsNewChatModalOpen(false)

      // Refresh chat list first to ensure the new chat is in the list
      await refetch()

      // Then select the chat - this ensures polling starts immediately
      setSelectedChatId(newChat.id)
    } else {
      toast({
        title: "Error",
        description: "Failed to create chat. Please try again.",
        variant: "destructive",
      })
    }
  }

  return (
    <div className="dark flex h-screen bg-background">
      {/* Sidebar */}
      <Sidebar
        chats={chats}
        selectedChatId={selectedChatId}
        onSelectChat={setSelectedChatId}
        onNewChat={() => setIsNewChatModalOpen(true)}
        isLoading={isLoadingChats}
        isCollapsed={isSidebarCollapsed}
        onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
      />

      {/* Main Content */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {selectedChatId ? (
          viewMode === "chat" ? (
            <Chat
              chatId={selectedChatId}
              onChatUpdate={updateChatInList}
              viewMode={viewMode}
              onViewModeChange={setViewMode}
            />
          ) : (
            <Board
              chatId={selectedChatId}
              version={
                selectedVersion === "latest"
                  ? undefined
                  : Number(selectedVersion)
              }
              viewMode={viewMode}
              onViewModeChange={setViewMode}
              selectedVersion={selectedVersion}
              onVersionChange={setSelectedVersion}
            />
          )
        ) : (
          <Chat chatId={null} onChatUpdate={updateChatInList} />
        )}
      </div>

      {/* New Chat Modal */}
      <NewChatModal
        open={isNewChatModalOpen}
        onOpenChange={setIsNewChatModalOpen}
        onCreate={handleCreateChat}
        isCreating={isCreating}
      />

      {/* Toast Notifications */}
      <Toaster />
    </div>
  )
}
