import { createContext, useContext, type ReactNode } from "react"
import { useChat } from "@/hooks/useChat"
import type { Message, SourceRef, ChatSession } from "@/types/chat"

interface ChatContextValue {
  messages: Message[]
  isStreaming: boolean
  currentSources: SourceRef[]
  sessions: ChatSession[]
  activeSessionId: string | null
  sendMessage: (question: string) => Promise<void>
  newChat: () => void
  loadSession: (sessionId: string) => Promise<void>
  deleteSession: (sessionId: string) => Promise<void>
}

const ChatContext = createContext<ChatContextValue | null>(null)

export function ChatProvider({ children }: { children: ReactNode }) {
  const chat = useChat()
  return (
    <ChatContext.Provider value={chat}>
      {children}
    </ChatContext.Provider>
  )
}

export function useChatContext() {
  const ctx = useContext(ChatContext)
  if (!ctx) {
    throw new Error("useChatContext must be used within ChatProvider")
  }
  return ctx
}
