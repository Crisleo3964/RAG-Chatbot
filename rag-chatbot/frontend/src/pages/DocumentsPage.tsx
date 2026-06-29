import { useState, useEffect, useCallback, useRef } from "react"
import { motion } from "framer-motion"
import { Sidebar } from "@/components/Sidebar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog"
import { UploadModal } from "@/components/UploadModal"
import { SettingsModal } from "@/components/SettingsModal"
import { UserProfileModal } from "@/components/UserProfileModal"
import { useChatContext } from "@/context/ChatContext"
import { getDocuments, downloadDocument, retryIngestion, deleteDocument } from "@/services/api"
import type { DocumentStatusResponse } from "@/types/api"
import { FileText, Download, RefreshCw, Upload, ArrowLeft, Clock, CheckCircle2, XCircle, AlertCircle, Trash2, ExternalLink } from "lucide-react"
import { useNavigate } from "react-router-dom"

const STATUS_ICONS = {
  PENDING: Clock,
  PROCESSING: RefreshCw,
  COMPLETED: CheckCircle2,
  FAILED: XCircle,
} as const

const STATUS_COLORS = {
  PENDING: "bg-yellow-100 text-yellow-800 border-yellow-200" as const,
  PROCESSING: "bg-blue-100 text-blue-800 border-blue-200" as const,
  COMPLETED: "bg-green-100 text-green-800 border-green-200" as const,
  FAILED: "bg-red-100 text-red-800 border-red-200" as const,
}

