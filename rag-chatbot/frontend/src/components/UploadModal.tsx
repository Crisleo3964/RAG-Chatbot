import { useState, useCallback, useRef, useEffect } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog"
import { Button } from "@/components/ui/button"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import { uploadDocument, getDocumentStatus } from "@/services/api"
import { Upload, FileText, CheckCircle2, Loader2, X, AlertCircle, Clock } from "lucide-react"
import { cn } from "@/lib/utils"

interface UploadModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
}

interface FileStatus {
  file: File
  documentId?: string
  status: "pending" | "uploading" | "processing" | "completed" | "failed"
  message?: string
  pollCtrl?: AbortController
}

export function UploadModal({ open, onOpenChange }: UploadModalProps) {
  const [files, setFiles] = useState<FileStatus[]>([])
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const addFiles = useCallback((newFiles: FileList | File[]) => {
    const pdfs = Array.from(newFiles).filter(
      (f) => f.type === "application/pdf" || f.name.endsWith(".pdf"),
    )
    setFiles((prev) => [
      ...prev,
      ...pdfs.map((f) => ({ file: f, status: "pending" as const })),
    ])
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files)
      }
    },
    [addFiles],
  )

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(true)
  }, [])

  const handleDragLeave = useCallback(() => setDragOver(false), [])

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }, [])

  const pollStatus = useCallback((index: number, documentId: string) => {
    const ctrl = new AbortController()
    let active = true

    const poll = async () => {
      while (active) {
        try {
          const res = await getDocumentStatus(documentId)
          if (!active || ctrl.signal.aborted) break
          setFiles((prev) =>
            prev.map((f, idx) =>
              idx === index
                ? {
                    ...f,
                    status: res.status === "PENDING" ? "processing" as const
                         : res.status === "PROCESSING" ? "processing" as const
                         : res.status === "COMPLETED" ? "completed" as const
                         : "failed" as const,
                    message: res.status === "COMPLETED"
                      ? `${res.chunks_created} chunks created`
                      : res.status === "FAILED"
                        ? res.error || "Processing failed"
                        : undefined,
                  }
                : f,
            ),
          )
          if (res.status === "COMPLETED" || res.status === "FAILED") break
        } catch {
          if (!active) break
        }
        await new Promise((r) => setTimeout(r, 2000))
      }
    }

    poll()
    return ctrl
  }, [])

  const uploadAll = useCallback(async () => {
    for (let i = 0; i < files.length; i++) {
      const entry = files[i]
      if (entry.status !== "pending") continue

      setFiles((prev) =>
        prev.map((f, idx) => (idx === i ? { ...f, status: "uploading" } : f)),
      )

      try {
        const res = await uploadDocument(entry.file)
        const ctrl = pollStatus(i, res.document_id)
        pollCtrlsRef.current.push(ctrl)
        setFiles((prev) =>
          prev.map((f, idx) =>
            idx === i
              ? { ...f, documentId: res.document_id, status: "processing", message: res.status, pollCtrl: ctrl }
              : f,
          ),
        )
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "Upload failed"
        setFiles((prev) =>
          prev.map((f, idx) => (idx === i ? { ...f, status: "failed", message: msg } : f)),
        )
      }
    }
  }, [files, pollStatus])

  const pollCtrlsRef = useRef<AbortController[]>([])

  useEffect(() => {
    if (!open) {
      pollCtrlsRef.current.forEach((c) => c.abort())
      pollCtrlsRef.current = []
      setFiles([])
    } else {
      pollCtrlsRef.current = []
    }
  }, [open])

  const hasPending = files.some((f) => f.status === "pending")
  const allDone = files.length > 0 && files.every((f) => f.status === "completed" || f.status === "failed")

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogClose onClick={() => onOpenChange(false)} />
        <DialogHeader>
          <DialogTitle>Upload Documents</DialogTitle>
          <DialogDescription>
            Upload PDF files to ingest into the knowledge base.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onClick={() => inputRef.current?.click()}
            className={cn(
              "flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-8 transition-colors",
              dragOver
                ? "border-foreground bg-accent"
                : "border-border hover:border-foreground/30",
            )}
          >
            <Upload className="h-8 w-8 text-muted-foreground" />
            <p className="text-sm font-medium text-foreground">
              Drop PDF files here
            </p>
            <p className="text-xs text-muted-foreground">or click to browse</p>
            <input
              ref={inputRef}
              type="file"
              accept=".pdf"
              multiple
              className="hidden"
              onChange={(e) => e.target.files && addFiles(e.target.files)}
            />
          </div>

          {files.length > 0 && (
            <div className="space-y-2">
              {files.map((entry, i) => (
                <div
                  key={i}
                  className="flex items-center gap-3 rounded-lg border border-border p-3"
                >
                  <FileText className="h-5 w-5 shrink-0 text-muted-foreground" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-foreground truncate">
                      {entry.file.name}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {(entry.file.size / 1024).toFixed(0)} KB
                      {entry.message && entry.status !== "completed" && entry.status !== "failed" && (
                        <span className="ml-2 text-blue-500">{entry.message}</span>
                      )}
                      {entry.message && (entry.status === "completed" || entry.status === "failed") && (
                        <span className={`ml-2 ${entry.status === "failed" ? "text-destructive" : "text-success"}`}>{entry.message}</span>
                      )}
                    </p>
                  </div>
                  {entry.status === "uploading" && (
                    <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
                  )}
                  {entry.status === "processing" && (
                    <Clock className="h-4 w-4 text-blue-500" />
                  )}
                  {entry.status === "completed" && (
                    <CheckCircle2 className="h-4 w-4 text-success" />
                  )}
                  {entry.status === "failed" && (
                    <AlertCircle className="h-4 w-4 text-destructive" />
                  )}
                  {entry.status === "pending" && (
                    <button
                      onClick={() => removeFile(i)}
                      className="text-muted-foreground hover:text-foreground cursor-pointer"
                    >
                      <X className="h-4 w-4" />
                    </button>
                  )}
                </div>
              ))}
            </div>
          )}

          {allDone && (
            <Alert variant={files.some((f) => f.status === "failed") ? "destructive" : "success"}>
              <AlertTitle>
                {files.some((f) => f.status === "failed") ? "Some Uploads Failed" : "All Uploads Complete"}
              </AlertTitle>
              <AlertDescription>
                {files.filter((f) => f.status === "completed").length} succeeded, {files.filter((f) => f.status === "failed").length} failed.
              </AlertDescription>
            </Alert>
          )}

          <div className="flex gap-2 justify-end">
            <Button
              variant="outline"
              onClick={() => onOpenChange(false)}
            >
              {allDone ? "Done" : "Cancel"}
            </Button>
            {hasPending && (
              <Button onClick={uploadAll}>
                Upload {files.filter((f) => f.status === "pending").length} file(s)
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
