import { useState, useEffect, useCallback } from "react"
import { motion } from "framer-motion"
import { useNavigate } from "react-router-dom"
import { useAuth } from "@/hooks/useAuth"
import { useChatContext } from "@/context/ChatContext"
import { Sidebar } from "@/components/Sidebar"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { Skeleton } from "@/components/ui/skeleton"
import { Alert, AlertTitle, AlertDescription } from "@/components/ui/alert"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogClose,
} from "@/components/ui/dialog"
import { SettingsModal } from "@/components/SettingsModal"
import { UserProfileModal } from "@/components/UserProfileModal"
import { getUsers, createUser } from "@/services/auth"
import type { User, AdminCreateUserRequest } from "@/types/user"
import { Users, UserPlus, Shield, ArrowLeft, AlertCircle, Loader2, CheckCircle2 } from "lucide-react"

export function AdminUsersPage() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const { sessions, activeSessionId, loadSession, deleteSession } = useChatContext()
  const handleSelectSession = useCallback((sessionId: string) => {
    loadSession(sessionId)
    navigate("/chat")
  }, [loadSession, navigate])
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showSettings, setShowSettings] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const [showCreate, setShowCreate] = useState(false)

  const fetchUsers = useCallback(async () => {
    try {
      const data = await getUsers()
      setUsers(data)
      setError(null)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to load users")
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchUsers()
  }, [fetchUsers])

  if (user?.role !== "admin") {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <div className="text-center">
          <AlertCircle className="h-8 w-8 text-destructive mx-auto mb-3" />
          <h2 className="text-lg font-semibold text-foreground mb-2">Access Denied</h2>
          <p className="text-sm text-muted-foreground mb-4">You need admin privileges to view this page.</p>
          <Button variant="outline" onClick={() => navigate("/chat")}>Go to Chat</Button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar
        onNewChat={() => navigate("/chat")}
        onUpload={() => navigate("/chat")}
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
            <h1 className="text-sm font-semibold text-foreground">User Management</h1>
          </div>
          <Button variant="outline" size="sm" onClick={() => setShowCreate(true)} className="gap-2">
            <UserPlus className="h-4 w-4" />
            Add User
          </Button>
        </div>

        <ScrollArea className="flex-1">
          <div className="mx-auto max-w-4xl p-6">
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-16 w-full rounded-lg" />
                ))}
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center py-20">
                <AlertCircle className="h-8 w-8 text-destructive mb-3" />
                <p className="text-sm text-muted-foreground">{error}</p>
                <Button variant="outline" size="sm" className="mt-4" onClick={fetchUsers}>Retry</Button>
              </div>
            ) : (
              <div className="space-y-2">
                {users.map((u, i) => (
                  <motion.div
                    key={u.user_id}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.03 }}
                    className="flex items-center gap-4 rounded-lg border border-border bg-surface p-4"
                  >
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted shrink-0">
                      <Users className="h-5 w-5 text-muted-foreground" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium text-foreground">{u.email}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">{u.user_id.slice(0, 8)}...</p>
                    </div>
                    <Badge variant={u.role === "admin" ? "default" : "secondary"} className="shrink-0">
                      <Shield className="h-3 w-3 mr-1" />
                      {u.role}
                    </Badge>
                  </motion.div>
                ))}
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      <CreateUserDialog open={showCreate} onOpenChange={setShowCreate} onCreated={fetchUsers} />
      <SettingsModal open={showSettings} onOpenChange={setShowSettings} />
      <UserProfileModal open={showProfile} onOpenChange={setShowProfile} />
    </div>
  )
}

function CreateUserDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onCreated: () => void
}) {
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [role, setRole] = useState<"user" | "admin">("user")
  const [error, setError] = useState<string | null>(null)
  const [success, setSuccess] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)
    setSuccess(false)

    if (!email.trim() || !password) {
      setError("Email and password are required")
      return
    }

    setIsLoading(true)
    try {
      const req: AdminCreateUserRequest = { email: email.trim(), password, role }
      await createUser(req)
      setSuccess(true)
      setEmail("")
      setPassword("")
      setRole("user")
      onCreated()
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axiosErr = err as { response?: { data?: { detail?: string } } }
        setError(axiosErr.response?.data?.detail || "Failed to create user")
      } else {
        setError("Failed to create user")
      }
    } finally {
      setIsLoading(false)
    }
  }, [email, password, role, onCreated])

  const handleClose = useCallback(() => {
    if (!isLoading) {
      setEmail("")
      setPassword("")
      setRole("user")
      setError(null)
      setSuccess(false)
      onOpenChange(false)
    }
  }, [isLoading, onOpenChange])

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-sm">
        <DialogClose onClick={handleClose} />
        <DialogHeader>
          <DialogTitle>Add User</DialogTitle>
          <DialogDescription>Create a new user account.</DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <Alert variant="destructive">
              <AlertTitle>Error</AlertTitle>
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}
          {success && (
            <Alert variant="success">
              <AlertTitle>Success</AlertTitle>
              <AlertDescription>User created successfully.</AlertDescription>
            </Alert>
          )}

          <div className="space-y-2">
            <Label htmlFor="new-email">Email</Label>
            <Input
              id="new-email"
              type="email"
              placeholder="user@company.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isLoading || success}
              autoFocus
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="new-password">Password</Label>
            <Input
              id="new-password"
              type="password"
              placeholder="Minimum 4 characters"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              disabled={isLoading || success}
            />
          </div>

          <div className="space-y-2">
            <Label>Role</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant={role === "user" ? "default" : "outline"}
                size="sm"
                className="flex-1"
                onClick={() => setRole("user")}
                disabled={isLoading || success}
              >
                User
              </Button>
              <Button
                type="button"
                variant={role === "admin" ? "default" : "outline"}
                size="sm"
                className="flex-1"
                onClick={() => setRole("admin")}
                disabled={isLoading || success}
              >
                Admin
              </Button>
            </div>
          </div>

          {!success && (
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                <>
                  <UserPlus className="h-4 w-4" />
                  Create User
                </>
              )}
            </Button>
          )}

          {success && (
            <Button type="button" variant="outline" className="w-full" onClick={handleClose}>
              <CheckCircle2 className="h-4 w-4" />
              Done
            </Button>
          )}
        </form>
      </DialogContent>
    </Dialog>
  )
}