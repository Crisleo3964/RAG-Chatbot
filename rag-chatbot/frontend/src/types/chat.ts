export interface ChatRequest {
  question: string
  session_id?: string
}

export interface SourceRef {
  document: string
  page: number
}

export interface ChatResponse {
  answer: string
  sources: SourceRef[]
  session_id?: string
}

export interface ChatSession {
  session_id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface ChatMessage {
  message_id: string
  session_id: string
  role: "user" | "assistant"
  content: string
  sources?: SourceRef[]
  created_at: string
}

export interface Message {
  id: string
  role: "user" | "assistant"
  content: string
  sources?: SourceRef[]
  timestamp: Date
}

export interface ChatState {
  messages: Message[]
  isStreaming: boolean
  currentSources: SourceRef[]
}
