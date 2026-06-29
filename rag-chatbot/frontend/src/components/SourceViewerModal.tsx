import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog"
import type { SourceRef } from "@/types/chat"
import { FileText } from "lucide-react"

interface SourceViewerModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  source: SourceRef | null
}

export function SourceViewerModal({ open, onOpenChange, source }: SourceViewerModalProps) {
  if (!source) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogClose onClick={() => onOpenChange(false)} />
        <DialogHeader>
          <DialogTitle>Source Details</DialogTitle>
          <DialogDescription>
            Retrieved document chunk information.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="flex items-center gap-3 rounded-lg border border-border p-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
              <FileText className="h-5 w-5 text-muted-foreground" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">
                {source.document}
              </p>
              <p className="text-xs text-muted-foreground">
                Page {source.page}
              </p>
            </div>
          </div>

          <div className="rounded-lg border border-border bg-muted/50 p-4">
            <p className="text-xs text-muted-foreground mb-2 font-medium uppercase tracking-wider">
              Retrieved Content
            </p>
            <p className="text-sm text-foreground leading-relaxed">
              Source content from {source.document}, page {source.page}. The
              full text chunk will be displayed here with future backend support.
            </p>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