export function DocumentsPage() {
  const navigate = useNavigate()
  const { sessions, activeSessionId, loadSession, deleteSession } = useChatContext()
  const handleSelectSession = useCallback((sessionId: string) => {
    loadSession(sessionId)
    navigate("/chat")
  }, [loadSession, navigate])
  const [documents, setDocuments] = useState<DocumentStatusResponse[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const prevShowUpload = useRef(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [retrying, setRetrying] = useState<string | null>(null)
  const [deleteTarget, setDeleteTarget] = useState<DocumentStatusResponse | null>(null)
  const [deleting, setDeleting] = useState(false)

  const pollIntervalRef = useRef(5000)
  const prevStatusSnapshotRef = useRef("")

  const fetchDocuments = useCallback(async (active = true, signal?: AbortSignal) => {
    try {
      const data = await getDocuments(signal)
      if (active && !signal?.aborted) {
        setDocuments(Array.isArray(data) ? data : [])
        setError(null)
      }
    } catch (err: unknown) {
      if (active && !signal?.aborted) {
        setError(err instanceof Error ? err.message : "Failed to load documents")
      }
    } finally {
      if (active) {
        setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    const ctrl = new AbortController()
    fetchDocuments(true, ctrl.signal)
    return () => ctrl.abort()
  }, [fetchDocuments])

  useEffect(() => {
    const hasPending = (documents || []).some((d) => d.status === "PENDING" || d.status === "PROCESSING")
    if (!hasPending) {
      pollIntervalRef.current = 5000
      return
    }

    const currentSnapshot = documents.map((d) => `${d.document_id}:${d.status}:${d.chunks_created}`).join("|")
    if (currentSnapshot !== prevStatusSnapshotRef.current) {
      prevStatusSnapshotRef.current = currentSnapshot
      pollIntervalRef.current = 5000
    }

    const ctrl = new AbortController()
    const timer = setTimeout(() => fetchDocuments(true, ctrl.signal), pollIntervalRef.current)
    pollIntervalRef.current = Math.min(pollIntervalRef.current * 1.5, 30000)

    return () => {
      clearTimeout(timer)
      ctrl.abort()
    }
  }, [documents, fetchDocuments])

  useEffect(() => {
    if (prevShowUpload.current && !showUpload) {
      fetchDocuments()
    }
    prevShowUpload.current = showUpload
  }, [showUpload, fetchDocuments])

  const handleOpen = useCallback((doc: DocumentStatusResponse) => {
    const stored = localStorage.getItem("auth")
    if (!stored) return
    try {
      const { token } = JSON.parse(stored)
      window.open(`/documents/${doc.document_id}/file?inline=true&token=${encodeURIComponent(token)}`, "_blank")
    } catch {
    }
  }, [])

  const handleDownload = useCallback(async (doc: DocumentStatusResponse) => {
    try {
      const blob = await downloadDocument(doc.document_id)
      const url = URL.createObjectURL(blob)
      const a = document.createElement("a")
      a.href = url
      a.download = doc.file_name
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      URL.revokeObjectURL(url)
    } catch {
      setError("Failed to download document")
    }
  }, [])

  const handleRetry = useCallback(async (documentId: string) => {
    setRetrying(documentId)
    try {
      await retryIngestion(documentId)
      await fetchDocuments()
    } catch {
      setError("Failed to retry ingestion")
    } finally {
      setRetrying(null)
    }
  }, [fetchDocuments])

  const handleDeleteConfirm = useCallback(async () => {
    if (!deleteTarget) return
    setDeleting(true)
    try {
      await deleteDocument(deleteTarget.document_id)
      setDeleteTarget(null)
      await fetchDocuments()
    } catch {
      setError("Failed to delete document")
    } finally {
      setDeleting(false)
    }
  }, [deleteTarget, fetchDocuments])

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric", hour: "2-digit", minute: "2-digit" })
  }

  return (
    <div className="flex h-screen bg-background">
        <Sidebar
          onNewChat={() => navigate("/chat")}
          onUpload={() => setShowUpload(true)}
          onSettings={() => setShowSettings(true)}
          onProfile={() => setShowProfile(true)}
          sessions={sessions}
          activeSessionId={activeSessionId}
          onSelectSession={handleSelectSession}
          onDeleteSession={deleteSession}
        />

      <div className="flex flex-1 flex-col min-w-0">
        <div className="flex h-14 items-center justify-between border-b border-border px-6 shrink-0">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate("/chat")} className="h-8 w-8">
              <ArrowLeft className="h-4 w-4" />
            </Button>
            <h1 className="text-sm font-semibold text-foreground">Documents</h1>
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowUpload(true)} className="gap-2">
            <Upload className="h-4 w-4" />
            Upload
          </Button>
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-4xl p-6">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 w-full rounded-lg" />
                ))}
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-20">
                <AlertCircle className="h-8 w-8 text-destructive mb-3" />
                <p className="text-sm text-muted-foreground">{error}</p>
                <Button variant="outline" size="sm" className="mt-4" onClick={() => fetchDocuments()}>Retry</Button>
              </div>
            ) : documents.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-20">
                <FileText className="h-12 w-12 text-muted-foreground mb-4" />
                <h2 className="text-lg font-semibold text-foreground mb-2">No documents yet</h2>
                <p className="text-sm text-muted-foreground mb-6">Upload a PDF to get started.</p>
                <Button onClick={() => setShowUpload(true)} className="gap-2">
                  <Upload className="h-4 w-4" />
                  Upload Document
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                {(documents || []).map((doc, i) => {
                  const StatusIcon = (doc.status && STATUS_ICONS[doc.status]) || FileText
                  const statusColor = (doc.status && STATUS_COLORS[doc.status]) || "bg-muted text-muted-foreground border-border"
                  return (
                    <motion.div
                      key={doc.document_id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: i * 0.03 }}
                      className="flex items-center gap-4 rounded-lg border border-border bg-surface p-4"
                    >
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
                        <FileText className="h-5 w-5 text-muted-foreground" />
                      </div>

                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-foreground truncate">{doc.file_name}</p>
                        <div className="flex items-center gap-3 mt-1">
                          <Badge className={`${statusColor} text-xs`}>
                            <StatusIcon className="h-3 w-3 mr-1" />
                            {doc.status}
                          </Badge>
                          {doc.status === "COMPLETED" && (
                            <span className="text-xs text-muted-foreground">{doc.chunks_created} chunks</span>
                          )}
                          <span className="text-xs text-muted-foreground">{formatDate(doc.created_at)}</span>
                        </div>
                        {doc.status === "FAILED" && doc.error && (
                          <p className="text-xs text-destructive mt-1">{doc.error}</p>
                        )}
                      </div>

                      <div className="flex items-center gap-1 shrink-0">
                        {doc.status === "COMPLETED" && (
                          <>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleOpen(doc)} title="Open">
                              <ExternalLink className="h-4 w-4" />
                            </Button>
                            <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => handleDownload(doc)} title="Download">
                              <Download className="h-4 w-4" />
                            </Button>
                          </>
                        )}
                        {doc.status === "FAILED" && (
                          <Button
                            variant="ghost"
                            size="icon"
                            className="h-8 w-8"
                            onClick={() => handleRetry(doc.document_id)}
                            disabled={retrying === doc.document_id}
                            title="Retry ingestion"
                          >
                            <RefreshCw className={`h-4 w-4 ${retrying === doc.document_id ? "animate-spin" : ""}`} />
                          </Button>
                        )}
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 text-muted-foreground hover:text-destructive"
                          onClick={() => setDeleteTarget(doc)}
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </motion.div>
                  )
                })}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      <Dialog open={deleteTarget !== null} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent className="max-w-sm">
          <DialogClose onClick={() => setDeleteTarget(null)} />
          <DialogHeader>
            <DialogTitle>Delete Document</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteTarget?.file_name}"? This will remove the file and all its chunks from the vector store. This action cannot be undone.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2 pt-2">
            <Button variant="outline" onClick={() => setDeleteTarget(null)} disabled={deleting}>
              Cancel
            </Button>
            <Button variant="destructive" onClick={handleDeleteConfirm} disabled={deleting}>
              {deleting ? "Deleting..." : "Delete"}
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      <UploadModal open={showUpload} onOpenChange={setShowUpload} />
      <SettingsModal open={showSettings} onOpenChange={setShowSettings} />
      <UserProfileModal open={showProfile} onOpenChange={setShowProfile} />
    </div>
  )
}