import type { SourceRef } from "@/types/chat"
import { FileText, ChevronRight } from "lucide-react"

interface SourceCardProps {
  source: SourceRef
  onClick: () => void
}

export function SourceCard({ source, onClick }: SourceCardProps) {
  return (
    <button
      onClick={onClick}
      className="group flex w-full items-center gap-3 rounded-lg border border-border bg-surface px-3 py-2.5 text-left transition-all duration-150 hover:bg-accent hover:border-foreground/20 active:scale-[0.98] cursor-pointer"
    >
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-muted">
        <FileText className="h-4 w-4 text-muted-foreground" />
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-foreground truncate">
          {source.document}
        </p>
        <p className="text-xs text-muted-foreground">
          Page {source.page}
        </p>
      </div>
      <ChevronRight className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
    </button>
  )
}
