export interface HealthResponse {
  status: string
}

export interface ErrorResponse {
  detail: string | unknown[]
}

export interface IngestAcceptedResponse {
  document_id: string
  file_name: string
  status: string
  user_id: string
}

export interface DocumentStatusResponse {
  document_id: string
  file_name: string
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED"
  chunks_created: number
  error: string | null
  user_id: string
  created_at: string
  updated_at: string
}

export interface ApiError {
  status: number
  message: string
  detail?: string | unknown[]
}
