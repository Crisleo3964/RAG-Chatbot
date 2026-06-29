import { useState, useCallback, useEffect } from "react"
import type { Message, SourceRef, ChatSession } from "@/types/chat"
import { postChat, getSessions, getSessionMessages, deleteSession } from "@/services/api"
import { useAuth } from "@/hooks/useAuth"

let messageIdCounter = 0

function nextId(): string {
  messageIdCounter += 1
  return `msg-${Date.now()}-${messageIdCounter}`
}

function toMessage(m: { message_id: string; role: string; content: string; sources?: SourceRef[]; created_at: string }): Message {
  return {
    id: m.message_id,
    role: m.role as "user" | "assistant",
    content: m.content,
    sources: m.sources,
    timestamp: new Date(m.created_at),
  }
}

export function useChat() {
  const { isAuthenticated } = useAuth()
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)
  const [currentSources, setCurrentSources] = useState<SourceRef[]>([])
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)

  const loadSessions = useCallback(async () => {
    try {
      const list = await getSessions()
      setSessions(list)
    } catch {
      console.warn("Failed to load sessions")
    }
  }, [])

  useEffect(() => {
    if (isAuthenticated) {
      loadSessions()
    }
  }, [isAuthenticated, loadSessions])

  const loadSession = useCallback(async (sessionId: string) => {
    try {
      const history = await getSessionMessages(sessionId)
      setMessages(history.map(toMessage))
      setActiveSessionId(sessionId)
      setCurrentSources([])
    } catch {
      console.error("Failed to load session messages")
    }
  }, [])

  const handleDeleteSession = useCallback(async (sessionId: string) => {
    try {
      await deleteSession(sessionId)
      setSessions((prev) => prev.filter((s) => s.session_id !== sessionId))
      if (activeSessionId === sessionId) {
        setMessages([])
        setActiveSessionId(null)
        setCurrentSources([])
      }
    } catch {
      console.error("Failed to delete session")
    }
  }, [activeSessionId])

  const newChat = useCallback(() => {
    setMessages([])
    setActiveSessionId(null)
    setCurrentSources([])
  }, [])

  const sendMessage = useCallback(async (question: string) => {
    const userMsg: Message = {
      id: nextId(),
      role: "user",
      content: question,
      timestamp: new Date(),
    }

    setMessages((prev) => [...prev, userMsg])
    setIsStreaming(true)

    try {
      const response = await postChat({ question, session_id: activeSessionId || undefined })
      const sources = response.sources || []

      const assistantMsg: Message = {
        id: nextId(),
        role: "assistant",
        content: response.answer,
        sources,
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, assistantMsg])
      setCurrentSources(sources)

      if (response.session_id) {
        setActiveSessionId(response.session_id)
        loadSessions()
      }
    } catch (error: unknown) {
      let errorMessage = "An unexpected error occurred"
      if (error && typeof error === "object" && "response" in error) {
        const axiosErr = error as { response?: { data?: { detail?: string } } }
        errorMessage = axiosErr.response?.data?.detail || errorMessage
      } else if (error instanceof Error) {
        errorMessage = error.message
      }
      const errorMsg: Message = {
        id: nextId(),
        role: "assistant",
        content: errorMessage,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, errorMsg])
    } finally {
      setIsStreaming(false)
    }
  }, [activeSessionId, loadSessions])

  return {
    messages,
    isStreaming,
    currentSources,
    sessions,
    activeSessionId,
    sendMessage,
    newChat,
    loadSession,
    deleteSession: handleDeleteSession,
  }
}
