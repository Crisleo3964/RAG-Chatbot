import { useState } from "react"
import { useNavigate } from "react-router-dom"
import { motion, AnimatePresence } from "framer-motion"
import { useAuth } from "@/hooks/useAuth"
import { useTheme } from "@/hooks/useTheme"
import { Button } from "@/components/ui/button"
import { ScrollArea } from "@/components/ui/scroll-area"
import { Separator } from "@/components/ui/separator"
import { Avatar, AvatarFallback } from "@/components/ui/avatar"
import { cn } from "@/lib/utils"
import type { ChatSession } from "@/types/chat"
import {
  MessageSquare,
  Plus,
  Upload,
  Settings,
  PanelLeft,
  History,
  FileText,
  Users,
  Trash2,
  Sun,
  Moon,
} from "lucide-react"

interface SidebarProps {
  onNewChat: () => void
  onUpload: () => void
  onSettings: () => void
  onProfile: () => void
  sessions?: ChatSession[]
  activeSessionId?: string | null
  onSelectSession?: (sessionId: string) => void
  onDeleteSession?: (sessionId: string) => void
}

export function Sidebar({ onNewChat, onUpload, onSettings, onProfile, sessions = [], activeSessionId = null, onSelectSession, onDeleteSession }: SidebarProps) {
  const { user } = useAuth()
  const { theme, toggleTheme } = useTheme()
  const navigate = useNavigate()
  const [isCollapsed, setIsCollapsed] = useState(false)

  const initials = user?.email
    ? user.email.charAt(0).toUpperCase()
    : "?"

  return (
    <>
      <motion.aside
        animate={{ width: isCollapsed ? 60 : 260 }}
        transition={{ duration: 0.2, ease: "easeInOut" }}
        className="flex flex-col border-r border-border bg-surface h-full overflow-hidden"
      >
        <div className="flex items-center gap-2 px-4 h-14 border-b border-border shrink-0">
          <AnimatePresence mode="wait">
            {!isCollapsed && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                exit={{ opacity: 0 }}
                className="flex items-center gap-2 flex-1"
              >
                <div className="flex h-7 w-7 items-center justify-center rounded-lg bg-foreground">
                  <MessageSquare className="h-4 w-4 text-background" />
                </div>
                <span className="text-sm font-semibold text-foreground">DocChat</span>
              </motion.div>
            )}
          </AnimatePresence>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsCollapsed(!isCollapsed)}
            className="ml-auto shrink-0"
          >
            <PanelLeft className="h-4 w-4" />
          </Button>
        </div>

        <div className="p-3 shrink-0">
          <Button
            variant="default"
            className="w-full justify-start gap-2"
            onClick={onNewChat}
          >
            <Plus className="h-4 w-4 shrink-0" />
            {!isCollapsed && <span>New Chat</span>}
          </Button>
        </div>

        <div className="p-3 space-y-1 shrink-0">
          <SidebarButton
            icon={<MessageSquare className="h-4 w-4" />}
            label="Chat"
            collapsed={isCollapsed}
            onClick={() => navigate("/chat")}
          />
          <SidebarButton
            icon={<FileText className="h-4 w-4" />}
            label="Documents"
            collapsed={isCollapsed}
            onClick={() => navigate("/documents")}
          />
          {user?.role === "admin" && (
            <SidebarButton
              icon={<Users className="h-4 w-4" />}
              label="User Management"
              collapsed={isCollapsed}
              onClick={() => navigate("/admin/users")}
            />
          )}
        </div>

        <Separator />

        <div className="px-3 pb-2 pt-3">
          {!isCollapsed && (
            <div className="flex items-center gap-2 px-2 py-1">
              <History className="h-3.5 w-3.5 text-muted-foreground" />
              <span className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                History
              </span>
            </div>
          )}
        </div>

        <ScrollArea className="flex-1 px-3">
          {!isCollapsed && (
            <div className="space-y-1">
              {sessions.length === 0 ? (
                <p className="text-sm text-muted-foreground py-8 text-center">
                  No chat history yet
                </p>
              ) : (
                sessions.map((s) => (
                  <div key={s.session_id} className="group relative">
                    <Button
                      variant="ghost"
                      className={cn(
                        "w-full justify-start gap-2 text-sm text-left h-auto py-2 pr-8",
                        s.session_id === activeSessionId
                          ? "bg-accent text-foreground"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                      onClick={() => onSelectSession?.(s.session_id)}
                    >
                      <MessageSquare className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{s.title}</span>
                    </Button>
                    {onDeleteSession && (
                      <button
                        onClick={(e) => { e.stopPropagation(); onDeleteSession(s.session_id) }}
                        className="absolute right-1 top-1/2 -translate-y-1/2 h-6 w-6 items-center justify-center rounded hover:bg-destructive/10 text-muted-foreground hover:text-destructive hidden group-hover:flex"
                      >
                        <Trash2 className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                ))
              )}
            </div>
          )}
        </ScrollArea>

        <Separator />

        <div className="p-3 space-y-1 shrink-0">
          <SidebarButton
            icon={<Upload className="h-4 w-4" />}
            label="Upload Documents"
            collapsed={isCollapsed}
            onClick={onUpload}
          />
          <SidebarButton
            icon={<Settings className="h-4 w-4" />}
            label="Settings"
            collapsed={isCollapsed}
            onClick={onSettings}
          />
          <SidebarButton
            icon={theme === "dark" ? <Moon className="h-4 w-4" /> : <Sun className="h-4 w-4" />}
            label={theme === "dark" ? "Dark Mode" : "Light Mode"}
            collapsed={isCollapsed}
            onClick={toggleTheme}
          />
        </div>

        <Separator />

        <div className="p-3 shrink-0">
          <button
            onClick={onProfile}
            className="flex w-full items-center gap-3 rounded-lg p-2 hover:bg-accent transition-colors cursor-pointer"
          >
            <Avatar className="h-8 w-8">
              <AvatarFallback className="text-xs">{initials}</AvatarFallback>
            </Avatar>
            {!isCollapsed && (
              <div className="flex-1 text-left min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {user?.email?.split("@")[0] || "User"}
                </p>
                <p className="text-xs text-muted-foreground truncate">{user?.email}</p>
              </div>
            )}
          </button>
        </div>
      </motion.aside>
    </>
  )
}

interface SidebarButtonProps {
  icon: React.ReactNode
  label: string
  collapsed: boolean
  onClick: () => void
}

function SidebarButton({ icon, label, collapsed, onClick }: SidebarButtonProps) {
  return (
    <Button
      variant="ghost"
      className="w-full justify-start gap-3 text-muted-foreground hover:text-foreground"
      onClick={onClick}
    >
      {icon}
      {!collapsed && <span>{label}</span>}
    </Button>
  )
}
