import { motion } from "framer-motion"
import type { Message } from "@/types/chat"
import { cn } from "@/lib/utils"
import { User, Bot } from "lucide-react"

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user"
  const isError = !isUser && message.content.startsWith("Error:")

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2 }}
      className={cn("flex items-start gap-3 px-4 py-3", isUser && "flex-row-reverse")}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-secondary text-foreground",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className={cn("max-w-[75%] space-y-2", isUser && "text-right")}>
        <div
          className={cn(
            "inline-block rounded-2xl px-4 py-2.5 text-sm leading-relaxed",
            isUser
              ? "bg-primary text-primary-foreground"
              : isError
                ? "bg-destructive/10 text-destructive border border-destructive/20"
                : "bg-secondary text-foreground",
          )}
        >
          {message.content}
        </div>
        {message.sources && message.sources.length > 0 && (
          <div className="flex flex-wrap gap-1.5 justify-start">
            {message.sources.map((src, i) => (
              <span
                key={i}
                className="inline-flex items-center rounded-full border bg-surface px-2 py-0.5 text-xs text-muted-foreground"
              >
                {src.document} · p.{src.page}
              </span>
            ))}
          </div>
        )}
      </div>
    </motion.div>
  )
}
