import axios, { type AxiosInstance } from "axios"
import type { ChatRequest, ChatResponse, ChatSession, ChatMessage } from "@/types/chat"
import type { HealthResponse, IngestAcceptedResponse, DocumentStatusResponse } from "@/types/api"

const BASE_URL = import.meta.env.VITE_API_URL || ""

function createApi(): AxiosInstance {
  const instance = axios.create({
    baseURL: BASE_URL,
    timeout: 30000,
    headers: {
      "Content-Type": "application/json",
    },
  })

  instance.interceptors.request.use((config) => {
    if (config.headers.Authorization) return config
    const stored = localStorage.getItem("auth")
    if (stored) {
      try {
        const { token } = JSON.parse(stored)
        if (token) {
          config.headers.Authorization = `Bearer ${token}`
        }
      } catch {
      }
    }
    return config
  })

  instance.interceptors.response.use(
    (response) => response,
    (error) => {
      if (error.response?.status === 401) {
        localStorage.removeItem("auth")
        window.dispatchEvent(new CustomEvent("auth:logout"))
      }
      return Promise.reject(error)
    },
  )

  return instance
}

const api = createApi()

export async function getHealth(): Promise<HealthResponse> {
  const { data } = await api.get<HealthResponse>("/health")
  return data
}

export async function postChat(request: ChatRequest): Promise<ChatResponse> {
  const { data } = await api.post<ChatResponse>("/chat", request)
  return data
}

export async function uploadDocument(file: File): Promise<IngestAcceptedResponse> {
  const formData = new FormData()
  formData.append("file", file)
  const { data } = await api.post<IngestAcceptedResponse>("/ingest", formData, {
    headers: { "Content-Type": "multipart/form-data" },
    timeout: 120000,
  })
  return data
}

export async function getDocuments(signal?: AbortSignal): Promise<DocumentStatusResponse[]> {
  const { data } = await api.get<DocumentStatusResponse[]>("/api/documents", { signal })
  return data
}

export async function getDocumentStatus(documentId: string): Promise<DocumentStatusResponse> {
  const { data } = await api.get<DocumentStatusResponse>(`/documents/${documentId}/status`)
  return data
}

export async function retryIngestion(documentId: string): Promise<IngestAcceptedResponse> {
  const { data } = await api.post<IngestAcceptedResponse>(`/documents/${documentId}/retry`)
  return data
}

export async function downloadDocument(documentId: string): Promise<Blob> {
  const { data } = await api.get<Blob>(`/documents/${documentId}/file`, {
    responseType: "blob",
  })
  return data
}

export async function deleteDocument(documentId: string): Promise<void> {
  await api.delete(`/documents/${documentId}`)
}

export async function getSessions(): Promise<ChatSession[]> {
  const { data } = await api.get<ChatSession[]>("/chat/sessions")
  return data
}

export async function getSessionMessages(sessionId: string): Promise<ChatMessage[]> {
  const { data } = await api.get<ChatMessage[]>(`/chat/sessions/${sessionId}`)
  return data
}

export async function deleteSession(sessionId: string): Promise<void> {
  await api.delete(`/chat/sessions/${sessionId}`)
}

export default api
