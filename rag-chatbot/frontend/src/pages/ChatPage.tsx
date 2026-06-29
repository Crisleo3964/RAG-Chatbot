import { useState, useRef, useEffect, useCallback } from "react"
import { motion, AnimatePresence } from "framer-motion"
import { useChatContext } from "@/context/ChatContext"
import { Sidebar } from "@/components/Sidebar"
import { ChatInput } from "@/components/ChatInput"
import { MessageBubble } from "@/components/MessageBubble"
import { SourceCard } from "@/components/SourceCard"
import { LoadingIndicator } from "@/components/LoadingIndicator"
import { UploadModal } from "@/components/UploadModal"
import { SettingsModal } from "@/components/SettingsModal"
import { SourceViewerModal } from "@/components/SourceViewerModal"
import { UserProfileModal } from "@/components/UserProfileModal"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { MessageSquare, BookOpen, PanelRightClose } from "lucide-react"
import type { SourceRef } from "@/types/chat"

export function ChatPage() {
  const {
    messages,
    isStreaming,
    currentSources,
    sessions,
    activeSessionId,
    sendMessage,
    newChat,
    loadSession,
    deleteSession,
  } = useChatContext()
  const [showUpload, setShowUpload] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [showSources, setShowSources] = useState(true)
  const [viewerSource, setViewerSource] = useState<SourceRef | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = useCallback(
    (question: string) => {
      sendMessage(question)
    },
    [sendMessage],
  )

  const hasMessages = messages.length > 0
  const lastAssistantMsg = [...messages]
    .reverse()
    .find((m) => m.role === "assistant" && !m.content.startsWith("Error:"))

  const sourcesToShow = lastAssistantMsg?.sources?.length
    ? lastAssistantMsg.sources
    : currentSources

  return (
    <div className="flex h-screen bg-background">
      <Sidebar
        onNewChat={newChat}
        onUpload={() => setShowUpload(true)}
        onSettings={() => setShowSettings(true)}
        onProfile={() => setShowProfile(true)}
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelectSession={loadSession}
        onDeleteSession={deleteSession}
      />

      <div className="flex flex-1 flex-col min-w-0">
        {hasMessages ? (
          <ScrollArea ref={scrollRef} className="flex-1">
            <div className="mx-auto max-w-3xl py-6">
              <AnimatePresence initial={false}>
                {messages.map((msg) => (
                  <MessageBubble key={msg.id} message={msg} />
                ))}
              </AnimatePresence>
              {isStreaming && <LoadingIndicator />}
            </div>
          </ScrollArea>
        ) : (
          <div className="flex flex-1 items-center justify-center">
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center max-w-md px-4"
            >
              <div className="mb-4 flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-muted">
                  <MessageSquare className="h-8 w-8 text-muted-foreground" />
                </div>
              </div>
              <h2 className="text-lg font-semibold text-foreground mb-2">
                Ask your documents
              </h2>
              <p className="text-sm text-muted-foreground leading-relaxed">
                Upload PDFs and ask questions about their content. The assistant
                will search through your documents and provide answers with
                source citations.
              </p>
              <Button
                variant="outline"
                className="mt-6"
                onClick={() => setShowUpload(true)}
              >
                Upload a document to get started
              </Button>
            </motion.div>
          </div>
        )}

        <ChatInput onSend={handleSend} disabled={isStreaming} />
      </div>

      <AnimatePresence>
        {showSources && sourcesToShow.length > 0 && (
          <motion.aside
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 280, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="border-l border-border bg-surface overflow-hidden hidden lg:block"
          >
            <div className="flex h-14 items-center justify-between border-b border-border px-4 shrink-0">
              <div className="flex items-center gap-2">
                <BookOpen className="h-4 w-4 text-muted-foreground" />
                <span className="text-sm font-medium text-foreground">
                  Sources
                </span>
                <span className="text-xs text-muted-foreground">
                  {sourcesToShow.length}
                </span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowSources(false)}
                className="h-7 w-7"
              >
                <PanelRightClose className="h-4 w-4" />
              </Button>
            </div>
            <ScrollArea className="p-3 space-y-2">
              {sourcesToShow.map((src, i) => (
                <SourceCard
                  key={i}
                  source={src}
                  onClick={() => setViewerSource(src)}
                />
              ))}
            </ScrollArea>
          </motion.aside>
        )}
      </AnimatePresence>

      {!showSources && sourcesToShow.length > 0 && (
        <button
          onClick={() => setShowSources(true)}
          className="fixed right-4 top-4 z-10 flex h-9 items-center gap-2 rounded-lg border border-border bg-surface px-3 text-sm text-muted-foreground hover:text-foreground shadow-sm transition-colors cursor-pointer"
        >
          <BookOpen className="h-4 w-4" />
          Sources ({sourcesToShow.length})
        </button>
      )}

      <UploadModal open={showUpload} onOpenChange={setShowUpload} />
      <SettingsModal open={showSettings} onOpenChange={setShowSettings} />
      <SourceViewerModal
        open={viewerSource !== null}
        onOpenChange={(open) => !open && setViewerSource(null)}
        source={viewerSource}
      />
      <UserProfileModal open={showProfile} onOpenChange={setShowProfile} />
    </div>
  )
}
